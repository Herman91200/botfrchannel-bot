import aiosqlite
import time
from datetime import datetime

DB_PATH = "bot_data.db"

async def init_db():
    """Создает таблицу для хранения кулдаунов."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                last_sent_time INTEGER
            )
        """)
        await db.commit()

async def get_cooldown(user_id: int) -> int:
    """Возвращает оставшееся время кулдауна в секундах (0, если можно отправлять)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_sent_time FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                last_time = row[0]
                current_time = int(time.time())
                elapsed = current_time - last_time
                if elapsed < 1800:  # 30 минут = 1800 секунд
                    return 1800 - elapsed
    return 0

async def set_cooldown(user_id: int):
    """Обновляет время последней отправки для пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        current_time = int(time.time())
        await db.execute("""
            INSERT INTO users (user_id, last_sent_time) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_sent_time = excluded.last_sent_time
        """, (user_id, current_time))
        await db.commit()

def format_time(seconds: int) -> str:
    """Переводит секунды в красивый формат (например, '15 минут')."""
    minutes = seconds // 60
    return f"{minutes} минут"