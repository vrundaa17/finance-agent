from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist

app = APIRouter(tags=['Alert'])

@app.post("/alerts")
def create_alert(stock_name: str,condition: str, threshold:float,is_persistent:bool,expire_days:int):
    """Add a new alert"""
    return watchlist.add_alert(stock_name,condition,threshold,is_persistent,expire_days)

@app.get("/alerts")
def list_alerts(stock_name:str):
    """List all my alerts"""
    return watchlist.get_alerts(stock_name)

@app.get("/alerts/active")
def list_active_alerts():
    """List all the active alerts """
    return watchlist.get_active_alerts()

@app.get("/alerts/logs")
def list_alert_logs():
    """Show my alert log"""
    return watchlist.get_alert_log()

@app.delete("/alerts/{alert_id}")
def delete_alert(alert_id: int):
    return watchlist.user_delete_alert(alert_id)