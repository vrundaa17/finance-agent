from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
sys.path.insert(0, "/Users/prashant/Desktop/fxis/task/fahhhhhh")
import agent.find as find
from agent.analyse import build_graph
from db import init_db
from visualise import generate_all_charts
import api.watchlist as watchlist
import api.schema as schema
from scheduler import start_scheduler
from fastapi.staticfiles import StaticFiles
import os,asyncio
from datetime import datetime
from contextlib import asynccontextmanager

graph = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    init_db()
    graph = build_graph()
    scheduler= start_scheduler()
    yield
    scheduler.shutdown()

app=FastAPI(
    title= 'Fahhh',
    version='1.0.0',
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("charts", exist_ok=True)
app.mount("/charts", StaticFiles(directory="charts"), name="charts")


#helper
async def run_report(stock_name : str):
    """Helper function for invoking the graph in thread pol"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,lambda : graph.invoke({'stock_name':stock_name.upper()})
    )
    if result.get("report"):
        watchlist.report(stock_name, result["report"])
    return result



@app.get("/health")
def health():
    return {"status": "ok", "service": "fahhhhhh"}


@app.get("/stock/{stock_name}")
def stock_overview(stock_name:str):
    return find.get_kyc_of_stock(stock_name)

@app.get("/quotes")
def get_quotes(tickers: str):
    """Get live price + change for multiple stocks """
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    quotes = []
    for sym in symbols:
        try:
            data = find.get_kyc_of_stock(sym)
            price = data.get("current_price")
            prev = data.get("previous_close")
            change = round(price - prev, 2) if price and prev else None
            change_pct = round((change / prev) * 100, 2) if change and prev else None
            quotes.append({
                "stock_name": sym,
                "company_name": data.get("company_name"),
                "current_price": price,
                "change": change,
                "change_pct": change_pct,
            })
        except Exception as e:
            quotes.append({"stock_name": sym, "error": str(e)})
    return {"quotes": quotes}


@app.get("/news")
def general_news(limit: int = 8):
    """Get general market news"""
    try:
        news = find.get_news_finnhub("general")
        trimmed = news[:limit]
        for item in trimmed:
            if item.get("time"):
                item["time"] = datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M")
        return {"news": trimmed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# watchlist - db
@app.get("/watchlists")
def get_all_watchlists():
    """List all the watchlists"""
    return watchlist.list_watchlist()
 
@app.post("/watchlists")
def create_new_watchlist(request: schema.Watchlist):
    """Create new watchlist"""
    return watchlist.create_watchlist(request.name)

@app.get("/watchlists/{watchlist_name}")
def get_stock_watchlist(watchlist_name: str):
    """ Get all the stock in a watchlist"""
    stock_name = watchlist.get_stock(watchlist_name)
    if stock_name is None:
        raise HTTPException(status_code=404, detail=f"Watchlist '{watchlist_name}' not found")
    return {"watchlist": watchlist_name, "stock_name": stock_name}

@app.post("/watchlists/add")
def add_to_watchlist(body:schema.StockAdd):
    """Add stocks to the watchlist"""
    return watchlist.add_stock(body.watchlist_name,body.stock_name,body.notes or None)

@app.delete("/watchlists/{watchlist_name}/{stock}")
def remove_stock(watchlist_name:str,stock:str):
    """Remove from the watchlist"""
    return watchlist.remove_stock(watchlist_name,stock)

@app.delete("/watchlists/{watchlist_name}")
def delete_existing_watchlist(watchlist_name: str):
    """Delete the watchlist"""
    return watchlist.delete_watchlist(watchlist_name)




#reports
@app.post("/report/{stock_name}")
async def single_report(stock_name : str):
    """Generate full report for a single stock"""
    
    result = await run_report(stock_name)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "stock": stock_name.upper(),
        "company_name": result["fundamentals"].get("company_name"),
        "current_price": result["fundamentals"].get("current_price"),
        "fundamentals": result.get("fundamentals", {}),
        "report": result.get("report"),
        "charts": result.get("charts", {}),
    }


@app.post("/report/watchlist")
async def watchlist_report(request : schema.WatchlistReportRequest):
    """Run reports for multiple stocks in parallel"""
    
    stocks = [run_report(st) for st in request.stock_name]
    results = await asyncio.gather(*stocks)
    reports =[]
    for stock, result in zip(request.stock_name, results):
        reports.append({
            "stock" : stock.upper(),
            "company_name": result.get("fundamentals",{}).get("company_name"),
            "current_price": result.get("fundamentals", {}).get("current_price"),
            "report": result.get("report"),
            "error": result.get("error"),
            "status": "success" if result.get("report") else "error",
        })
    return {
        "total": len(reports),
        "successful": sum(1 for r in reports if r["status"] == "success"),
        "failed": sum(1 for r in reports if r["status"] == "error"),
        "reports": reports,
    }


@app.get("/report/{stock_name}/cached")
def cached_report(stock_name: str):
    """Get the last generated report without regenerating"""
    
    stored = watchlist.get_reports(stock_name.upper())
    if not stored:
        raise HTTPException(
            status_code=404,
            detail=f"No reports are generated yet..."
        )
    return stored


@app.post("/report/watchlist/{name}")
async def report_for_named_watchlist(name: str):
    """Generate reports for all the stocks in a saved watchlist"""
    
    stock_name= watchlist.get_stock(name)
    if not stock_name:
        raise HTTPException(
            status_code=404,
            detail=f"Watchlist '{name}' is empty or doesn't exist."
        )
    request = schema.WatchlistReportRequest(stock_name=stock_name)
    return await watchlist_report(request)



#chart generation
@app.get("/generate_charts/{stock_name}")
def get_charts(stock_name: str, period: str = "3mo",chart_types:str="fundamentals,volume"):
    """Generate charts for a stock and return public url"""
    
    try:
        price_data = find.get_price_history(stock_name,period)
        stock_data = find.get_kyc_of_stock(stock_name)
        paths = generate_all_charts(chart_types,price_data,stock_data,stock_name)
        base_url='http://localhost:8000'
        urls = {
            chart_type: f"{base_url}/charts/{os.path.basename(path)}"
            for chart_type, path in paths.items()
            if path
        }
        return {"stock": stock_name.upper(), "charts": urls}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    
    
#--------------------------------------------------------------------------------------------------------------------------------------------------------    
#alerts
@app.post("/alerts")
def create_alert(stock_name: str,condition: str, threshold:float,is_persistent:bool,expire_days:int):
    """Add a new alert"""
    return watchlist.add_alert(stock_name,condition,threshold,is_persistent,expire_days)

@app.get("/alerts")
def list_alerts(stock_name:str):
    """List all my alerts"""
    return watchlist.get_alerts(stock_name)

@app.get("/alerts/active")
def list_active_alerts():
    """List all the active alerts """
    return watchlist.get_active_alerts()

@app.get("/alerts/logs")
def list_alert_logs():
    """Show my alert log"""
    return watchlist.get_alert_log()

@app.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    return watchlist.user_delete_alert(alert_id)