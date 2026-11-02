"""
SQLite Database Persistence Manager.
Operates in WAL mode to allow seamless concurrent UI reading and background logging.
"""
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from config import DB_PATH


class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS actions_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    approved INTEGER NOT NULL DEFAULT 0,
                    executed INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_messages_convo ON messages(conversation_id);
            """)

    # --- CONVERSATION OPERATIONS ---
    def get_or_create_active_conversation(self) -> str:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                return row["id"]

            new_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (new_id, "New Session", now, now)
            )
            return new_id

    def create_new_conversation(self, title: str = "New Session") -> str:
        new_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (new_id, title, now, now)
            )
        return new_id

    def add_message(self, conversation_id: str, role: str, content: str) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, now)
            )
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, conversation_id)
            )
            return cursor.lastrowid or 0

    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
                (conversation_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_messages_for_llm(self, conversation_id: str, limit: int = 10) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit)
            )
            rows = cursor.fetchall()
            # Reverse back to chronological order for LLM context
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # --- SETTINGS KEY-VALUE STORE ---
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value)
            )

    # --- SAFETY AUDIT LOGGING ---
    def log_action_request(self, action_type: str, payload: str, approved: bool, executed: bool) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO actions_audit (timestamp, action_type, payload, approved, executed) VALUES (?, ?, ?, ?, ?)",
                (now, action_type, payload, 1 if approved else 0, 1 if executed else 0)
            )
            return cursor.lastrowid or 0

