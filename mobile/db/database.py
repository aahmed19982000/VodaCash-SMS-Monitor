# mobile/db/database.py
import sqlite3
import threading
import os
import logging
from shared.config import BASE_DIR

logger = logging.getLogger("VodaCash.MobileDB")

MOBILE_DB_PATH = os.path.join(BASE_DIR, "mobile", "db", "mobile_cache.db")

class MobileDatabase:
    """قاعدة البيانات المحلية للموبايل لتخزين العمليات (Queue) في حال انقطاع الاتصال."""
    
    def __init__(self, db_path=MOBILE_DB_PATH):
        self._db_path = db_path
        self._local = threading.local()
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._create_tables()
        logger.info("✅ Mobile Database initialized")

    @property
    def _conn(self):
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._conn.commit()

    def enqueue(self, payload: str):
        self._conn.execute("INSERT INTO offline_queue (payload) VALUES (?)", (payload,))
        self._conn.commit()

    def get_all(self):
        rows = self._conn.execute("SELECT id, payload FROM offline_queue ORDER BY id ASC").fetchall()
        return [{"id": r["id"], "payload": r["payload"]} for r in rows]

    def remove(self, record_id: int):
        self._conn.execute("DELETE FROM offline_queue WHERE id = ?", (record_id,))
        self._conn.commit()
