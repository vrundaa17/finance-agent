import streamlit as st
import api_client as api
import logging
logger = logging.getLogger(__name__)

def portfolio():
    settings = st.session_state.get("settings", {
        "currency_symbol": "₹",
    })
    
    st.markdown("## 👜 Portfolio")
    st.divider()

 
    with st.expander("➕ Create New Watchlist"):
        new_name = st.text_input("Watchlist name", placeholder="tech_stocks, nifty_stock...")
        if st.button("Create"):
            if new_name.strip():
                res, err = api.api_post("/watchlists", {"name": new_name.strip()})
                if err:
                    logger.error(err)
                    st.error(f"Try again in a while : {err}")
                else:st.success(f"Created '{new_name}'"); st.rerun()
            else:
                st.warning("Enter a name.")

    watchlists, err = api.api_get("/watchlists")
    if err:
        logger.error(err)
        st.error("Try again in a while")
    elif not watchlists:
        st.info("No watchlists yet — create one above.")
    else:
        for wl in watchlists:
            name  = wl["name"]
            count = wl["ticker_count"]
            selected = []
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
                        api.api_delete(f"/watchlists/{name}")
                        st.rerun()
                        
                        
                # with st.expander(""): 

                stocks_data, _ = api.api_get(f"/watchlists/{name}")
                stocks = stocks_data.get("stock_name", []) if stocks_data else []
                
                if stocks:
                    
                    for stock in stocks:
                        s1, s2 = st.columns([9, 1])
                        with s1:
                            checked = st.checkbox(stock, key=f"check_{name}_{stock}")
                            if checked: selected.append(stock)
                        with s2:
                            if st.button("×", key=f"rm_{name}_{stock}"):
                                api.api_delete(f"/watchlists/{name}/{stock}")
                                st.rerun()
                else:
                    st.info("No stocks yet.")


                a1, a2 = st.columns([4, 1])
                with a1:
                    new_ticker = st.text_input("Add stock", placeholder="RELIANCE.NS", key=f"inp_{name}", label_visibility="collapsed")
                with a2:
                    if st.button("Add", key=f"add_{name}"):
                        if new_ticker.strip():
                            res, err = api.api_post("/watchlists/add", {
                                "watchlist_name": name,
                                "stock_name": new_ticker.strip().upper(),
                                "notes": ""
                            })
                            if err: 
                                logger.error(err)
                                st.error(f"Try again in a while : {err}")
                            else:st.success(f"Added {new_ticker.upper()}"); st.rerun()

                # analyse
                if st.session_state.get(f"run_brief_{name}"):
                    st.session_state[f"run_brief_{name}"] = False
                    if not selected:
                        st.warning("Select at least one stock to analyse.")
                    else:
                        with st.spinner(f"Running analysis for {name}... ({len(selected)} stocks)"):
                            data, err = api.api_post("/report/watchlist", {"stock_name": selected})

                        if err:
                            logger.error(f"Error: {err}")
                            st.error(f"Try again in a while : {err}")
                        elif data:
                            st.success(f"✓ {data['successful']}/{data['total']} reports generated — check the Stock Analysis page for full details.")
                            st.caption(f"Analysed: {', '.join(selected)}")
