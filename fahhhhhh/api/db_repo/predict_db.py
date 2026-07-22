from core.db import get_connection
from datetime import datetime,timedelta
import agent.find as find
import logging
logger = logging.getLogger(__name__)

def save_prediction(stock_name: str, direction: str, confidence: float, accuracy: float,predicted_price:float=None,analysis_price:float=None,horizon_days:int=None) -> dict:
    target_date=None
    if horizon_days:
        d = datetime.now()
        added=0
        while added<horizon_days:
            d+= timedelta(days=1)
            if d.weekday()<5:
                added+=1
        target_date= d.strftime("%Y-%m-%d")
            
    
    with get_connection() as conn:
        cur = conn.execute(
            """ INSERT INTO predict_log
            (stock_name, predicted_at, direction, confidence, accuracy,
             predicted_price, analysis_price, horizon_days, target_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (stock_name.upper(), datetime.now().isoformat(), direction, confidence,
              accuracy if accuracy is not None else 0.0,
              predicted_price, analysis_price, horizon_days, target_date))
        conn.commit()
        return {"status": "saved", "stock": stock_name.upper(), "direction": direction,'id':cur.lastrowid}

def get_predictions(stock_name: str = None) -> list[dict]:
    with get_connection() as conn:
        if stock_name:
            rows = conn.execute(
                "SELECT * FROM predict_log WHERE stock_name = ? ORDER BY predicted_at DESC",
                (stock_name.upper(),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM predict_log ORDER BY predicted_at DESC LIMIT 50"
            ).fetchall()
        return [dict(r) for r in rows]
    
    
def update_actual_outcome(stock_name: str, date: str, actual: str):
    with get_connection() as conn:
        row = conn.execute("""
            SELECT id, direction FROM predict_log WHERE stock_name = ? AND predicted_at LIKE ?
            ORDER BY predicted_at DESC LIMIT 1 """,
        (stock_name.upper(), f"{date}%")).fetchone()

        if not row:
            return {"status": "not found"}

        was_correct = 1 if row["direction"] == actual else 0
        conn.execute("""
            UPDATE predict_log 
            SET actual_outcome = ?, was_correct = ?
            WHERE id = ?
        """, (actual, was_correct, row["id"]))
        conn.commit()
        return {"status": "updated", "was_correct": bool(was_correct)}
    
    
def add_human_feedback(prediction_id: int, flag: str, note: str = "") -> dict:
    with get_connection() as conn:
        conn.execute("""
            UPDATE predict_log 
            SET human_flag = ?, human_note = ?
            WHERE id = ?
        """, (flag, note, prediction_id))
        conn.commit()
        return {"status": "feedback saved", "id": prediction_id, "flag": flag}


        
def cleanup_old_predictions():
    """Delete predictions older than 100 days."""
    with get_connection() as conn:
        conn.execute("""
            DELETE FROM predict_log 
            WHERE predicted_at < datetime('now', '-100 days')
        """)
        conn.commit()
        
        
def auto_verify_predictions():
    today = datetime.now().date()
    updated = 0
    verified = 0

    #pending 
    with get_connection() as conn:
        predictions = conn.execute(
            """SELECT *FROM predict_log WHERE actual_outcome IS NULL AND target_date IS NOT NULL """
        ).fetchall()

    for row in predictions:
        try:
            hist = find.get_price_history(row["stock_name"], "5d")
            latest_price = float(hist["close"][-1])
        except Exception as e:
            logger.error(f"Price fetch failed for {row['stock_name']}: {e}")
            continue

        with get_connection() as conn:
            conn.execute(""" UPDATE predict_log SET latest_price = ? WHERE id = ?""",(latest_price,row["id"]))
            conn.commit()

        updated += 1
        target_date = datetime.strptime(str(row["target_date"]), "%Y-%m-%d").date()
        if today < target_date:
            logger.info(f"Tracking {row['stock_name']}: current={latest_price}, "
                f"target={target_date}, status=PENDING")
            continue
        
        if latest_price > float(row["analysis_price"]):
            actual_direction = "UP"
        else:
            actual_direction = "DOWN"
        was_correct = (1 if actual_direction == row["direction"] else 0 )
        
        with get_connection() as conn:
            conn.execute(
                """UPDATE predict_log SET actual_outcome = ?, was_correct = ?
                WHERE id = ?""", (actual_direction, was_correct, row["id"])
            )
            conn.commit()
        verified += 1
        logger.info(
            f"Verified {row['stock_name']}: "
            f"prediction={row['direction']} "
            f"actual={actual_direction} "
            f"correct={was_correct}"
        )

    logger.info(f"[Scheduler] Updated prices: {updated}, Verified predictions: {verified}")
    return {"updated": updated,"verified": verified}
