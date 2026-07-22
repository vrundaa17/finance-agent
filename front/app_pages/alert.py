import streamlit as st
import api_client as api
import logging
logger = logging.getLogger(__name__)
def alert():
    st.markdown("## 🚨 Price Alerts")
    st.divider()
    
    settings = st.session_state.get("settings", {
        "alert_days": 30,
    })
    
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
        a_days = st.number_input("Days", min_value=1, step=1, value=settings["alert_days"], label_visibility="collapsed")
    with c6:
        set_alert = st.button("Set →")
    
    if set_alert:
        if a_ticker and a_threshold > 0:

            res, err = api.api_post(
                "/alerts",
                {
                    "stock_name": a_ticker.upper(),
                    "condition": a_condition,
                    "threshold": float(a_threshold),
                    "is_persistent": True if a_persistent == "True" else False,
                    "expire_days": int(a_days)
                }
            )
            if err:
                st.error(f"Try again in a while : {err}")
            else:
                st.success("Alert created!")
                st.json(res)
                st.rerun()

        else:
            st.warning("Enter ticker and threshold.")

    st.divider()


    st.markdown('<div>🤿 Active Alerts</div>', unsafe_allow_html=True)
    active, err = api.api_get("/alerts/active")
    if err: 
        logger.error(err)
        st.error(f"Try again in a while : {err}")
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
                if st.button("×", key=f"del_alert_{a['id']}"):
                    res, derr = api.api_delete(f"/alerts/{a['id']}")
                    if derr:
                        st.error(derr)
                    else:
                        st.rerun()
    st.divider()


    st.markdown('<div class="section-label">😮‍💨 Triggered Alerts Log</div>', unsafe_allow_html=True)
    log, err = api.api_get("/alerts/logs")
    if err: 
        logger.error(err)
        st.error(f"Try again in a while : {err}")
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
