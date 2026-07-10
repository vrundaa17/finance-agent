import streamlit as st
import logging
import api_client as api
import os
logger = logging.getLogger(__name__)

def edit():
    st.markdown("""
        <style>
            label[data-testid="stWidgetLabel"] p { font-size: 20px; }
            div[data-testid="stToggle"] label p { font-size: 20px; }
            div[data-testid="stExpander"] summary p { font-size: 20px; }
            div[data-testid="stExpander"] p { font-size: 20px; }
            .section-label { font-size: 23px; letter-spacing: 0.1em; }
            div[data-testid="stMarkdown"] p { font-size: 20px; line-height: 1.7; }
            div[data-testid="stCaptionContainer"] p { font-size: 18px; }
            table td, table th { font-size: 14px; }
            div[data-testid="column"] p { font-size: 20px; }
            div[data-testid="stCheckbox"] label p { font-size: 20px; }
            button[data-testid="baseButton-secondary"] p { font-size: 14px; }
        </style>
    """, unsafe_allow_html=True)
 

    
    st.markdown("## 🪄 Edits")
    st.divider()


    st.markdown('<div class="section-label">Dashboard Preferences</div>', unsafe_allow_html=True)

    if "settings" not in st.session_state:
        st.session_state.settings = {
            "default_watchlist": "",
            "default_period": "3mo",
            "show_predictions": True,
            "show_targets": True,
            "show_charts": True,
            "currency_symbol":"₹",
            "alert_days": 30,
        }

    s = st.session_state.settings

    col1, col2 = st.columns(2)

    with col1:
        watchlists, _ = api.api_get("/watchlists")
        wl_names = [w["name"] for w in watchlists] if watchlists else []
        default_wl = st.selectbox(
            "Default watchlist on home page",
            options=["—"] + wl_names,
            index=0 if not s["default_watchlist"] else
                  (["—"] + wl_names).index(s["default_watchlist"])
                  if s["default_watchlist"] in wl_names else 0
        )
        s["default_watchlist"] = default_wl if default_wl != "—" else ""

        s["default_period"] = st.selectbox(
            "Default chart period",
            ["1mo", "3mo", "6mo", "1y", "2y"],
            index=["1mo", "3mo", "6mo", "1y", "2y"].index(s["default_period"])
        )
        
        s["currency_symbol"] = st.selectbox(
            "Currency symbol",
            ["₹", "$", "€", "£"],
            index=["₹", "$", "€", "£"].index(s["currency_symbol"])
        )

    with col2:
        s["show_charts"]= st.toggle("Show charts on analysis page", value=s["show_charts"])
        s["show_targets"]= st.toggle("Show buy/sell targets",value=s["show_targets"])
        s["show_predictions"]= st.toggle("Show ML predictions",value=s["show_predictions"])
        s["alert_days"]= st.number_input("Default alert expiry (days)",min_value=1, max_value=365,value=s["alert_days"])

    st.divider()

    
    st.markdown('<div class="section-label">ML Prediction Settings</div>', unsafe_allow_html=True)

    if "pred_settings" not in st.session_state:
        st.session_state.pred_settings = {
            "training_period": "2y",
            "auto_verify": True,
        }

    ps = st.session_state.pred_settings

    pc1, pc2 = st.columns(2)
    with pc1:
        ps["training_period"] = st.selectbox(
            "Training data period",
            ["6mo", "1y", "2y", "5y"],
            index=["6mo", "1y", "2y", "5y"].index(ps["training_period"]),
            help="More data = more patterns but older data may be less relevant"
        )
        
    with pc2:
        ps["auto_verify"] = st.toggle(
            "Auto-verify yesterday's predictions daily",
            value=ps["auto_verify"],
            help="Scheduler checks actual outcome every morning at 9am"
        )
        if st.button("Verify All Pending Predictions Now"):
            result, err = api.api_post("/predictions/verify/all")
            if err: st.error(err)
            else:   st.success(f"Verified {result.get('verified', 0)} predictions")

    st.divider()

    
    st.markdown('<div class="section-label">Prediction Review</div>', unsafe_allow_html=True)
    st.caption("Review past predictions and give feedback to improve the model")

    preds, _ = api.api_get("/predictions")

    if preds:
        total= len(preds)
        verified= [p for p in preds if p.get("was_correct") is not None]
        correct= [p for p in verified if p.get("was_correct") == 1]
        agrees = [p for p in preds if p.get("human_flag") == "AGREE"]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Predictions", total)
        m2.metric("Verified",len(verified))
        m3.metric("Model Accuracy",f"{round(len(correct)/len(verified)*100)}%" if verified else "—")
        m4.metric("Advisor Agreed",len(agrees))

        st.divider()

        for p in preds[:20]:
            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 1, 1, 2])
            c1.write(p["predicted_at"][:10])
            c2.write(f"**{p['stock_name']}**")
            c3.write(p["direction"])
            c4.write(f"{p['confidence']}%")

            if p.get("was_correct") == 1:
                c5.success("✓")
            elif p.get("was_correct") == 0:
                c5.error("✗")
            else:
                c5.write("⏳")

            if not p.get("human_flag"):
                with c6:
                    b1, b2, = st.columns(2)
                    if b1.button("✔️", key=f"s_agree_{p['id']}"):
                        api.api_post(f"/predictions/{p['id']}/feedback", params={"flag": "AGREE"})
                        
                        st.rerun()
                    if b2.button("✖️", key=f"s_dis_{p['id']}"):
                        api.api_post(f"/predictions/{p['id']}/feedback", params={"flag": "DISAGREE"})
                        st.rerun()

            else:
                flag_emoji = {"AGREE": "✔️", "DISAGREE": "✖️"}.get(p["human_flag"], "")
                c6.write(f"{flag_emoji} {p['human_flag']}")
    else:
        st.info("No predictions yet. Run an analysis on the Stock Analysis page first.")

    st.divider()

    
    st.markdown('<div class="section-label">Danger Zone</div>', unsafe_allow_html=True)

    with st.expander("⚠️ Clear Data"):
        st.warning("These actions cannot be undone.")
        d1, d2 = st.columns(2)
        with d1:
            if st.button("Clear All Charts", type="secondary"):
                result,err= api.api_delete("/charts/clear")
                if err : st.error(err)
                else:
                    st.success(f"Deleted chart files")
        with d2:
            if st.button("Clear Prediction History", type="secondary"):
                result, err = api.api_delete("/predictions/clear")
                if err: 
                    st.error(err)
                else:   
                    st.success("Prediction history cleared")