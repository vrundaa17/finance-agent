from core.db import get_connection
from datetime import datetime
import utils 
import agent.find as find
import sqlite3
import logging,json
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
    try:
        find.get_kyc_of_stock(stock_name)
    except ValueError as e:
        return {'status': 'invalid', 'message': str(e)}
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


def report(stock_name, report, targets=None, lstm_prediction=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO report (stock_name, report, targets, lstm_prediction, generated_at) VALUES (?, ?, ?, ?, ?)",
            (stock_name.upper(), report,
             json.dumps(targets) if targets else None,
             json.dumps(lstm_prediction) if lstm_prediction else None,
             utils._now_is_ist())
        )
        conn.commit()
        logger.info(f"Report added {stock_name}")


def get_reports(stock_name):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT report, targets, lstm_prediction, generated_at FROM report WHERE stock_name = ? ORDER BY generated_at DESC LIMIT 1",
            (stock_name.upper(),)
        ).fetchone()
        logger.info(f"Fetched report for {stock_name}")
        if not row:
            return None
        d = dict(row)
        d["targets"] = utils.loads_or_none(d.get("targets"))
        d["lstm_prediction"]=utils.loads_or_none(d.get("lstm_prediction"))
        return d


def list_reports_today() -> list[dict]:
    """Get all stocks that were analysed today"""
    today = utils._today_ist()
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT stock_name, generated_at FROM report
               WHERE substr(generated_at, 1, 10) = ?
               ORDER BY generated_at DESC""",
            (today,)
        ).fetchall()
        logger.info(f"List of reports for {today}")
        return [dict(r) for r in rows]

       
def is_reported_today(stock_name: str) -> bool:
    """Check if a report was already generated today for this stock"""
    latest = get_reports(stock_name)
    if not latest:
        return False
    generated_date = latest["generated_at"][:10]  
    today =utils._today_ist()
    return generated_date == today



def record_failure(stock_name, error):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, retry_count FROM report_failures WHERE stock_name=? AND resolved=0 AND date(failed_at)=date('now','localtime')",
            (stock_name.upper(),)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE report_failures SET retry_count=retry_count+1, error=?, error_type=?, failed_at=? WHERE id=?",
                (error, utils.classify_error(error), utils._now_is_ist(), row["id"])
            )
        else:
            conn.execute(
                "INSERT INTO report_failures (stock_name, error, error_type, failed_at, retry_count) VALUES (?,?,?,?,0)",
                (stock_name.upper(), error, utils.classify_error(error), utils._now_is_ist())
            )
        conn.commit()
        logger.info(f"[Failure] recorded for {stock_name}")

def resolve_failure(stock_name):
    with get_connection() as conn:
        conn.execute("UPDATE report_failures SET resolved=1 WHERE stock_name=? AND resolved=0", (stock_name.upper(),))
        conn.commit()

def get_pending_failures(max_retries=3):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT stock_name, retry_count FROM report_failures WHERE resolved=0 AND retry_count<? AND date(failed_at)=date('now','localtime')",
            (max_retries,)
        ).fetchall()
        return [dict(r) for r in rows]
    
    
def cleanup_reports():
    """Delete all reports not generated today"""
    today = utils._today_ist()
    with get_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM report WHERE substr(generated_at, 1, 10) != ?",
            (today,)
        ).rowcount
        conn.commit()
        if deleted:
            logger.info(f"[Scheduler] Cleaned up {deleted} old reports")
