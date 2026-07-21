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

from api.routes.core_route import run_report
import api.db.report_db as report_watchlist
import api.db.alert_db as alert_watchlist
import api.db.predict_db as edit_watchlist

from core.visualise import clear_all_charts

from cache import set_job_state,r
from celery_app import celery_app
import logging
logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")



async def _run_daily_reports_async():
    logger.info("[Scheduler] running daily rep")
    watchlists = report_watchlist.list_watchlist()
    semaphore = asyncio.Semaphore(5)
    async def _process_stock(stock):
        async with semaphore:
            if report_watchlist.is_reported_today(stock):
                logger.info(f"[Scheduler] {stock} already reported today, skipping ")
                return
            try:
                logger.info(f"[Scheduler] Generating report for {stock}...")
                result = await run_report(stock)
                if result.get("report"):
                    logger.info(f"[Scheduler] {stock} report found")
                else:
                    logger.info(f"[Scheduler] {stock} report failed : {result.get('error')}")
            except Exception as e:
                logger.error(f"[Scheduler] Exxeption {e}")
    tasks=[
        _process_stock(stock)
        for wl in watchlists
        for stock in report_watchlist.get_stock(wl['name'])
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
    alerts = alert_watchlist.get_active_alerts()
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
            alert_watchlist.mark_alert_triggered(alert['id'],price)
            logger.info(f"[ALERT] TRIGGERED : {stock} is {price}")
            logger.info(f"({alert['condition']} {alert['threshold']})")
    set_job_state("price_alerts", "done")



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
        report_watchlist.cleanup_reports,
        CronTrigger(hour=12,minute=0,timezone=IST),
        id="cleanup_reports",
        name="Clean Up Expired Reports",
        replace_existing=True,
    )
    scheduler.add_job(
        alert_watchlist.cleanup_alerts,
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
        edit_watchlist.auto_verify_predictions,
        CronTrigger(hour=14,minute=00,timezone=IST),
        id="auto_verify_predictions",
        name="Verifing predictions",
        replace_existing=True,
        )
    scheduler.start()
    logger.info(f"[Scheduler] started ")
    return scheduler


