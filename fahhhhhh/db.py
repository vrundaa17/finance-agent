import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "watchlist.db")
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """ CREATE TABLE IF NOT EXISTS watchlists
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
                )
            """
        )
        conn.execute(
            """ CREATE TABLE IF NOT EXISTS stocks
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_name TEXT NOT NULL,
                added_at TEXT NOT NULL,
                watchlist_id INTEGER NOT NULL,
                notes TEXT,
                FOREIGN KEY (watchlist_id) REFERENCES watchlists(id)
                UNIQUE(watchlist_id, stock_name)
            )"""
        )
        conn.execute(
            """ CREATE TABLE IF NOT EXISTS report(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_name TEXT NOT NULL,
                report TEXT NOT NULL,
                targets TEXT,
                lstm_prediction TEXT,
                generated_at TEXT NOT NULL
                )"""
        )

        existing_report_cols = {row["name"] for row in conn.execute("PRAGMA table_info(report)")}
        for col in ("targets", "lstm_prediction"):
            if col not in existing_report_cols:
                conn.execute(f"ALTER TABLE report ADD COLUMN {col} TEXT")
                
                
        conn.execute(
            """ CREATE TABLE IF NOT EXISTS alert(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_name TEXT NOT NULL,
                condition TEXT NOT NULL,
                threshold REAL NOT NULL,
                is_persistent INTEGER DEFAULT 0,
                expires_at TEXT,
                triggered INTEGER DEFAULT 0,
                triggered_at TEXT,
                created_at TEXT NOT NULL
                )
            """
        )
        conn.execute(
            """ 
            CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_name TEXT NOT NULL,
            condition TEXT NOT NULL,
            threshold REAL NOT NULL,
            price_at_trigger REAL NOT NULL,
            triggered_at TEXT NOT NULL
            )
            """
        )  

        
        conn.execute(
            """ 
            CREATE TABLE IF NOT EXISTS predict_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_name TEXT NOT NULL,
                predicted_at TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                accuracy REAL NOT NULL,
                predicted_price REAL,
                current_price REAL,
                horizon_days INTEGER,
                target_date TEXT,
                actual_outcome TEXT,
                actual_price REAL,
                was_correct INTEGER,
                human_flag TEXT,
                human_note TEXT
            )
            """
        )
        conn.commit()
        
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(predict_log)")}
        for col, coltype in [("predicted_price","REAL"),("current_price","REAL"),
                              ("horizon_days","INTEGER"),("target_date","TEXT"),
                              ("actual_price","REAL")]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE predict_log ADD COLUMN {col} {coltype}")
        conn.commit()