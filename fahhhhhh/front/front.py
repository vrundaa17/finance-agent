import streamlit as st
from app_pages.home import home
from app_pages.stock import stock_analysis
from app_pages.portfolio import portfolio
from app_pages.alert import alert

st.set_page_config(
    page_title="Financial AI Agent",
    page_icon="🧟‍♀️",
    layout="wide",
    initial_sidebar_state="expanded"
)


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
        font-size: 21px;
        white-space: pre-wrap;
    }

    .alert-row {
        background: #111318;
        border: 1px solid #1e2330;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .badge-active{ background: rgba(0,212,170,0.15); color: #00d4aa; padding: 2px 8px; border-radius: 10px; }
    .badge-fired { background: rgba(239,68,68,0.15);  color: #ef4444; padding: 2px 8px; border-radius: 10px; }
    .badge-persistent{ background: rgba(245,158,11,0.15); color: #f59e0b; padding: 2px 8px; border-radius: 10px; }

    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 16px;
        font-weight:bold;
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
    div[role="radiogroup"] {
        gap: 6px;
    }
    div[role="radiogroup"] label {
        background: #111318;
        border: 1px solid #1e2330;
        border-radius: 8px;
        padding: 10px 14px;
        width: 100%;
        cursor: pointer;
    }
    div[role="radiogroup"] label:hover {
        border-color: #00d4aa;
    }
    div[role="radiogroup"] input:checked + div {
        color: #00d4aa;
    }
    div[role="radiogroup"] label > div:first-child {
        display: none;
}
    </style>
    """,
    unsafe_allow_html=True)




with st.sidebar:
    st.markdown("### Financial AI Agent")
    st.caption("Market intelligence")
    st.divider()

    page = st.radio(
        "Navigate",
        ["🏃 Dashboard", "🚀 Stock Analysis", "💼 Portfolio", "‼️ Alerts"],
        label_visibility="collapsed"
    )



if page == "🏃 Dashboard":
    home()
    
elif page == "🚀 Stock Analysis":
    stock_analysis()
    
elif page == "💼 Portfolio":
    portfolio()

elif page == "‼️ Alerts":
    alert()