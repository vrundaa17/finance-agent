from mcp.server.fastmcp import FastMCP
import sys,os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import agent.find as find
import api.db.report_db as report_watchlist
import api.db.predict_db as edit_watchlist
import api.db.alert_db as alert_watchlist
from core.visualise import generate_all_charts
import base64
from mcp.types import Resource
from agent.analyse import build_graph
from agent.lstm import train_pred_lstm
from agent.target import calculate_targets

mcp = FastMCP("fahhhh")
graph = build_graph()


@mcp.tool()
def analyse_stock(stock_name:str)-> dict:
    """Generate full AI stock report for a stock ticker e.g. AAPL, TSLA, RELIANCE.NS.
    Includes fundamentals analysis, latest news summary, risk assessment with computed
    volatility metrics, and a professional daily brief. Takes 15-30 seconds.
    """

    result = graph.invoke({"stock_name": stock_name.upper()})
    report = result.get('report') or result.get('error')
    if result.get('report'):
        report_watchlist.report(stock_name,report)
    return report


@mcp.tool()
def fundamentals(stock_name:str)-> dict:
    """Get key stock fundamentals for a ticker: current price, P/E ratio, EPS,
    revenue growth, profit margin, debt-to-equity, sector, and 52-week range.
    Use for a quick data snapshot. ticker example: AAPL, MSFT, RELIANCE.NS
    """
    return find.get_kyc_of_stock(stock_name)


@mcp.tool()
def news(stock_name:str)-> dict:
    """Get latest news articles for a stock from the last 24 hours.
    Returns headlines, summaries, sources and URLs.
    ticker example: AAPL, TSLA, INFY.NS
    """
    return find.get_news_by_stock(stock_name)


@mcp.tool()
def statement(stock_name:str,stype:str)-> dict:
    """Get a financial statement for a stock.
    stype options: balance_sheet, income_stmt, cash_flow,
    quarterly_balance_sheet, quarterly_income_stmt, quarterly_cashflow,
    dividend, splits, actions
    """
    return find.get_statement(stock_name, stype)



#------------------------------------------------------------------------------
#chart tools
@mcp.resource("chart://{stock_name}/{chart_type}/{period}")
def get_chart_resource(stock_name: str, chart_type: str,period:str)-> Resource:
    """
    MCP Resource — returns chart as binary PNG.
    Claude Desktop renders this inline as an image.
    Access via: chart://RELIANCE.NS/price/3mo
    """
    price_history = find.get_price_history(stock_name, period)
    kyc_data = find.get_kyc_of_stock(stock_name)
    paths = generate_all_charts([chart_type], price_history, kyc_data, stock_name)

    path = paths.get(chart_type)
    if not path or not os.path.exists(path):
        raise ValueError(f"Char '{chart_type}' count not found.")
    
    with open(path,'rb')as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")
        
    return Resource(
        uri=f"chart://{stock_name}/{chart_type}/{period}",
        name=f"{stock_name} {chart_type} chart ({period})",
        mimeType="image/png",
        blob=img_data,
    )

@mcp.tool()
def charts(chart_types: list[str], stock_name: str, period: str = "3mo") -> dict:
    """Generate financial charts for a stock ticker and return viewable URLs.
    chart_types: ['price', 'volume', 'fundamentals'] or any combination.
    period: '1mo', '3mo', '6mo', '1y'.
    After calling this, fetch the images using the returned resource URIs.
    """
    price_history = find.get_price_history(stock_name, period)
    kyc_data = find.get_kyc_of_stock(stock_name)
    paths = generate_all_charts(chart_types, price_history, kyc_data, stock_name)

    resource_urls = {
        chart_type: f"chart://{stock_name}/{chart_type}/{period}" for chart_type in chart_types if paths.get(chart_type)
    }

    return {
        "stock_name": stock_name.upper(),
        "message": "Charts generated.",
        "resources": resource_urls
    }



#---------------------------------------------------------------------------------------------------------------------------
#watchlist tools
@mcp.tool()
def create_watchlist(watchlist_name):
    """Create a new named watchlist to track a group of stocks.
    Example: create_new_watchlist('uncle_portfolio') or create_new_watchlist('tech_stocks')."""
    return report_watchlist.create_watchlist(watchlist_name)

@mcp.tool()
def list_watchlist():
    """ Show all existing watchlists with their names and ticker counts."""
    return report_watchlist.list_watchlist()

@mcp.tool()
def delete_watchlist(watchlist_name:str):
    """Delete a watchlist and all its tickers permanently."""
    return report_watchlist.delete_watchlist(watchlist_name)

@mcp.tool()
def add_stock(watchlist_name,stock_name,note):
    """Add a stock ticker to a watchlist.
    ticker: stock symbol e.g. AAPL, TSLA, RELIANCE.NS
    notes: optional note e.g. 'Client A holding', 'High conviction'
    Creates the watchlist if it doesn't exist yet."""
    return report_watchlist.add_stock(watchlist_name,stock_name,note)


@mcp.tool()
def list_stock(watchlist_name):
    """Get all tickers in a named watchlist.
    Returns a list of ticker symbols."""
    return report_watchlist.get_stock(watchlist_name)

@mcp.tool()
def remove_stock(watchlist_name,stock_name):
    """Remove a stock ticker from a watchlist."""
    return report_watchlist.remove_stock(watchlist_name,stock_name)


@mcp.tool()
def get_report(stock_name:str):
    """Get the most recently cached report for a ticker without regenerating.
    Useful when the stock needs to be re-c
    """
    report = report_watchlist.get_reports(stock_name)
    if not report:
        return{'error':f'No report for {stock_name}.Run analyse_stock.first'}
    return report 


#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#alert tools
@mcp.tool()
def set_price_alert(stock_name: str, condition: str, threshold: float,
                    is_persistent: bool = False, expires_days: int = 30) -> dict:
    """
    Set a price alert for a stock.
    condition: 'above' or 'below'
    threshold: price level to trigger at
    is_persistent: if True, alert never expires and resets after triggering
    expires_days: days until alert auto-deletes if not triggered (default 30)
    Example: set_price_alert('RELIANCE.NS', 'below', 1200, is_persistent=True)
    """
    return alert_watchlist.add_alert(stock_name, condition, threshold, is_persistent, expires_days)

@mcp.tool()
def view_alerts(stock_name: str = "") -> list:
    """
    View all price alerts. Optionally filter by stock name.
    """
    return alert_watchlist.get_alerts(stock_name.upper() if stock_name else None)

@mcp.tool()
def view_alert_log() -> list:
    """
    View all triggered price alerts with the price at trigger time.
    Use this to see what alerts fired and when.
    """
    return alert_watchlist.get_alert_log()

@mcp.tool()
def predict_stock(stock_name: str, horizon: int = 5) -> dict:
    """Predict short-term price direction (UP/DOWN) for a stock using the LSTM model.
    horizon: trading days ahead to predict. Takes 20-40 seconds.
    """
    price_history = find.get_price_history(stock_name, "3y")
    index_history = find.get_price_history("^NSEI", "3y")
    result = train_pred_lstm(price_history, index_history, horizon=horizon)
    edit_watchlist.save_prediction(
        stock_name=stock_name, direction=result["direction"],
        confidence=result["confidence"], accuracy=result["bd_accuracy"],
        predicted_price=result["predicted_price"], analysis_price=result["analysis_price"],
        horizon_days=result["horizon_days"],
    )   
    return result


@mcp.tool()
def get_targets(stock_name: str, period: str = "3mo") -> dict:
    """Calculate buy/sell target price levels for a stock from recent price action and fundamentals."""
    price_history = find.get_price_history(stock_name, period)
    fundamentals_data = find.get_kyc_of_stock(stock_name)
    return calculate_targets(price_history, fundamentals_data)


@mcp.tool()
def quotes(tickers: str) -> dict:
    """Get live price and change for one or more comma-separated tickers, e.g. 'RELIANCE.NS,TCS.NS'."""
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    result = []
    for sym in symbols:
        try:
            data = find.get_kyc_of_stock(sym)
            price = data.get("current_price")
            prev = data.get("previous_close")
            change = round(price - prev, 2) if price and prev else None
            change_pct = round((change / prev) * 100, 2) if change and prev else None
            result.append({
                "stock_name": sym, "company_name": data.get("company_name"),
                "current_price": price, "change": change, "change_pct": change_pct,
            })
        except Exception as e:
            result.append({"stock_name": sym, "error": str(e)})
    return {"quotes": result}


@mcp.tool()
def market_news(limit: int = 8) -> dict:
    """Get general market news headlines, not tied to a specific stock."""
    news_items = find.get_news_finnhub("general")
    return {"news": news_items[:limit]}


@mcp.tool()
def analyse_watchlist(watchlist_name: str) -> dict:
    """Run the full AI stock report for every ticker in a saved watchlist."""
    tickers = report_watchlist.get_stock(watchlist_name)
    if not tickers:
        return {"error": f"Watchlist '{watchlist_name}' not found or empty."}
    results = {}
    for stock in tickers:
        try:
            result = graph.invoke({"stock_name": stock.upper()})
            report = result.get("report") or result.get("error")
            if result.get("report"):
                report_watchlist.report(stock, report, targets=result.get("targets"))
            results[stock] = report
        except Exception as e:
            results[stock] = f"error: {str(e)}"
    return results


@mcp.tool()
def get_predictions(stock_name: str = "") -> list:
    """View past LSTM predictions, optionally filtered by ticker. Use this to find a
    prediction's id before calling add_prediction_feedback."""
    return edit_watchlist.get_predictions(stock_name.upper() if stock_name else None)


@mcp.tool()
def add_prediction_feedback(prediction_id: int, flag: str, note: str = "") -> dict:
    """Add human feedback on a past LSTM prediction.
    flag: e.g. 'correct', 'incorrect', 'unsure'.
    """
    return edit_watchlist.add_human_feedback(prediction_id, flag, note)

if __name__ == "__main__":
    mcp.run()
