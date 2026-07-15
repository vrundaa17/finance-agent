import sys
import os,datetime
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pytz
import agent.find as find
from agent.analyse import build_graph
import api.watchlist as watchlist
from visualise import cleanup_charts
from api.watchlist import cleanup_reports,cleanup_alerts
import logging
logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
graph = build_graph()


def run_daily_reports():
    print("[Scheduler] running daily rep")
    watchlists = watchlist.list_watchlist()

    for wl in watchlists:
        tickers = watchlist.get_stock(wl["name"])
        for stock in tickers:
            try:
                print(f"[Scheduler] Generating report for {stock}...")
                result = graph.invoke({"stock_name": stock})
                if result.get("report"):
                    watchlist.report(stock,result['report'])
                    logger.info(f"[Scheduler]  {stock} report found")
                else:
                    logger.error(f"[Scheduler] X {stock} failed : {result.get('error')}")
            except Exception as e:
                logger.error(f"[Scheduler] X {stock} - Exception : {e}")
    logger.info("[Scheduler] Daily reports done")
    
    
def check_price_alerts():
    now = datetime.datetime.now(IST)
    if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
        return
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        return
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


def verify_prediction():
    yesterday = (datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    unverified = [p for p in watchlist.get_predictions() if not p["actual_outcome"] and p["predicted_at"].startswith(yesterday[:7])]
    unique_stocks = list(set(p["stock_name"] for p in unverified))
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


def start_scheduler():
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(
        run_daily_reports,
        CronTrigger(hour=9, minute=15, timezone=IST),
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
        cleanup_charts,
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
        CronTrigger(hour=0,minute=0,timezone=IST),
        id="auto_verify_predictions",
        name="Verifing predictions",
        replace_existing=True,
        )
    scheduler.start()
    logger.info(f"[Scheduler] started ")
    return scheduler


