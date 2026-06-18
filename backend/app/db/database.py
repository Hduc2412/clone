"""
Database SQLite — Sprint 3
Lưu lịch sử hội thoại và lead xuống file.
"""
import aiosqlite
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "chatbot.db"

async def init_db():
    """Tạo các bảng nếu chưa có."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # Bảng lưu lịch sử hội thoại
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT DEFAULT 'chung',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
          # Bảng lưu lead
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    print("[DB] Khởi tạo database thành công.")

async def save_message(session_id: str, role: str, content: str, intent: str = "chung"):
    """Lưu 1 tin nhắn vào bảng messages."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, intent) VALUES (?, ?, ?, ?)",
            (session_id, role, content, intent)
        )
        await db.commit()

async def save_lead(session_id: str, name: str = None, phone: str = None, note: str = None):
    """Lưu lead vào bảng leads."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO leads (session_id, name, phone, note) VALUES (?, ?, ?, ?)",
            (session_id, name, phone, note)
        )
        await db.commit()

async def get_message(session_id: str) -> list:
    """Lấy toàn bộ tin nhắn của 1 session."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT role, content, intent, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,)
        )
        rows = await cursor.fetchall()
        return [
            {"role": r[0], "content": r[1], "intent": r[2], "created_at": r[3]}
            for r in rows
        ]

async def get_all_leads() -> list:
    """Lấy toàn bộ lead — dùng cho Analytics sau này."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT session_id, name, phone, note, created_at FROM leads ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {"session_id": r[0], "name": r[1], "phone": r[2], "note": r[3], "created_at": r[4]}
            for r in rows
        ]



