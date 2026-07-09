'''
sqlite connection methods 
'''
import sqlite3,pytz
from db import get_connection
from datetime import datetime,timedelta
IST = pytz.timezone("Asia/Kolkata")

import logging
logger = logging.getLogger(__name__)

def create_watchlist(name ):
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO watchlists (name, created_at) VALUES (?, ?)",
                (name, datetime.now().isoformat())
                )
            conn.commit()
            logger.info(f"Watchlist created : {name}")
            return {'status' : 'created','watchlist':name}
        except sqlite3.IntegrityError:
            logger.error(f'Error in creating watchlist {name}')
            return{'status':'exists','watchlist':name}


def list_watchlist():
    with get_connection() as conn:
        rows = conn.execute(
            """
                SELECT w.name, w.created_at, COUNT(t.id) as ticker_count
                FROM watchlists w
                LEFT JOIN stocks t ON t.watchlist_id = w.id
                GROUP BY w.id
        """).fetchall()
        logger.info(f"Listing all the watchlist...{len(rows)}")
        return [dict(r) for r in rows]
        
        
def delete_watchlist(watchlist_name:str):
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name = ?", (watchlist_name,)
        ).fetchone()
 
        if not watchlist:
            return{'status':'error','message':f'Watchlist {watchlist_name} not found'}
        
        conn.execute("DELETE FROM stocks WHERE watchlist_id = ?", (watchlist["id"],))
        conn.execute(
            "DELETE FROM watchlists where id=?",(watchlist['id'],)
        )
        conn.commit()
        logger.info(f"Deleting the watchlist {watchlist_name}")
        return {'status':'deleted','watchlist':watchlist_name}


def add_stock(watchlist_name,stock_name,notes=None):
    create_watchlist(watchlist_name)
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name=?",(watchlist_name,)
        ).fetchone()
        
        if not watchlist:
            logger.info(f"The watchlist doesnot exists... {watchlist_name}")
            return {'status' : 'error', 'message':f'Watchlist {watchlist_name} not found'}
        
        try: 
            conn.execute(
                "INSERT INTO stocks (watchlist_id, stock_name, added_at, notes) VALUES (?,?,?,?)",
                (watchlist['id'], stock_name.upper(),datetime.now().isoformat(),notes)
            )
            conn.commit()
            logger.info(f"Added stock : {stock_name} | watchlist : {watchlist_name}")
            return {'status': 'added', 'stock_name':stock_name.upper(),'watchlist':watchlist_name}
        except sqlite3.IntegrityError:
            logger.error(f"Exists already {stock_name} | {watchlist_name}")
            return {"status": "exists", "stock_name": stock_name.upper(), "watchlist": watchlist_name}
        
        
def remove_stock(watchlist_name, stock_name):
    create_watchlist(watchlist_name)
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name=?",(watchlist_name,)
        ).fetchone()
        
        if not watchlist:
            logger.info(f"ERROR {watchlist_name} not there")
            return {'status' : 'error', 'message':f'Watchlist {watchlist_name} not found'}
        
        cursor = conn.execute(
            "DELETE FROM stocks WHERE watchlist_id =? AND stock_name=?",
            (watchlist['id'],stock_name.upper())
        )
        conn.commit()
        
        if cursor.rowcount ==0:
            logger.error(f"Not found {stock_name} | {watchlist_name}")
            return{
                'status':'not found', 'stock_name' :stock_name.upper(), 'watchlist' : watchlist_name
            }
        logger.info(f"Removed stock : {stock_name} | watchlist : {watchlist_name}")
        return{'status':'removed','stock_name':stock_name.upper(), 'watchlist':watchlist_name}
            
                   
def get_stock(watchlist_name):
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name = ?", (watchlist_name,)
        ).fetchone()
 
        if not watchlist:
            logger.error(f"Watchlist {watchlist_name} not found")
            return []
        
        rows = conn.execute(
            "SELECT stock_name FROM stocks WHERE watchlist_id = ? ORDER BY added_at",
            (watchlist["id"],)
        ).fetchall()
        
        logger.info(f"Fetched stocks in watchlist : {watchlist_name}")
        return [r["stock_name"] for r in rows]


def report(stock_name,report):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO report (stock_name, report, generated_at) VALUES (?, ?, ?)",
            (stock_name.upper(), report, datetime.now().isoformat())
        )
        conn.commit()
        logger.info(f"Report added {stock_name}")


def get_reports(stock_name):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT report, generated_at FROM report WHERE stock_name = ? ORDER BY generated_at DESC LIMIT 1",
            (stock_name.upper(),)
        ).fetchone()
        logger.info(f"Fetched report for {stock_name}")
        return dict(row) if row else None


def list_reports_today() -> list[dict]:
    """Get all stocks that were analysed today"""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT stock_name, generated_at FROM report
               WHERE substr(generated_at, 1, 10) = ?
               ORDER BY generated_at DESC""",
            (today,)
        ).fetchall()
        logger.info(f"List of reports for {today}")
        return [dict(r) for r in rows]
    
    
    
#------------------------------------------------------------------------------------------------------------------------------------------------------------
#alert
def add_alert(stock_name:str, condition : str,threshold : float ,is_persistent: bool = False, expires_days: int = 5):
    expires_at =  (datetime.now() + timedelta(days=expires_days)).isoformat()
    now = datetime.now(IST)
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
            
def is_reported_today(stock_name: str) -> bool:
    """Check if a report was already generated today for this stock"""
    latest = get_reports(stock_name)
    if not latest:
        return False
    generated_date = latest["generated_at"][:10]  
    today = datetime.now().strftime("%Y-%m-%d")
    return generated_date == today


def cleanup_reports():
    """Delete all reports not generated today"""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM report WHERE substr(generated_at, 1, 10) != ?",
            (today,)
        ).rowcount
        conn.commit()
        if deleted:
            logger.info(f"[Scheduler] Cleaned up {deleted} old reports")
