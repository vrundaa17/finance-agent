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

#-------------------------------------------------------------------------------------------------------------------------------------------

def api_get(path):
    try:
        r = requests.get(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_post(path, body=None, params=None):
    try:
        r = requests.post(BASE_URL + path, json=body, params=params, timeout=120)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def api_delete(path):
    try:
        r = requests.delete(BASE_URL + path, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, str(e)

def format_large(n):
    if not n: return "—"
    if n >= 1e12:return f"${n/1e12:.1f}T"
    if n >= 1e9:return f"${n/1e9:.1f}B"
    if n >= 1e6:return f"${n/1e6:.1f}M"
    return f"{n:,.0f}"

#-------------------------------------------------------------------------------------------------------------------------------------

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
    st.markdown("## Your finance agent ")
    st.caption(f"Today is {datetime.now().strftime('%A, %d %B %Y')}")
    st.divider()

    watchlists, _ = api_get("/watchlists")
    alerts, _ = api_get("/alerts/active")
    log, _ = api_get("/alerts/logs")

    total_stocks = sum(w.get("ticker_count", 0) for w in watchlists) if watchlists else 0
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Watchlists",len(watchlists) if watchlists else 0)
    col2.metric("Stocks Tracked",total_stocks)
    col3.metric("Active Alerts",len(alerts) if alerts else 0)
    col4.metric("Alerts Fired",len(log) if log else 0)

    st.divider()

    st.markdown('<div class="section-label">Quick Analysis</div>', unsafe_allow_html=True)
    qcol1, qcol2 = st.columns([3, 1])
    with qcol1:
        quick_ticker = st.text_input("Ticker", placeholder="RELIANCE.NS, AAPL, TSLA", label_visibility="collapsed")
    with qcol2:
        run_quick = st.button("Analyse →")

    if run_quick and quick_ticker:
        with st.spinner(f"Running full analysis for {quick_ticker.upper()}..."):
            data, err = api_post(f"/report/{quick_ticker.upper()}")
        if err:
            st.error(f"Error: {err}")
        elif data:
            st.success(f"Report generated for {data.get('company_name', quick_ticker)}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Price",f"${data.get('current_price', '—')}")
            c2.metric("Ticker",data.get('stock', quick_ticker).upper())
            c3.metric("Company",data.get('company_name', '—'))
            st.markdown('<div class="report-box">' + (data.get('report') or 'No report.') + '</div>', unsafe_allow_html=True)

    st.divider()

    if log:
        st.markdown('<div class="section-label">Recently Triggered Alerts</div>', unsafe_allow_html=True)
        for a in log[:5]:
            st.markdown(f"""
            <div class="alert-row">
                <span style="color:#00d4aa;font-weight:500">{a['stock_name']}</span>
                <span style="color:#64748b">{a['condition']} {a['threshold']}</span>
                <span style="color:#ef4444">triggered @ {a['price_at_trigger']}</span>
                <span style="color:#64748b">{a.get('triggered_at','')[:16]}</span>
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        
    col_stocks, col_news = st.columns(2)

    with col_stocks:
        st.markdown('<div class="section-label">Watchlist Snapshot</div>', unsafe_allow_html=True)

        default_tickers = "AAPL,TSLA,MSFT,GOOGL,RELIANCE.NS"
        quotes_data, qerr = api_get(f"/quotes?tickers={default_tickers}")

        if qerr:
            st.error(qerr)
        elif quotes_data and quotes_data.get("quotes"):
            for q in quotes_data["quotes"]:
                if q.get("error"):
                    st.metric(q["stock_name"], "—", "error")
                else:
                    st.metric(
                        q["stock_name"],
                        f"${q['current_price']}",
                        f"{q['change']} ({q['change_pct']}%)" if q.get("change") is not None else None
                    )

    with col_news:
        st.markdown('<div class="section-label">Market News</div>', unsafe_allow_html=True)

        news_data, news_err = api_get("/news?limit=6")
        if news_err:
            st.error(news_err)
        elif news_data and news_data.get("news"):
            for n in news_data["news"]:
                st.markdown(f"""
                <div class="alert-row" style="flex-direction:column;align-items:flex-start;">
                    <a href="{n['url']}" target="_blank" style="color:#00d4aa;font-weight:500;text-decoration:none;">{n['headline']}</a>
                    <span style="color:#64748b;font-size:11px;">{n['source']} · {n['time']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news available.")


elif page == "🚀 Stock Analysis":
    st.markdown("## Stock Analysis")
    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Stock ticker", placeholder="RELIANCE.NS, AAPL, TCS.NS, TSLA")
    with col2:
        period = st.selectbox("Period", ["1mo", "3mo", "6mo", "1y"], index=1)

    run_col, chart_col = st.columns(2)
    with run_col:
        run_report = st.button("🤖 Generate Full Report")
    with chart_col:
        run_charts = st.button("📈 Generate Charts Only")

    if run_report and ticker:
        with st.spinner(f"Running multi-agent analysis for {ticker.upper()}... (15-30 sec)"):
            data, err = api_post(f"/report/{ticker.upper()}")

        if err:
            st.error(f"Failed: {err}")
        elif data:
            st.success(f"✓ Analysis complete for {data.get('company_name', ticker)}")

            # metrics
            st.markdown('<div class="section-label">Key Metrics</div>', unsafe_allow_html=True)
            f = data.get("fundamentals", {})
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Price",f"{data.get('current_price', '—')}")
            m2.metric("P/E Ratio",f"{f.get('pe_ratio', '—'):.1f}" if f.get('pe_ratio') else "—")
            m3.metric("EPS",f"{f.get('eps', '—')}")
            m4.metric("Market Cap",format_large(f.get('market_cap')))
            m5.metric("Rev Growth",f"{f.get('revenue_growth', 0)*100:.1f}%" if f.get('revenue_growth') else "—")
            m6.metric("Profit Margin",f"{f.get('profit_margin', 0)*100:.1f}%" if f.get('profit_margin') else "—")

            st.divider()

            st.markdown('<div class="section-label">Daily Brief</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="report-box">{data.get("report", "No report generated.")}</div>', unsafe_allow_html=True)


            st.divider()
            st.markdown('<div class="section-label">Charts</div>', unsafe_allow_html=True)
            with st.spinner("Generating charts..."):
                charts_data, cerr = api_get(f"/generate_charts/{ticker.upper()}?period={period}&chart_types=price,volume,fundamentals")

            if charts_data and charts_data.get("charts"):
                charts = charts_data["charts"]
                if charts.get("price"):
                    st.image(charts["price"], use_container_width=True)
                c1, c2 = st.columns(2)
                if charts.get("volume"):
                    c1.image(charts["volume"], use_container_width=True)
                if charts.get("fundamentals"):
                    c2.image(charts["fundamentals"], use_container_width=True)

    if run_charts and ticker:
        with st.spinner("Generating charts..."):
            charts_data, err = api_get(f"/generate_charts/{ticker.upper()}?period={period}&chart_types=price,volume,fundamentals")

        if err:
            st.error(f"Chart error: {err}")
        elif charts_data and charts_data.get("charts"):
            charts = charts_data["charts"]
            st.markdown('<div class="section-label">Charts</div>', unsafe_allow_html=True)
            if charts.get("price"):
                st.image(charts["price"], use_container_width=True)
            c1, c2 = st.columns(2)
            if charts.get("volume"):
                c1.image(charts["volume"], use_container_width=True)
            if charts.get("fundamentals"):
                c2.image(charts["fundamentals"], use_container_width=True)



elif page == "💼 Portfolio":
    st.markdown("## Watchlists")
    st.divider()

 
    with st.expander("➕ Create New Watchlist"):
        new_name = st.text_input("Watchlist name", placeholder="uncle_portfolio, tech_stocks...")
        if st.button("Create"):
            if new_name.strip():
                res, err = api_post("/watchlists", {"name": new_name.strip()})
                if err:st.error(err)
                else:st.success(f"Created '{new_name}'"); st.rerun()
            else:
                st.warning("Enter a name.")

    watchlists, err = api_get("/watchlists")
    if err: st.error(err)
    elif not watchlists:
        st.info("No watchlists yet — create one above.")
    else:
        for wl in watchlists:
            name  = wl["name"]
            count = wl["ticker_count"]

            with st.container(border=True):
                h1, h2, h3 = st.columns([7, 1, 1])
                with h1:
                    st.markdown(f"### {name}")
                    st.caption(f"{count} stocks")
                with h2:
                    if st.button("Analyse", key=f"brief_{name}"):
                        st.session_state[f"run_brief_{name}"] = True
                with h3:
                    if st.button("🗑️", key=f"del_wl_{name}", help="Delete watchlist"):
                        api_delete(f"/watchlists/{name}")
                        st.rerun()


                stocks_data, _ = api_get(f"/watchlists/{name}")
                stocks = stocks_data.get("stock_name", []) if stocks_data else []

                if stocks:
                    selected = []
                    for stock in stocks:
                        s1, s2 = st.columns([9, 1])
                        with s1:
                            checked = st.checkbox(stock, key=f"check_{name}_{stock}")
                            if checked: selected.append(stock)
                        with s2:
                            if st.button("×", key=f"rm_{name}_{stock}"):
                                api_delete(f"/watchlists/{name}/{stock}")
                                st.rerun()
                else:
                    st.info("No stocks yet.")


                a1, a2 = st.columns([4, 1])
                with a1:
                    new_ticker = st.text_input("Add stock", placeholder="RELIANCE.NS", key=f"inp_{name}", label_visibility="collapsed")
                with a2:
                    if st.button("Add", key=f"add_{name}"):
                        if new_ticker.strip():
                            res, err = api_post("/watchlists/add", {
                                "watchlist_name": name,
                                "stock_name": new_ticker.strip().upper(),
                                "notes": ""
                            })
                            if err: st.error(err)
                            else:st.success(f"Added {new_ticker.upper()}"); st.rerun()

                # run morning brief
                if st.session_state.get(f"run_brief_{name}"):
                    st.session_state[f"run_brief_{name}"] = False
                    if not stocks:
                        st.warning("No stocks in this watchlist.")
                    else:
                        with st.spinner(f"Running morning brief for {name}... ({len(stocks)} stocks)"):
                            data, err = api_post(f"/report/watchlist/{name}")

                        if err:
                            st.error(f"Error: {err}")
                        elif data:
                            st.success(f"✓ {data['successful']}/{data['total']} reports generated")
                            for r in data["reports"]:
                                with st.expander(f"{r.get('company_name', r['stock'])} — {r['stock']} {'✓' if r['status']=='success' else '✗'}"):
                                    if r.get("current_price"):
                                        st.metric("Price", f"${r['current_price']}")
                                    if r.get("report"):
                                        st.markdown(f'<div class="report-box">{r["report"]}</div>', unsafe_allow_html=True)
                                    if r.get("error"):
                                        st.error(r["error"])


elif page == "‼️ Alerts":
    st.markdown("## Price Alerts")
    st.divider()

    # create alert
    st.markdown('<div class="section-label">Set New Alert</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 ,c6= st.columns([2, 2, 2, 2,2, 1])
    with c1:
        a_ticker = st.text_input("Ticker", placeholder="AAPL", label_visibility="collapsed")
    with c2:
        a_condition = st.selectbox("Condition", ["below", "above"], label_visibility="collapsed")
    with c3:
        a_threshold = st.number_input("Price", min_value=0.0, step=1.0, label_visibility="collapsed")
    with c4:
        a_persistent = st.selectbox("Y/N",["True","False"],label_visibility="collapsed")
    with c5:
        a_days = st.number_input("Days", min_value=1, step=1, label_visibility="collapsed")
    with c6:
        set_alert = st.button("Set →")
    
    if set_alert:
        if a_ticker and a_threshold > 0:

            res, err = api_post(
                "/alerts",
                params={
                    "stock_name": a_ticker.upper(),
                    "condition": a_condition,
                    "threshold": float(a_threshold),
                    "is_persistent": True if a_persistent == "True" else False,
                    "expire_days": int(a_days)
                }
            )
            if err:
                st.error(err)
            else:
                st.success("Alert created!")
                st.json(res)
                st.rerun()

        else:
            st.warning("Enter ticker and threshold.")

    st.divider()


    st.markdown('<div class="section-label">Active Alerts</div>', unsafe_allow_html=True)
    active, err = api_get("/alerts/active")
    if err: st.error(err)
    elif not active:
        st.info("No active alerts. Set one above.")
    else:
        for a in active:
            badge = '<span class="badge-persistent">persistent</span>' if a.get("is_persistent") else '<span class="badge-active">watching</span>'
            expires = a.get("expires_at", "")[:10] if a.get("expires_at") else "—"

            row_col, btn_col = st.columns([9, 1])
            with row_col:
                st.markdown(f"""
                <div class="alert-row">
                    <span style="color:#00d4aa;font-weight:500;min-width:120px">{a['stock_name']}</span>
                    <span style="color:#64748b">{a['condition']}</span>
                    <span style="color:#e2e8f0;font-weight:500">{a['threshold']}</span>
                    <span style="color:#64748b">expires {expires}</span>
                    {badge}
                </div>
                """, unsafe_allow_html=True)
            with btn_col:
                if st.button("❌", key=f"del_alert_{a['id']}"):
                    res, derr = api_delete(f"/alerts/{a['id']}")
                    if derr:
                        st.error(derr)
                    else:
                        st.rerun()
    st.divider()


    st.markdown('<div class="section-label">Triggered Alerts Log</div>', unsafe_allow_html=True)
    log, err = api_get("/alerts/logs")
    if err: st.error(err)
    elif not log:
        st.info("No alerts have triggered yet.")
    else:
        for a in log:
            st.markdown(f"""
            <div class="alert-row">
                <span style="color:#00d4aa;font-weight:500;min-width:120px">{a['stock_name']}</span>
                <span style="color:#64748b">{a['condition']} {a['threshold']}</span>
                <span style="color:#ef4444">triggered @ {a['price_at_trigger']}</span>
                <span style="color:#64748b">{a.get('triggered_at','')[:16]}</span>
                <span class="badge-fired">fired</span>
            </div>
            """, unsafe_allow_html=True)