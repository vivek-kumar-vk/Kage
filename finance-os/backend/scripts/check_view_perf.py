from services.db import connect
import sqlite3
import sys

def check_view_perf():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM latest_prices")
    plan = cursor.fetchall()
    conn.close()
    
    index_used = any('idx_price_history_symbol_date' in str(row) for row in plan)
    
    if not index_used:
        print("Index idx_price_history_symbol_date not used in the query plan.")
        sys.exit(1)
    
    print("Index idx_price_history_symbol_date used in the query plan.")

if __name__ == "__main__":
    check_view_perf()
