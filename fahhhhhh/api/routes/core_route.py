from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import api.db.report_db as report_watchlist
import api.db.predict_db as predict_watchlist
import agent.find as find
import asyncio,datetime
from agent.analyse import build_graph
from agent.lstm import train_pred_lstm
from core.db import check_db_health
from core.celery_app import check_celery_health
from core.cache import r
import logging,utils
logger = logging.getLogger(__name__)

app = APIRouter(tags=['core'])
graph= None


def init_graph():
    global graph
    graph = build_graph()
    return graph




async def run_report(stock_name: str, horizon: int = 1):
    
    if report_watchlist.is_reported_today(stock_name):
        cached = report_watchlist.get_reports(stock_name)
        try:
            kyc = find.get_kyc_of_stock(stock_name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"fundamentals": kyc, "report": cached["report"],
                "targets": cached.get("targets"), "lstm_prediction": cached.get("lstm_prediction"), "charts": {}}
    
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: graph.invoke({'stock_name': stock_name.upper()})
    )

    lstm_result = None
    if not result.get("error"):
        try:
            price_history = find.get_price_history(stock_name, "3y")
            index_history = find.get_price_history("^NSEI", "3y")
            
            lstm_key = f"lstm:{stock_name.upper()}:{horizon}"
            lstm_cached = r.get(lstm_key)
            if lstm_cached:
                lstm_result = utils.loads_or_none(lstm_cached)
            else:
                lstm_result = await loop.run_in_executor(
                    None, lambda: train_pred_lstm(price_history, index_history, horizon=horizon)
                )
                r.set(lstm_key,utils.dumps_or_none(lstm_result),ex=3600)
            predict_watchlist.save_prediction(
                stock_name=stock_name, direction=lstm_result["direction"],
                confidence=lstm_result["confidence"], accuracy=lstm_result["bd_accuracy"],
                predicted_price=lstm_result["predicted_price"], analysis_price=lstm_result["analysis_price"],
                horizon_days=lstm_result["horizon_days"],
            )
        except Exception as e:
            logger.error(f"LSTM failed for {stock_name}: {e}")

    if result.get("report"):
        report_watchlist.report(stock_name, result["report"], targets=result.get("targets"), lstm_prediction=lstm_result)

    result["lstm_prediction"] = lstm_result
    return result



@app.get("/health")
def health():
    checks = {"api": "ok"}
    try:
        r.ping()
        checks["redis"]="ok"
    except Exception:
        checks["redis"] = "down"
    
    checks["database"] = "ok" if check_db_health() else "down"
    checks["celery"] = "ok" if check_celery_health() else "down"
    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(content=checks, status_code=status_code)


@app.get("/quotes")
async def get_quotes(tickers: str):
    """Get live price + change for multiple stocks """
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    semaphore = asyncio.Semaphore(5)
    loop = asyncio.get_event_loop()
    
    async def fetch_one(sym):
        async with semaphore:
            try:
                data = await loop.run_in_executor(None, find.get_kyc_of_stock, sym)
                price = data.get("current_price")
                prev = data.get("previous_close")
                change = round(price - prev, 2) if price and prev else None
                change_pct = round((change / prev) * 100, 2) if change and prev else None
                return {
                    "stock_name": sym,
                    "company_name": data.get("company_name"),
                    "current_price": price,
                    "change": change,
                    "change_pct": change_pct,
                }
            except ValueError as e:
                return {"stock_name": sym, "error": str(e)}
            except Exception as e:
                return {"stock_name": sym, "error": str(e)}

    quote = await asyncio.gather(*(fetch_one(sym) for sym in symbols))
    logger.info("Live stocks fetched...")
    return {"quotes": quote}


@app.get("/news")
def general_news(limit: int = 8):
    """Get general market news"""
    try:
        news = find.get_news_finnhub("general")
        trimmed = news[:limit]
        for item in trimmed:
            if item.get("time"):
                item["time"] = datetime.datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d %H:%M")
        logger.info("Live news fetched...")
        return {"news": trimmed}
    except Exception as e:
        logger.error(f"Error while fetching live news {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
