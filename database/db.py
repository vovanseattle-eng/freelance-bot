from contextlib import asynccontextmanager
import aiosqlite
from config import DATABASE_PATH

INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    categories TEXT DEFAULT 'dev,design,smm,copywriting,video',
    notifications_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS terms_acceptances (
    user_id INTEGER PRIMARY KEY,
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.create_function("py_lower", 1, lambda s: s.lower() if s else "")
        # Очистка устаревших таблиц заказов для освобождения памяти и диска
        await db.execute("DROP TABLE IF EXISTS order_deliveries;")
        await db.execute("DROP TABLE IF EXISTS orders;")
        await db.executescript(INIT_SQL)
        await db.commit()
        try:
            await db.execute("VACUUM;")
        except Exception:
            pass

@asynccontextmanager
async def get_connection():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.create_function("py_lower", 1, lambda s: s.lower() if s else "")
        yield db
