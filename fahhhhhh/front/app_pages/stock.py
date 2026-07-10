import streamlit as st
import api_client as api
import logging
logger = logging.getLogger(__name__)
def stock_analysis():
    settings = st.session_state.get("settings", {
        "show_charts": True, "show_predictions": True,
        "show_targets": True, "currency_symbol": "₹"
    })
    pred_settings = st.session_state.get("pred_settings", {"training_period": "2y"})
    
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
            st.error(err)
        elif data and data.get("reports"):
            result = data["reports"][0]
            if result.get("status") == "error":
                st.error(result.get("error", "Analysis failed"))
            else:
                if settings["show_predictions"]:
                    st.markdown('<div class="section-label">ML Prediction (Experimental)</div>', unsafe_allow_html=True)
                    with st.spinner("Training model on price history..."):
                        pred, perr = api.api_get(f"/predict/{ticker.upper()}?period={pred_settings['training_period']}")

                    if perr:
                        st.error(perr)
                    elif pred and not pred.get("error"):
                        p1, p2, p3 = st.columns(3)
                        p1.metric("Next Day Direction", pred["direction"])
                        p2.metric("Confidence",f"{pred['confidence']}%")
                        p3.metric("Backtest Accuracy",f"{pred['accuracy']}%")
                        
                        with st.expander("**Top signals used by model:**"):
                            for sig in pred["top_signals"]:
                                st.markdown(f"<h5>- {sig['feature']}  —  importance: {sig['importance']}</h5>",unsafe_allow_html=True)
                        st.caption(f"⚠️ {pred['disclaimer']}")
                    
                    st.divider()
                    
                    
                if settings["show_targets"]:
                    st.markdown('<div class="section-label">Buy / Sell Targets [Mathematically] </div>', unsafe_allow_html=True)
                    with st.spinner("Mathematically Calculating level..."):
                        t,terr = api.api_get(f"/target/{ticker.upper()}?periods={period}")
                    
                    if terr:
                        st.error(f"Targets error: {terr}")
                    elif t and not t.get("error"):
                        with st.container(border=True):
                            tc1,tc2,tc3,tc4 = st.columns(4)
                            tc1.metric("Current Price", f"{settings['currency_symbol']}{t['current_price']}")
                            tc2.metric(
                                "Buy Target",
                                f"{t['buy_target']['level']}" if t.get('buy_target') else "—",
                                delta=f"{t['buy_target']['strength']}" if t.get('buy_target') else None
                            )
                            tc3.metric(
                                "Sell Target",
                                f"{t['sell_target']['level']}" if t.get('sell_target') else "—",
                                delta=f"{t['sell_target']['strength']}" if t.get('sell_target') else None
                            )
                            tc4.metric(
                                "Stop Loss",
                                f"{t['stop_loss']['level']}" if t.get('stop_loss') else "-"
                            )
                            if t.get("risk_reward"):
                                rating = "Favourable" if t['risk_reward'] >=2 else "Acceptable" if t['risk_reward']>=1 else "Poor"
                                st.info(f"Risk/Reward Ratio: **{t['risk_reward']} :1** -{rating}")
                        
                            sl, rl = st.columns(2)
                            with sl:
                                st.markdown("**Support Levels**")
                                for s in t.get("support_levels",[]):
                                    st.markdown(f"<h5>{s['level']} - {s['strength']} {s['touches']}</h5>",unsafe_allow_html=True)
                                    
                            with rl:
                                st.markdown("**Resistance Levels**")
                                for r in t.get("resistance_levels",[]):
                                    st.markdown(f"<h5>{r['level']} — {r['strength']} ({r['touches']} touches)</h5>",unsafe_allow_html=True)
                                    
                    st.caption("⚠️ This is not financial advice. Consult a licensed financial advisor before trading.")

                st.divider()
                st.success(f"✓ Analysis complete for {result.get('company_name', ticker)}")
                f = result.get("fundamentals", {})
                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Price", f"{settings['currency_symbol']}{result.get('current_price', '—')}")
                m2.metric("P/E Ratio", f"{f.get('pe_ratio', '—'):.1f}" if f.get('pe_ratio') else "—")
                m3.metric("EPS", f"{f.get('eps', '—')}")
                m4.metric("Market Cap", api.format_large(f.get('market_cap')))
                m5.metric("Rev Growth", f"{f.get('revenue_growth', 0)*100:.1f}%" if f.get('revenue_growth') else "—")
                m6.metric("Profit Margin", f"{f.get('profit_margin', 0)*100:.1f}%" if f.get('profit_margin') else "—")

                st.divider()
                st.markdown('<div class="section-label">Daily Brief</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="report-box">{result.get("report", "No report generated.")}</div>', unsafe_allow_html=True)

                st.divider()   
            
                if settings["show_charts"]:
                    st.markdown('<div class="section-label">Charts</div>', unsafe_allow_html=True)
                    with st.spinner("🌩️ Generating charts..."):
                        charts_data, charts_err = api.api_get(f"/generate_charts/{ticker.upper()}?period={period}&chart_types=price,volume,fundamentals")

                    if charts_err:
                        st.warning(f"Charts unavailable: {charts_err}")
                    elif charts_data and charts_data.get("charts"):
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
            st.error(err)
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
    