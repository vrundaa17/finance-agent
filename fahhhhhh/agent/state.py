from typing import Optional,TypedDict

class AgentState(TypedDict):
    stock_name : str
    fundamentals : Optional[dict]
    history : Optional[dict]
    news_category:Optional[str]
    news : Optional[dict]
    analysis_fundamentals : Optional[str]
    analysis_news :Optional[str]
    analysis_risk :Optional[str]
    report:Optional[str]
    error : Optional[str]