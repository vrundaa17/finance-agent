'''
sqlite connection methods 
'''
import sqlite3
from db import get_connection
from datetime import datetime


def create_watchlist(name ):
    with get_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO watchlists (name, created_at) VALUES (?, ?)",
                (name, datetime.now().isoformat())
                )
            conn.commit()
            return {'status' : 'created','watchlist':name}
        except sqlite3.IntegrityError:
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
        return {'status':'deleted','watchlist':watchlist_name}


def add_stock(watchlist_name,stock_name,notes=None):
    create_watchlist(watchlist_name)
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name=?",(watchlist_name,)
        ).fetchone()
        
        if not watchlist:
            return {'status' : 'error', 'message':f'Watchlist {watchlist_name} not found'}
        
        try: 
            conn.execute(
                "INSERT INTO stocks (watchlist_id, stock_name, added_at, notes) VALUES (?,?,?,?)",
                (watchlist['id'], stock_name.upper(),datetime.now().isoformat(),notes)
            )
            conn.commit()
            return {'status': 'added', 'stock_name':stock_name.upper(),'watchlist':watchlist_name}
        except sqlite3.IntegrityError:
            return {"status": "exists", "stock_name": stock_name.upper(), "watchlist": watchlist_name}
        
        
def remove_stock(watchlist_name, stock_name):
    create_watchlist(watchlist_name)
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name=?",(watchlist_name,)
        ).fetchone()
        
        if not watchlist:
            return {'status' : 'error', 'message':f'Watchlist {watchlist_name} not found'}
        
        cursor = conn.execute(
            "DELETE FROM stocks WHERE watchlist_id =? AND stock_name=?",
            (watchlist['id'],stock_name.upper())
        )
        conn.commit()
        
        if cursor.rowcount ==0:
            return{
                'status':'not found', 'stock_name' :stock_name.upper(), 'watchlist' : watchlist_name
            }
        
        return{'status':'removed','stock_name':stock_name.upper(), 'watchlist':watchlist_name}
            
                   
def get_stock(watchlist_name):
    with get_connection() as conn:
        watchlist = conn.execute(
            "SELECT id FROM watchlists WHERE name = ?", (watchlist_name,)
        ).fetchone()
 
        if not watchlist:
            return []
        
        rows = conn.execute(
            "SELECT stock_name FROM stocks WHERE watchlist_id = ? ORDER BY added_at",
            (watchlist["id"],)
        ).fetchall()
        return [r["stock_name"] for r in rows]


def report(stock_name,report):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO report (stock_name, report, generated_at) VALUES (?, ?, ?)",
            (stock_name.upper(), report, datetime.now().isoformat())
        )
        conn.commit()


def get_reports(stock_name):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT report, generated_at FROM report WHERE stock_name = ? ORDER BY generated_at DESC LIMIT 1",
            (stock_name.upper(),)
        ).fetchone()
        return dict(row) if row else None
    
    
#--------

def add_alert(stock_name:str, condition : str,threshold : float ):
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO alert (stock_name,condition,threshold,created_at)
                VALUES(?,?,?,?)""",
                (stock_name.upper(),condition,threshold,datetime.now().isoformat())
        )
        conn.commit()
        return {
            "status":"created", "stock_name":stock_name.upper(),"condition":condition,"threshold":threshold
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
            "UPDATE alert SET triggered = 1, triggered_at = ? WHERE id = ?",
            (now, alert_id)
        )
        conn.execute(
            """INSERT INTO alert_log (stock_name, condition, threshold, price_at_trigger, triggered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (alert["stock_name"], alert["condition"],
             alert["threshold"], price, now)
        )
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