import sqlite3

def delete_mock_and_check():
    conn = sqlite3.connect("desktop/db/desktop_cache.db")
    conn.execute("DELETE FROM transactions WHERE transaction_id = 'mock_tx_999'")
    conn.commit()
    print("Mock transaction 'mock_tx_999' deleted successfully.")
    conn.close()

if __name__ == "__main__":
    delete_mock_and_check()
