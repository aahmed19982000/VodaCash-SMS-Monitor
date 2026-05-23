import sqlite3

def check_vodafone_cash():
    conn = sqlite3.connect("desktop/db/desktop_cache.db")
    conn.row_factory = sqlite3.Row
    
    # 1. Check initial balance setting
    row = conn.execute("SELECT value FROM settings WHERE key = 'initial_balance_vodafone_cash'").fetchone()
    initial_bal = row["value"] if row else None
    print(f"Initial balance setting: {initial_bal}")
    
    # 2. Check the last transaction with balance_after >= 0
    latest_tx = conn.execute("""
        SELECT transaction_id, type, amount, balance_after, sms_timestamp, counterpart, profit_status 
        FROM transactions 
        WHERE wallet_id = 'vodafone_cash' AND balance_after >= 0 
        ORDER BY sms_timestamp DESC, received_at DESC, transaction_id DESC 
        LIMIT 1
    """).fetchone()
    if latest_tx:
        print("\nLast transaction with balance_after >= 0:")
        print(dict(latest_tx))
    else:
        print("\nNo transaction found with balance_after >= 0")
        
    # 3. Check recent transactions
    print("\nRecent 5 transactions for Vodafone Cash:")
    rows = conn.execute("""
        SELECT transaction_id, type, amount, balance_after, sms_timestamp, profit_status 
        FROM transactions 
        WHERE wallet_id = 'vodafone_cash'
        ORDER BY sms_timestamp DESC, received_at DESC, transaction_id DESC
        LIMIT 5
    """).fetchall()
    for r in rows:
        print(dict(r))
        
    # 4. Check net change sum
    tx_sum = conn.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN type IN ('RECEIVED', 'ATM_DEPOSIT') THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type IN ('SENT', 'BILL', 'PURCHASE', 'TOPUP', 'ATM_WITHDRAWAL') THEN amount ELSE 0 END), 0) AS net_change
        FROM transactions
        WHERE wallet_id = 'vodafone_cash'
    """).fetchone()
    net_change = tx_sum["net_change"] if tx_sum else 0.0
    print(f"\nNet change of all transactions: {net_change}")
    
    # 5. Check in-wallet fees
    fees_row = conn.execute("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_amount 
        FROM transactions 
        WHERE wallet_id = 'vodafone_cash' AND profit_status = 'IN_WALLET'
    """).fetchone()
    print(f"Transactions marked as IN_WALLET: {fees_row['count']} | Total amount: {fees_row['total_amount']}")

    conn.close()

if __name__ == "__main__":
    check_vodafone_cash()
