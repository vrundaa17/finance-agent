from fastapi import APIRouter, HTTPException
import api.watchlist as watchlist
from api.schema import AlertCreate

app = APIRouter(tags=['Alert'])

@app.post("/alerts")
def create_alert(request :AlertCreate ):
    """Add a new alert"""
    result = watchlist.add_alert(request.stock_name,request.condition,request.threshold,
        request.is_persistent,request.expire_days)
    
    if result.get("status") == "invalid":
        raise HTTPException(status_code=400, detail=result["message"])
    if result.get("status") == "closed":
        raise HTTPException(status_code=400, detail=result["message"])
    return result

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
    result =  watchlist.user_delete_alert(alert_id)
    if result.get("status")=="error":
        raise HTTPException(status_code=404, detail=result["message"])
    return result