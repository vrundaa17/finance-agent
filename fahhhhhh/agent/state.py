from typing import Optional,TypedDict

class AgentState(TypedDict):
    stock_name : str
    fundamentals : Optional[dict]
    price_history : Optional[dict]
    news_category:Optional[str]
    news : Optional[dict]
    analysis_fundamentals : Optional[str]
    analysis_news :Optional[str]
    analysis_risk :Optional[str]
    report:Optional[str]
    error : Optional[str]
    
    data_issues: Optional[list]
    data_ok: Optional[bool]
    risk_level:Optional[str]