import sys
import os,datetime
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pytz
from agent.analyse import build_graph
import api.watchlist as watchlist
from api.watchlist import cleanup_alerts

IST = pytz.timezone("Asia/Kolkata")
graph = build_graph()


def run_daily_reports():
    print("[Schhh] running daily rep")
    watchlists = watchlist.list_watchlists()

    for wl in watchlists:
        tickers = watchlist.get_stock(wl["name"])
        for stock in tickers:
            try:
                print(f"[Scheduler] Generating report for {stock}...")
                result = graph.invoke({"stock_name": stock})
                if result.get("report"):
                    watchlist.report(stock,result['report'])
                    print(f"[Scheduler]  {stock} report found")
                else:
                    print(f"[Scheduler] X {stock} failed : {result.get("error")}")
            except Exception as e:
                print(f"[Scheduler] X {stock} - Exception : {e}")
    print("[Scheduler] Daily reports done")
    
    
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
            print(f"[Alerts] Could not fetch price for {stock}: {e}")
    
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
            print(f"[ALERT] TRIGGERED : {stock} is {price}")
            print(f"({alert['condition']} {alert['threshold']})")




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
        cleanup_alerts,
        CronTrigger(hour=0,minute=0,timezone=IST),
        id="cleanup_alert",
        name="Clean Up Expired Alert",
        replace_existing=True,
    )
    
    scheduler.start()
    print(f"[Scheduler] started ")
    return scheduler


