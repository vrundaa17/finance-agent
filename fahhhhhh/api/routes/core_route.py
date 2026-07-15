from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
import agent.find as find
import asyncio,datetime
from agent.analyse import build_graph
from agent.lstm import train_pred_lstm
import logging
logger = logging.getLogger(__name__)

app = APIRouter(tags=['core'])
graph= None
import logging
logger = logging.getLogger(__name__)
def init_graph():
    global graph
    graph = build_graph()
    return graph




async def run_report(stock_name: str, horizon: int = 5):
    if watchlist.is_reported_today(stock_name):
        cached = watchlist.get_reports(stock_name)
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
            lstm_result = await loop.run_in_executor(
                None, lambda: train_pred_lstm(price_history, index_history, horizon=horizon)
            )
            watchlist.save_prediction(
                stock_name=stock_name, direction=lstm_result["direction"],
                confidence=lstm_result["confidence"], accuracy=lstm_result["bd_accuracy"],
                predicted_price=lstm_result["predicted_price"], current_price=lstm_result["current_price"],
                horizon_days=lstm_result["horizon_days"],
            )
        except Exception as e:
            logger.error(f"LSTM failed for {stock_name}: {e}")

    if result.get("report"):
        watchlist.report(stock_name, result["report"], targets=result.get("targets"), lstm_prediction=lstm_result)

    result["lstm_prediction"] = lstm_result
    return result



@app.get("/health")
def health():
    return {"status": "ok", "service": "fahhhhhh"}


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
            logger.error("Error while fetching live stock...")
            quotes.append({"stock_name": sym, "error": str(e)})
    logger.info("Live stocks fetched...")
    return {"quotes": quotes}


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
        
