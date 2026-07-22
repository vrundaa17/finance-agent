import yfinance as yf
import finnhub 
import pandas as pd
import os,utils
from core.cache import r, check_ratelimit
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
from dotenv import load_dotenv
import logging 
logger = logging.getLogger(__name__)
load_dotenv()
client = finnhub.Client(api_key= os.getenv("FINHUB_API"))



def get_kyc_of_stock(sname):
    if not check_ratelimit("yfinance",limit=100,window=60):
        raise ValueError("too many requests to yfinance")
    cached = r.get(f"kyc:{sname}")
    if cached:
        return utils.loads_or_none(cached)
    
    stock = yf.Ticker(utils._normalise_stock(sname))
    info = stock.info
    
    if not info or (info.get("currentPrice") is None and info.get("regularMarketPrice") is None):
        logger.error(f"Stock not there : {sname}")
        raise ValueError(f"'{sname}' is not a valid stock symbol")
    
    
    result= {
        "stock_name": sname.upper(),
        "company_name": info.get("longName", "N/A"),
        "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "industry" : info.get("industry"),
        "profit_margin": info.get("profitMargins"),
        "5_year_dividend":info.get("fiveYearAvgDividendYield"),
        
        "previous_close": info.get("previousClose"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "sector": info.get("sector"),
        
        "52_week_high":info.get("fiftyTwoWeekHigh"),
        "52_week_low":info.get("fiftyTwoWeekLow"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
    }
    r.set(f"kyc:{sname}",utils.dumps_or_none(result), ex=120)
    return result
    

def get_price_history(sname,period='5d'):
    if not check_ratelimit("yfinance",limit=600,window=60):
        raise ValueError("too many requests to yfinance")
    
    cached = r.get(f"price_history:{sname}:{period}")
    if cached:
        return utils.loads_or_none(cached)
    
    stock = yf.Ticker(utils._normalise_stock(sname))
    hist = stock.history(period=period)
    if hist.empty:
        logger.error(f"{sname} - no history ")
        raise ValueError("No history for the selected stock.")
    result= {
        "stock_name": sname.upper(),
        "dates": hist.index.strftime("%Y-%m-%d").tolist(),
        "close": hist["Close"].round(2).tolist(),
        "open": hist["Open"].round(2).tolist(),
        "high": hist["High"].round(2).tolist(),
        "low": hist["Low"].round(2).tolist(),
        "volume": hist["Volume"].tolist(),
    }
    r.set(f"price_history:{sname}:{period}", utils.dumps_or_none(result), ex=300)
    return result
    
def get_statement(sname,types='balance_sheet'):
    stock = yf.Ticker(utils._normalise_stock(sname))
    
    statement ={
        'balance_sheet': stock.balance_sheet,
        'dividend':stock.dividends,
        'cash_flow':stock.cashflow,
        'financials': stock.financials,
        "income_stmt": stock.income_stmt,
        'splits': stock.splits,
        'actions':stock.actions,
        "quarterly_balance_sheet": stock.quarterly_balance_sheet,
        "quarterly_income_stmt": stock.quarterly_income_stmt,
        "quarterly_cashflow": stock.quarterly_cashflow,
    }
    result ={}
    
    selected = types if isinstance(types ,list) else [types]
    for t in selected:
        data = statement.get(t)
        # print(t, type(data))
        if data is None or data.empty:
            continue
        if isinstance(data,pd.DataFrame):
            result[t]={
                'index': data.index.tolist(),
                'columns' : data.columns.astype(str).tolist(),
                'values' : data.fillna(" ").values.tolist(),
            }
        elif isinstance(data, pd.Series):
            result[t] = {
                "index": data.index.astype(str).tolist(),
                "values": data.fillna("").tolist()
            }
        
    return result


def get_news_by_stock(sname):
    cached = r.get(f"news:{sname}")
    if cached:
        return utils.loads_or_none(cached)
    
    stock = yf.Ticker(utils._normalise_stock(sname))
    news = stock.news
    if not news:
        raise ValueError("no recent news ")
    
    info =[]
    for item in news:
        content = item.get("content",{})
        info.append({
            'title':content.get("title"),
            'summary':content.get("summary"),
            'date' : content.get('pubDate'),
            "source": content.get("provider",{}).get("displayName"),
            "url" : content.get("canonicalUrl",{}).get("url")
        })
    r.set(f"news:{sname}",utils.dumps_or_none(info),ex=600) 
    return info


def get_news_finnhub(category="general"):
    cached = r.get(f"news:{category}")
    if cached:
        return utils.loads_or_none(cached)
    
    news = client.general_news(category)
    if not news:
        raise ValueError("No news found")
    result= [{
        'headline': item.get('headline',''),
        "summary": item.get("summary",''),
        "source": item.get("source",''),
        "url": item.get("url",''),
        "time": item.get("datetime",'')
        
    }for item in news]
    r.set(f"news:{category}",utils.dumps_or_none(result),ex=900)
    return result
    
