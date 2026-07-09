from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
import api.schema as schema
import asyncio,os
import agent.find as find
from visualise import generate_all_charts
from api.routes.core_route import run_report

app = APIRouter(tags=['Report'])

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
            "fundamentals":result.get("fundamentals",{}),
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
    
    
@app.get("/report/today")
def reports_today():
    """List all stocks analysed today"""
    return {"reports": watchlist.list_reports_today()}


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


# @app.post("/report/{stock_name}")
# async def single_report(stock_name : str):
#     """Generate full report for a single stock"""
    
#     result = await run_report(stock_name)
#     if result.get("error"):
#         raise HTTPException(status_code=400, detail=result["error"])
#     return {
#         "stock": stock_name.upper(),
#         "company_name": result["fundamentals"].get("company_name"),
#         "current_price": result["fundamentals"].get("current_price"),
#         "fundamentals": result.get("fundamentals", {}),
#         "report": result.get("report"),
#         "charts": result.get("charts", {}),
#     }