from pydantic import BaseModel,Field

class Watchlist(BaseModel):
    name: str  = Field(description="Watchlist Name", default='watchlist1')
 
class StockAdd(BaseModel):
    watchlist_name: str  = Field(description="Watchlist Name", default='watchlist1')
    stock_name: str = Field(description="StockName", default='RELIANCE.NS')
    notes: str  = Field(description="Optional Note ", default='my stock ')
    
class AlertCreate(BaseModel):
    stock_name: str
    condition: str
    threshold: float
    is_persistent: bool = False
    expire_days: int = 5
    
    
class WatchlistReportRequest(BaseModel):
    stock_name: list[str] = Field(description="Stock Name for report request", default_factory=lambda: ["RELIANCE.NS"])
    period: str  = Field(description="Time period of the data", default='1y')
    horizon: int = Field(description="Prediction horizon in days", default=5)