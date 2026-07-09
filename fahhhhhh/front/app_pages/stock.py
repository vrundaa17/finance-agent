import streamlit as st
import api_client as api
import logging
logger = logging.getLogger(__name__)
def stock_analysis():
    st.markdown("## 💿 Stock Analysis")
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
        run_charts = st.button("🌩️ Generate Charts Only")

    if run_report and ticker:
        with st.spinner(f"🏁 Running multi-agent analysis for {ticker.upper()}... (15-30 sec)"):
            data, err = api.api_post("/report/watchlist", {"stock_name": [ticker.upper()]})
        if err:
            logger.error(f"Failed: {err}")
            st.error(f"Try again in a while : {err}")
        elif data and data.get("reports"):
            result = data["reports"][0]
            if result.get("status") == "error":
                st.error(result.get("error", "Analysis failed"))
            else:
                st.success(f"✓ Analysis complete for {result.get('company_name', ticker)}")
                f = result.get("fundamentals", {})
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Price", f"{result.get('current_price', '—')}")
                m2.metric("P/E Ratio", f"{f.get('pe_ratio', '—'):.1f}" if f.get('pe_ratio') else "—")
                m3.metric("EPS", f"{f.get('eps', '—')}")
                m4.metric("Market Cap", api.format_large(f.get('market_cap')))
                m5.metric("Rev Growth", f"{f.get('revenue_growth', 0)*100:.1f}%" if f.get('revenue_growth') else "—")
                m6.metric("Profit Margin", f"{f.get('profit_margin', 0)*100:.1f}%" if f.get('profit_margin') else "—")

                st.divider()
                st.markdown('<div class="section-label">Daily Brief</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="report-box">{result.get("report", "No report generated.")}</div>', unsafe_allow_html=True)


            st.divider()
            st.markdown('<div class="section-label">Charts</div>', unsafe_allow_html=True)
            with st.spinner("🌩️ Generating charts..."):
                charts_data, _ = api.api_get(f"/generate_charts/{ticker.upper()}?period={period}&chart_types=price,volume,fundamentals")

            if charts_data and charts_data.get("charts"):
                charts = charts_data["charts"]
                
                c1, c2 = st.columns(2)
                if charts.get("volume"):
                    c1.image(charts["volume"], use_container_width=True)
                if charts.get("fundamentals"):
                    c2.image(charts["fundamentals"], use_container_width=True)
                if charts.get("price"):
                    st.image(charts["price"], use_container_width=True)

    if run_charts and ticker:
        with st.spinner("🌩️ Generating charts..."):
            charts_data, err = api.api_get(f"/generate_charts/{ticker.upper()}?period={period}&chart_types=price,volume,fundamentals")

        if err:
            logger.error(f"Chart error: {err}")
            st.error(f"Try again in a while : {err}")
        elif charts_data and charts_data.get("charts"):
            charts = charts_data["charts"]
            st.markdown('<div class="section-label">Charts</div>', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if charts.get("volume"):
                c1.image(charts["volume"], use_container_width=True)
            if charts.get("fundamentals"):
                c2.image(charts["fundamentals"], use_container_width=True)
            if charts.get("price"):
                st.image(charts["price"], use_container_width=True)

    today_data, _ = api.api_get("/report/today")
    today_reports = today_data.get("reports", []) if today_data else []

    with st.container(border=True):
        st.markdown(f"**👍🏻 {len(today_reports)} stock(s) analysed today**")
        if today_reports:
            with st.expander("View list"):
                for r in today_reports:
                    st.markdown(f"- **{r['stock_name']}** — {r['generated_at'][11:16]}")
                    
    st.divider()
    