import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Financial AI Agent",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_URL = "http://localhost:8000"

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    [data-testid="stAppViewContainer"] { background-color: #0a0c10; color: #e2e8f0; }
    [data-testid="stSidebar"]          { background-color: #111318; border-right: 1px solid #1e2330; }
    [data-testid="stSidebar"] *        { color: #e2e8f0; }

    div[data-testid="stMetric"] {
        background: #111318;
        border: 1px solid #1e2330;
        border-radius: 10px;
        padding: 16px;
    }
    div[data-testid="stMetric"] label  { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #00d4aa; font-family: 'IBM Plex Mono', monospace; }

    .stButton > button {
        background: #00d4aa;
        color: #000;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover { background: #00b894; color: #000; }

    .stTextInput > div > input {
        background: #111318;
        border: 1px solid #1e2330;
        color: #e2e8f0;
        border-radius: 8px;
    }

    .report-box {
        background: #111318;
        border: 1px solid #1e2330;
        border-radius: 12px;
        padding: 20px 24px;
        line-height: 1.8;
        color: #cbd5e1;
        font-size: 14px;
        white-space: pre-wrap;
    }

    .alert-row {
        background: #111318;
        border: 1px solid #1e2330;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .badge-active{ background: rgba(0,212,170,0.15); color: #00d4aa; padding: 2px 8px; border-radius: 10px; }
    .badge-fired { background: rgba(239,68,68,0.15);  color: #ef4444; padding: 2px 8px; border-radius: 10px; }
    .badge-persistent{ background: rgba(245,158,11,0.15); color: #f59e0b; padding: 2px 8px; border-radius: 10px; }

    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #64748b;
        margin-bottom: 12px;
    }

    hr { border-color: #1e2330; }

    [data-testid="stSelectbox"] > div > div {
        background: #111318;
        border: 1px solid #1e2330;
        color: #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True)


def api_get(path):
    try:
        r = requests.get(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)
    
    
def api_post(path,body=None, params=None):
    try:
        r = requests.post(BASE_URL + path ,json=body, params=params,timeout=120)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)
    
def api_delete(path):
    try:
        r = requests.delete(BASE_URL + path ,timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def format_large(n):
    if not n: return "—"
    if n >= 1e12:return f"${n/1e12:.1f}T"
    if n >= 1e9:return f"${n/1e9:.1f}B"
    if n >= 1e6:return f"${n/1e6:.1f}M"
    return f"${n:,.0f}"




with st.sidebar:
    st.title("## Fahhhh")
    st.caption("helping people in there downfall")
    st.divider()
    
    page = st.radio(
        "Navigate",["🏃 Dashboard", "🚀 Stock Analysis", "💼 Portfolio", "‼️ Alerts"],
        label_visibility= "collapsed",
        )
    
    
if page=="🏃 Dashboard":
    st.markdown("Your finance help!!")
    st.caption(f"Today is {datetime.now().strftime("%A %d %B %Y")}")
    st.divider()
    
    watchlists, _ = api_get("/watchlists")
    alerts, _ = api_get("/alerts/active")
    log, _ = api_get("/alerts/log")
    
    total_stocks = sum(w.get("ticker_count", 0) for w in watchlists) if watchlists else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Watchlists",len(watchlists) if watchlists else 0)
    col2.metric("Stocks Tracked",total_stocks)
    col3.metric("Active Alerts",len(alerts) if alerts else 0)
    col4.metric("Alerts Fired",len(log) if log else 0)

    st.divider()
    
    st.markdown('<div class="section-label">Quick Check</div>',unsafe_allow_html=True)
    
    
elif page=="🚀 Stock Analysis":
    st.markdown("## Stock Analysis")
    st.divider()
    
    col1,col2 = st.columsn(2)
    with col1:
        stock_name = st.text_input("Stock Name", placeholder="RELIANCE.NS, AAPL, TCS.NS, TSLA")
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)
        
    run_col, chart_col = st.columns(2)
    with run_col:
        run_report = st.button("Generate Full Report")
    with chart_col:
        run_charts = st.button("Generate Charts Only")
        
    if run_report and stock_name:
        with st.spinner(f"Running agent anlysis for {stock_name.upper()}"):
            data, err = api_post(f"/report/{stock_name.upper()}")

        if err:
            st.error(f"Failed: {err}")
        elif data:
            st.success(f"Analysis complete for {data.get('company_name', stock_name)}")
            
        st.markdown('<div class="section-label">Key Metrics</div>', unsafe_allow_html=True)
        f = data.get("fundamentals", {})
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Price",f"${data.get('current_price', '—')}")
        m2.metric("P/E Ratio",f"{f.get('pe_ratio', '—'):.1f}" if f.get('pe_ratio') else "—")
        m3.metric("EPS",f"${f.get('eps', '—')}")
        m4.metric("Market Cap",format_large(f.get('market_cap')))
        m5.metric("Rev Growth",f"{f.get('revenue_growth', 0)*100:.1f}%" if f.get('revenue_growth') else "—")
        m6.metric("Profit Margin",f"{f.get('profit_margin', 0)*100:.1f}%" if f.get('profit_margin') else "—")
        
        