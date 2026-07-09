import streamlit as st
from streamlit_autorefresh import st_autorefresh
from api_client import api_get, api_post
from datetime import datetime


def home():
    st.markdown("## 👾 Your finance agent ")
    st.caption(f"📅 Today is {datetime.now().strftime('%A, %d %B %Y')}")
    st_autorefresh(interval=60000, key="dashboard_refresh")
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

    st.markdown('<div class="section-label">🖋️ Quick Analysis</div>', unsafe_allow_html=True)
    qcol1, qcol2 = st.columns([3, 1])
    with qcol1:
        quick_ticker = st.text_input("Ticker", placeholder="RELIANCE.NS, AAPL, TSLA", label_visibility="collapsed")
    with qcol2:
        run_quick = st.button("Analyse →")

    if run_quick and quick_ticker:
        with st.spinner(f"🏁 Running full analysis for {quick_ticker.upper()}..."):
            data, err = api_post("/report/watchlist", {"stock_name": [quick_ticker.upper()]})
        if err:
            st.error(f"Error: {err}")
            
        elif data and data.get("reports"):
            result = data["reports"][0]
            if result.get("status") == "error":
                st.error(result.get("error", "Analysis failed"))
            else:
                st.success(f"🦾 Report generated for {data.get('company_name', quick_ticker)}")
                f = data.get("fundamentals", {})
            
                c1, c2, c3 = st.columns(3)
                c1.metric("Price", f"{result.get('current_price', '—')}")
                c2.metric("Ticker",result.get('stock', quick_ticker).upper())
                c3.metric("Company",f"{result.get('company_name', quick_ticker)}")
                st.markdown('<div class="report-box">' + (result.get('report') or 'No report.') + '</div>', unsafe_allow_html=True)

    st.divider()

    if log:
        st.markdown('<div class="section-label">😮‍💨 Recently Triggered Alerts</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-label">🏷️ Watchlist Snapshot</div>', unsafe_allow_html=True)

        default_tickers = "^NSEI,^BSESN,^NSEBANK,RELIANCE.NS"
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
                        f"{q['current_price']}",
                        f"{q['change']} ({q['change_pct']}%)" if q.get("change") is not None else None
                    )

    with col_news:
        st.markdown('<div class="section-label">📰 Market News</div>', unsafe_allow_html=True)

        news_data, news_err = api_get("/news?limit=6")
        if news_err:
            st.error(news_err)
        elif news_data and news_data.get("news"):
            st.write("DEBUG:", news_data)
            for n in news_data["news"]:
                st.markdown(f"""
                <div class="alert-row" style="flex-direction:column;align-items:flex-start;">
                    <a href="{n['url']}" target="_blank" style="color:#00d4aa;font-weight:500;text-decoration:none;">{n['headline']}</a>
                    <span style="color:#64748b;font-size:11px;">{n['source']} · {n['time']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No news available.")
