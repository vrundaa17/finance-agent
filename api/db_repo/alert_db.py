from core.db import get_connection
from datetime import datetime,timedelta
import utils
import agent.find as find
import logging
logger = logging.getLogger(__name__)


def add_alert(stock_name:str, condition : str,threshold : float ,is_persistent: bool = False, expires_days: int = 5):
    try:
        find.get_kyc_of_stock(stock_name)
    except ValueError as e:
        return {'status': 'invalid', 'message': str(e)}
    
    
    expires_at =  (datetime.now() + timedelta(days=expires_days)).isoformat()
    now = datetime.now(utils.IST)
    if not (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)):
        logger.info("Market closed")
        return {"status":"closed", "message":"Market is closed. Show up tomorrow"}
    if now.hour < 9 or (now.hour == 9 and now.minute < 15):
        logger.info("Market closed")
        return {"status":"closed", "message":"Market is closed. Show up tomorrow"}
    
    
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO alert
               (stock_name, condition, threshold, is_persistent, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (stock_name.upper(), condition, threshold,
             int(is_persistent),
             None if is_persistent else expires_at,
             datetime.now().isoformat())
        )
        conn.commit()
        logger.info(f"Alert created : {stock_name} ")
        return {
            "status": "created",
            "stock": stock_name.upper(),
            "condition": condition,
            "threshold": threshold,
            "persistent": is_persistent,
            "expires_at": None if is_persistent else expires_at
        }

def get_active_alerts():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alert WHERE triggered = 0"
        ).fetchall()
        
        return [dict(r) for r in rows]
    
    
def mark_alert_triggered(alert_id: int, price: float):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        alert = conn.execute(
           "SELECT * FROM alert WHERE id = ?", (alert_id,)
        ).fetchone()
        
        conn.execute(
            """INSERT INTO alert_log (stock_name, condition, threshold, price_at_trigger, triggered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (alert["stock_name"], alert["condition"],
             alert["threshold"], price, now)
        )
        
        if alert['is_persistent']:
            logger.info(f"[Alerts] Persistent alert triggered for {alert['stock_name']}")
        else:
            conn.execute(
                "UPDATE alert SET triggered = 1, triggered_at = ? WHERE id = ?",(now,alert_id)
            )
        logger.info(f"Alert triggered {alert['stock_name']}")
        conn.commit()

def get_alert_log() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alert_log ORDER BY triggered_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    
    
    
def get_alerts(stock_name: str = None) -> list[dict]:
    with get_connection() as conn:
        if stock_name:
            rows = conn.execute(
                "SELECT * FROM alert WHERE stock_name = ?",
                (stock_name.upper(),)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM alert").fetchall()
        return [dict(r) for r in rows]
    
 
def user_delete_alert(alert_id: int) -> dict:
    """User removes a specific alert by its id"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, stock_name FROM alert WHERE id=?", (alert_id,)
        ).fetchone()

        if not row:
            logger.error(f"Alert not found {row['stock_name']}")
            return {"status": "error", "message": f"Alert with id {alert_id} not found"}

        conn.execute("DELETE FROM alert WHERE id=?", (alert_id,))
        logger.info(f"Deleted Alert for {row['stock_name']}")
        conn.commit()
        return {"status": "deleted", "message": f"Alert for {row['stock_name']} deleted"}
       
    
def cleanup_alerts():
    with get_connection() as conn:
        now = datetime.now().isoformat()
        deleted = conn.execute(
            """DELETE FROM alert
               WHERE is_persistent = 0 AND expires_at IS NOT NULL AND expires_at < ? AND triggered = 0""",
            (now,)
        ).rowcount
        conn.commit()
        if deleted:
            logger.info(f"[Scheduler] Cleaned up {deleted}")
            return{"status":"cleared"}
        else:
            return{"status":"error"}
     
