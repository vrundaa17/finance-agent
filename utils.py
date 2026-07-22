from datetime import datetime
import pytz,json


IST = pytz.timezone("Asia/Kolkata")

def _today_ist():
    return datetime.now(IST).strftime("%Y-%m-%d")

def _now_is_ist():
    return datetime.now(IST).isoformat()

def _normalise_stock(stock_name:str)->str:
    stock= stock_name.strip().upper()
    
    if stock.startswith("^"):
        return stock
    if "." in stock:
        return stock
    return f"{stock}.NS"


def dumps_or_none(value):
    return json.dumps(value) if value else None

def loads_or_none(value):
    return json.loads(value) if value else None