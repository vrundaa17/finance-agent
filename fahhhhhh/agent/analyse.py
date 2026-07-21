import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langgraph.graph import StateGraph,END
from langchain_groq import ChatGroq
from agent.state import AgentState
from agent.target import calculate_targets
from agent.find import get_kyc_of_stock, get_price_history, get_news_by_stock, get_news_finnhub
from dotenv import load_dotenv
import statistics
from core.cache import r, cached_llm_call
import logging
logger = logging.getLogger(__name__)

load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile",)
    
def fetch_fundamentals(state:AgentState):
    try:
        fundamentals = get_kyc_of_stock(state['stock_name'])
        price_history = get_price_history(state['stock_name'],period='3mo')
        logger.info(f"Fetched fundamentals : {state['stock_name']}")
        return {**state, "fundamentals": fundamentals, "price_history": price_history}
    except Exception as e:
        logger.error(f"Fetch Fundamentals failed {state['stock_name']} : {str(e)}")
        return {**state, "error": f"fetch_fundamentals failed: {str(e)}"}
        
        
def fetch_news(state:AgentState):
    if state.get("error"):
        return state
    try:
        news_stock = get_news_by_stock(state['stock_name'])
        news_category = get_news_finnhub("general")  
        logger.info(f"Fetched News : {state['stock_name']}")
        return {
            **state,
            "news": {"source": "yfinance", "articles": news_stock},  
            "news_category": news_category
        }
    except Exception as e:
        logger.error(f"Fetch News failed {state['stock_name']} : {str(e)}")
        return {**state, "error": f"fetch_news failed: {str(e)}"} 
    
    
def analyse_fundamental(state:AgentState):
    if state.get("error") or not state.get("fundamentals"):
        return state
    
    data = state['fundamentals']
    prompt = f"""
        You are a financial analyst. Analyze the following fundamentals for {data['company_name']} ({data['stock_name']}) and 
        write a concise 3-4 sentence interpretation. 
        Focus on what the numbers mean, not just what they are. 
        Highlight any significant strengths or concerns.
        
        Fundamentals:
        - Current Price: {data['current_price']}
        - P/E Ratio: {data['pe_ratio']}
        - Forward P/E: {data['forward_pe']}
        - EPS: {data['eps']}
        - Revenue Growth: {data['revenue_growth']}
        - Profit Margin: {data['profit_margin']}
        - Debt to Equity: {data['debt_to_equity']}
        - Market Cap: {data['market_cap']}
        - Sector: {data['sector']}
        - 52-Week High: {data['52_week_high']}
        - 52-Week Low: {data['52_week_low']}
        
        Write your analysis in plain English, no bullet points.
    """
    
    content = cached_llm_call("fundamental",llm,prompt)
    logger.info(f"Analysed Fundamentals {state['stock_name']}")
    return{**state, "analysis_fundamentals":content}



def analyse_news(state: AgentState):
    if state.get("error") or not state.get("news"):
        return state
 
    articles = state['news']['articles']
    source = state['news']['source']
 
    headlines = "\n".join(
        f"- [{a['date']}] {a['title']} ({a['source']})"
        for a in articles if a.get("title")
    )
 
    prompt = f"""You are a financial news analyst. Below are recent headlines for {state['stock_name']} from {source}.
        Write a concise 3-4 sentence summary covering: overall sentiment (bullish/bearish/neutral), the 1-2 most significant events, and any notable analyst opinions or market reactions.
        Be specific — mention company names, percentages, or event details where available.
        
        Headlines:
        {headlines}
        
        Write in plain English, no bullet points."""
 
    content = cached_llm_call("news",llm,prompt)
    logger.info(f"Analysed News : {state['stock_name']}")
    return {**state, "analysis_news": content}
 
      
def analyse_risk(state:AgentState):
    if state.get("error") or not state.get("price_history"):
        return state
    closes = state["price_history"]["close"]
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    volatility = round(statistics.stdev(returns) * 100, 2) if len(returns) > 1 else None
    max_price = max(closes)
    high_52 = state["fundamentals"].get("52_week_high")
    low_52 = state["fundamentals"].get("52_week_low")
    min_after_max = min(closes[closes.index(max_price):])
    max_drawdown = round((min_after_max - max_price) / max_price * 100, 2)
    current = closes[-1]
    pct_from_high = round((current - high_52) / high_52 * 100, 2) if high_52 else None
    
    prompt =f"""
        You are a risk analyst. Write a concise 3-4 sentence risk assessment for {state['stock_name']} based on these computed metrics. 
        Include a balanced view and end with a one-sentence risk rating (Low / Moderate / High) with justification.
        Always end with: "This is not financial advice. Consult a licensed financial advisor before making investment decisions."
        
        Computed risk metrics:
        - Daily return volatility (3-month): {volatility}%
        - Max drawdown (3-month): {max_drawdown}%
        - Current price vs 52-week high: {pct_from_high}%
        - Current price: {current}
        - Debt to equity: {state['fundamentals'].get('debt_to_equity')}
        - Profit margin: {state['fundamentals'].get('profit_margin')}
        
        Write in plain English, no bullet points.
    """
    
    content = cached_llm_call("risk",llm,prompt)
    logger.info(f"Analysed Risk : {state['stock_name']}")
    return {**state, "analysis_risk": content}


def compile_report(state:AgentState):
    if state.get("error"):
        return {**state, "report": f"Report generation failed: {state['error']}"}
    stock_name = state['stock_name']
    company = state['fundamentals'].get("company_name",stock_name)
    price = state['fundamentals'].get('current_price')
    
    prompt = f"""You are a senior financial analyst writing a daily market brief for a professional financial advisor.
        Combine the following three analysis sections into one cohesive report for {company} ({stock_name}).
        Current price: {price}

        --- FUNDAMENTALS ANALYSIS
        {state.get('analysis_fundamentals', 'Not available')}

        --- NEWS ANALYSIS 
        {state.get('analysis_news', 'Not available')}

        --- RISK ASSESSMENT
        {state.get('analysis_risk', 'Not available')}
        
        --- BUY/SELL TARGETS
        {state.get('targets', {}).get('summary', 'Not available')}

        Write a professional brief that reads 4 separate sections explaining about every detail.
        The risk assessment is a must. Be realistic about it not assumption.
        Start with the company name and current price. End with the risk disclaimer."""
    
    content = cached_llm_call("report",llm,prompt)
    logger.info(f"Report compiled : {state['stock_name']}")
    return {**state, "report": content}



def check_data_quality(state:AgentState):
    if state.get("error"):
        return state
    
    f = state.get("fundamentals",{})
    history = state.get("price_history",{})
    logger.info(f"Checking DATA QUALITY : {state['stock_name']}")
    
    issues =[]
    if not f.get("current_price"):
        issues.append("price unavailable")
    if not f.get("pe_ratio"):
        issues.append("P/E ratio not available")
    if len(history.get("close", [])) < 20:
        issues.append("insufficient price history for risk calculation")
    return {**state, "data_issues": issues, "data_ok": len(issues) == 0}



def route_after_data_check(state:AgentState):
    if state.get("data_ok"):
        return "analyse_fundamentals"
    return "partial_report"


def partial_report(state:AgentState):
    if state.get("error"):
        return state
    issues = state.get("data_issues",[])
    f = state.get("fundamentals",{})
    report = f"""
        Limited report for {state['stock_name']} - {','.join(issues)}.
        Available Data:
        - Company : {f.get('company_name','Unknown')}
        - Price : {f.get('current_price',"Unavailable")}
        - Sector : {f.get('sector','Unknown')}
        Full analysis can not be carried out.
        This is not a financial advice.
        Try again after few minutes.
        Thank you for your understanding!"""
    return {**state, "report": report}


def route_after_fundamentals(state:AgentState):
    f = state.get("fundamentals",{})
    closes = state.get("price_history",{}).get("close",[])
    high_risk = False
    if f.get("debt_to_equity") and f['debt_to_equity']>200:
        high_risk = True
        
    if closes:
        high = max(closes)
        current = closes[-1]
        if (current - high)/high <-0.3:
            high_risk = True
    if f.get("profit_margin") and f["profit_margin"]<0:
        high_risk =True
        
        
    news = state.get("news", {})
    articles = news.get("articles", []) if news else []
    has_news = len(articles) > 0
    
    if high_risk and has_news:
        return "high_risk_analysis"
    if high_risk and not has_news:
        return "high_risk_analysis"
    if not has_news:
        return "analyse_risk"
    
    return "analyse_news"
    # return "high_risk_analysis" if high_risk else "analyse_news"


def high_risk_analysis(state:AgentState):
    f = state.get("fundamentals",{})
    closes = state.get("price_history",{}).get("close",[])
    prompt=f"""
        You are a senior risk analyst. This stock has triggered HIGH RISK signals.
        Write a detailed 4-5 sentence risk warning for {state['stock_name']}.
        Be specific about the risks. Be direct — this is for a professional advisor.

        Risk signals detected:
        - Closes : {closes}
        - Debt to Equity: {f.get('debt_to_equity')}
        - Profit Margin: {f.get('profit_margin')}
        - Current vs 52w High: {f.get('current_price')} vs {f.get('52_week_high')}

        End with: HIGH RISK RATING. This is not financial advice.
    """
    response = llm.invoke(prompt)
    return {**state, "analysis_risk":response.content, "risk_level":"HIGH"}


def analyse_targets(state: AgentState):
    if state.get("error") or not state.get("price_history"):
        return state
    targets = calculate_targets(
        state["price_history"],
        state["fundamentals"]
    )
    return {**state, "targets": targets}


# def route_after_news_fetch(state:AgentState):
    news = state.get("news",{})
    articles = news.get("articles",[]) if news else []
    
    if not articles:
        return "analyse_risk"
    return "analyse_news"
    
        
        
def build_graph():
    # l
    # stock - news - check 
    #                 route - partial
    #                       - analyse fun -high risk |  anal news -
    #                                           
    graph = StateGraph(AgentState)
    
    graph.add_node("fetch_fundamentals",fetch_fundamentals)
    graph.add_node("fetch_news",fetch_news)
    graph.add_node("check_data_quality",check_data_quality)
    graph.add_node("partial_report",partial_report)
    graph.add_node("analyse_fundamentals",analyse_fundamental)
    graph.add_node("analyse_news",analyse_news)
    graph.add_node("high_risk_analysis",high_risk_analysis)
    graph.add_node("analyse_risk",analyse_risk)
    graph.add_node("compile_report",compile_report)
    graph.add_node("analyse_targets", analyse_targets)
    
    graph.set_entry_point('fetch_fundamentals')
    
    graph.add_edge('fetch_fundamentals','fetch_news')
    graph.add_edge('fetch_news', 'check_data_quality') 
    graph.add_conditional_edges(
        "check_data_quality", route_after_data_check,{
            "analyse_fundamentals":"analyse_fundamentals",
            "partial_report":"partial_report",
        } )
    graph.add_conditional_edges(
        "analyse_fundamentals", route_after_fundamentals, {
            'high_risk_analysis': 'high_risk_analysis',
            'analyse_news': 'analyse_news',
            'analyse_risk': 'analyse_risk',
        }
    )
    graph.add_edge("high_risk_analysis","analyse_news")
    graph.add_edge("analyse_news","analyse_risk")
    graph.add_edge("analyse_risk","analyse_targets")
    graph.add_edge("analyse_targets","compile_report")
    graph.add_edge("partial_report", END)
    graph.add_edge("compile_report", END)
    logger.info("Graph compiled...")
    return graph.compile()

# gr = build_graph()
# if __name__ =="__main__":
#     ans = gr.invoke({'stock_name':"ETERNAL.NS"})
#     print(ans.get("report") or ans.get("error"))


