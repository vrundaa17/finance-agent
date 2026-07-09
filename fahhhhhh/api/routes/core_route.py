from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
import agent.find as find
import asyncio,os,datetime
from agent.analyse import build_graph

app = APIRouter(tags=['core'])
graph= None

def init_graph():
    global graph
    graph = build_graph()
    return graph


async def run_report(stock_name: str):
    if watchlist.is_reported_today(stock_name):
        cached = watchlist.get_reports(stock_name)
        kyc = find.get_kyc_of_stock(stock_name)
        return {"fundamentals": kyc, "report": cached["report"], "charts": {}}

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: graph.invoke({'stock_name': stock_name.upper()})
    )
    if result.get("report"):
        watchlist.report(stock_name, result["report"])
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
        # print(str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
