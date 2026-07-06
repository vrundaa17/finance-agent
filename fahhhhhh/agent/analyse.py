import sys
sys.path.insert(0, "/Users/prashant/Desktop/fxis/task/fahhhhhh")
from langgraph.graph import StateGraph,END
from langchain_groq import ChatGroq
from agent.state import AgentState
from agent.find import get_kyc_of_stock, get_price_history, get_news_by_stock, get_news_finnhub
from dotenv import load_dotenv
import statistics


load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile",)

def fetch_fundamentals(state:AgentState):
    try:
        fundamentals = get_kyc_of_stock(state['stock_name'])
        price_history = get_price_history(state['stock_name'],period='3mo')
        return {**state, "fundamentals": fundamentals, "price_history": price_history}
    except Exception as e:
        return {**state, "error": f"fetch_fundamentals failed: {str(e)}"}
        
        
def fetch_news(state:AgentState):
    try:
        news_stock = get_news_by_stock(state['stock_name'])
        news_category = get_news_finnhub("general")  
        return {
            **state,
            "news": {"source": "yfinance", "articles": news_stock},  
            "news_category": news_category
        }
    except Exception as e:
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
    
    response = llm.invoke(prompt)
    return{**state, "analysis_fundamentals":response.content}


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
 
    response = llm.invoke(prompt)
    return {**state, "analysis_news": response.content}
 
      
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
    
    response = llm.invoke(prompt)
    return {**state, "analysis_risk": response.content}


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

        Write a professional brief that reads as a single narrative, not three separate sections.
        Start with the company name and current price. End with the risk disclaimer."""
    
    response = llm.invoke(prompt)
    return {**state, "report": response.content}



def build_graph():
    graph = StateGraph(AgentState)
    
    graph.add_node("fetch_fundamentals",fetch_fundamentals)
    graph.add_node("fetch_news",fetch_news)
    graph.add_node("analyse_fundamentals",analyse_fundamental)
    graph.add_node("analyse_news",analyse_news)
    graph.add_node("analyse_risk",analyse_risk)
    graph.add_node("compile_report",compile_report)
    
    graph.set_entry_point('fetch_fundamentals')
    graph.add_edge('fetch_fundamentals','fetch_news')
    graph.add_edge("fetch_news", "analyse_fundamentals")
    graph.add_edge("analyse_fundamentals", "analyse_news")
    graph.add_edge("analyse_news", "analyse_risk")
    graph.add_edge("analyse_risk", "compile_report")
    graph.add_edge("compile_report", END)
 
    return graph.compile()

# gr = build_graph()
# if __name__ =="__main__":
#     ans = gr.invoke({'stock_name':"ETERNAL.NS"})
#     print(ans.get("report") or ans.get("error"))