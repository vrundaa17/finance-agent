from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
import api.schema as schema
import asyncio,os
import agent.find as find
from visualise import generate_all_charts,cleanup_charts
from agent.target import calculate_targets
from api.routes.core_route import run_report
from agent.predict import train_pred
import logging
logger = logging.getLogger(__name__)

app = APIRouter(tags=['Report'])

@app.post("/report/watchlist")
async def watchlist_report(request : schema.WatchlistReportRequest):
    """Run reports for multiple stocks in parallel"""
    try:
        stocks = [run_report(st) for st in request.stock_name]
        results = await asyncio.gather(*stocks, return_exceptions=True)
        reports = []
        for stock, result in zip(request.stock_name, results):
            if isinstance(result, Exception):
                reports.append({
                    "stock": stock.upper(),
                    "company_name": None,
                    "current_price": None,
                    "fundamentals": {},
                    "report": None,
                    "target" : None,
                    "error": str(result),
                    "status": "error",
                })
                continue
            reports.append({
                "stock": stock.upper(),
                "company_name": result.get("fundamentals", {}).get("company_name"),
                "current_price": result.get("fundamentals", {}).get("current_price"),
                "fundamentals": result.get("fundamentals", {}),
                "report": result.get("report"),
                "targets": result.get("targets", {}),
                "error": result.get("error"),
                "status": "error" if result.get("error") else "success",
            })

        logger.info(f"Report generation for stock :{request.stock_name}")
        return {
            "total": len(reports),
            "successful": sum(1 for r in reports if r["status"] == "success"),
            "failed": sum(1 for r in reports if r["status"] == "error"),
            "reports": reports,
        }
    except Exception as e:
        logger.error(f"watchlist_report failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
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
        stock_data = find.get_kyc_of_stock(stock_name)
        price_data = find.get_price_history(stock_name,period)
        paths = generate_all_charts(chart_types,price_data,stock_data,stock_name)
        base_url= os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
        urls = {
            chart_type: f"{base_url}/charts/{os.path.basename(path)}"
            for chart_type, path in paths.items()
            if path
        }
        logger.info(f"Charts generated for {stock_name.upper()} - {chart_types}")
        return {"stock": stock_name.upper(), "charts": urls}
    except Exception as e:
        logger.error(f"Chart generation failed : {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/charts/clear")
def clear_charts():
    cleanup_charts()
    return {"status": "cleared"}


#--------------------------------------------------------------------------------------------------------------------------------------------------------
# prediction :
@app.get("/target/{stock_name}")
def get_targets(stock_name : str, period:str = "3mo"):
    try :
        fundamentals = find.get_kyc_of_stock(stock_name)
        price_history = find.get_price_history(stock_name,period)
        return calculate_targets(price_history,fundamentals)
    except Exception as e:
        raise HTTPException(status_code = 400, detail=str(e))


@app.get("/predict/{stock_name}")
def predict_stock(stock_name:str, period: str="3y"):
    try:
        price_history = find.get_price_history(stock_name, period)
        result = train_pred(price_history)
        if not result.get("error"):
            watchlist.save_prediction(stock_name,result["direction"],result["confidence"],result["accuracy"])
        return result
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))
    
    
@app.get("/predictions")
def list_predictions(stock_name: str = None):
    return watchlist.get_predictions(stock_name)

@app.post("/predictions/{prediction_id}/feedback")
def human_feedback(prediction_id: int, flag: str, note: str = ""):
    return watchlist.add_human_feedback(prediction_id, flag, note)

@app.post("/predictions/verify")
def verify_prediction(stock_name: str, date: str, actual: str):
    return watchlist.update_actual_outcome(stock_name, date, actual)

@app.delete("/predictions/clear")
def clean_prediction():
    return watchlist.clear_predictions()

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