import sys
import os
from datetime import datetime,timedelta
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pytz,asyncio
import agent.find as find
from agent.analyse import build_graph
import api.watchlist as watchlist
from visualise import clear_all_charts
from api.watchlist import cleanup_reports,cleanup_alerts
from cache import set_job_state,r
from celery_app import celery_app
import logging
logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
graph = build_graph()




async def _run_daily_reports_async():
    print("[Scheduler] running daily rep")
    watchlists = watchlist.list_watchlist()
    semaphore = asyncio.Semaphore(5)
    async def _process_stock(stock):
        async with semaphore:
            try:
                logger.info(f"[Scheduler] Generating report for {stock}...")
                result = await graph.ainvoke({"stock_name": stock})
                if result.get("report"):
                    watchlist.report(stock,result['report'])
                    logger.info(f"[Scheduler]  {stock} report found")
                else:
                    logger.error(f"[Scheduler] X {stock} failed : {result.get('error')}")
            except Exception as e:
                logger.error(f"[Scheduler] X {stock} - Exception : {e}")
    tasks=[
        _process_stock(stock)
        for wl in watchlists
        for stock in watchlist.get_stock(wl['name'])
    ]
    await asyncio.gather(*tasks)
    logger.info("[Scheduler] Daily reports done")

@celery_app.task
def run_daily_reports_task():
    logger.info("[Celery] running daily reports")
    asyncio.run(_run_daily_reports_async())
    r.publish("reports", "daily_reports_done")
    
    
def run_daily_reports():
    logger.info("[Scheduler] running daily rep")
    run_daily_reports_task.delay()
    
    
def check_price_alerts():
    now = datetime.now(IST)
    if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
        return
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        return
    set_job_state("price_alerts", "running")
    alerts = watchlist.get_active_alerts()
    if not alerts:
        return
    stocks = list(set(a["stock_name"]for a in alerts))
    
    prices={}
    for stock in stocks:
        try:
            info = yf.Ticker(stock).info
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price:
                prices[stock]= price
        except Exception as e:
            logger.error(f"[Alerts] Could not fetch price for {stock}: {e}")
    
    for alert in alerts:
        stock = alert['stock_name']
        price = prices.get(stock)
        if not price:
            continue
        triggered = False
        if alert['condition']=='below' and price< alert['threshold']:
            triggered = True
        elif alert['condition']=='above' and price >alert['threshold']:
            triggered = True
            
        if triggered:
            watchlist.mark_alert_triggered(alert['id'],price)
            logger.info(f"[ALERT] TRIGGERED : {stock} is {price}")
            logger.info(f"({alert['condition']} {alert['threshold']})")
    set_job_state("price_alerts", "done")


def verify_prediction():
    set_job_state("verify_prediction", "running")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    unverified = [p for p in watchlist.get_predictions() if not p["actual_outcome"] and p["predicted_at"].startswith(yesterday[:7])]
    unique_stocks = list(set(p["stock_name"] for p in unverified))

    failed = []
    for stock in unique_stocks:
        try:
            history = find.get_price_history(stock, "5d")
            closes = history["close"]
            if len(closes) >= 2:
                actual = "UP" if closes[-1] > closes[-2] else "DOWN"
                watchlist.update_actual_outcome(stock, yesterday, actual)
                print(f"[Scheduler] Verified {stock}: {actual}")
        except Exception as e:
            print(f"[Scheduler] Could not verify {stock}: {e}")
            failed.append(stock)

    if failed:
        set_job_state("verify_prediction",f"done_with_errors : {",".join(failed)}")
    else:
        set_job_state("verify_prediction", "done")


# BackgroundScheduler runs jobs in worker threads, not in FastAPI event loop 

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        run_daily_reports,
        CronTrigger(hour=11, minute=6, timezone=IST),
        id="daily_reports",
        name="Daily market reports",
        replace_existing=True,
    )
    scheduler.add_job(
        check_price_alerts,
        IntervalTrigger(minutes=7),
        id="price_alerts",
        name="Price Alert Check",
        replace_existing=True
    )
    scheduler.add_job(
        cleanup_reports,
        CronTrigger(hour=12,minute=0,timezone=IST),
        id="cleanup_reports",
        name="Clean Up Expired Reports",
        replace_existing=True,
    )
    scheduler.add_job(
        cleanup_alerts,
        CronTrigger(hour=12,minute=0,timezone=IST),
        id="cleanup_alerts",
        name="Clean Up Expired Alert",
        replace_existing=True,
    )
    scheduler.add_job(
        clear_all_charts,
        CronTrigger(hour=12,minute=0,timezone=IST),
        id="cleanup_charts",
        name="Clean Up Charts",
        replace_existing=True,
    )
    scheduler.add_job(
        verify_prediction,
        CronTrigger(hour=12, minute=0, timezone=IST),
        id="verify_predictions",
        name="Verify yesterday predictions",
        replace_existing=True,
    )
    scheduler.add_job(
        watchlist.cleanup_old_predictions,
        CronTrigger(hour=0,minute=0,timezone=IST),
        id="cleanup_old_predictions",
        name="Clean Up Old predictions",
        replace_existing=True,
    )
    scheduler.add_job(
        watchlist.auto_verify_predictions,
        CronTrigger(hour=18,minute=28,timezone=IST),
        id="auto_verify_predictions",
        name="Verifing predictions",
        replace_existing=True,
        )
    scheduler.start()
    logger.info(f"[Scheduler] started ")
    return scheduler


