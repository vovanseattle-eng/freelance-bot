from contextlib import asynccontextmanager
import aiosqlite
from config import DATABASE_PATH

INIT_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    budget TEXT,
    contact TEXT,
    link TEXT NOT NULL,
    category TEXT NOT NULL,
    hash TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    categories TEXT DEFAULT 'dev,design,smm,copywriting,video',
    notifications_enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_deliveries (
    order_id INTEGER,
    user_id INTEGER,
    delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id, user_id)
);

CREATE TABLE IF NOT EXISTS terms_acceptances (
    user_id INTEGER PRIMARY KEY,
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_category ON orders(category);

CREATE INDEX IF NOT EXISTS idx_orders_hash ON orders(hash);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
"""

async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.create_function("py_lower", 1, lambda s: s.lower() if s else "")
        await db.executescript(INIT_SQL)
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN contact TEXT")
        except Exception:
            pass
        await db.commit()

@asynccontextmanager
async def get_connection():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.create_function("py_lower", 1, lambda s: s.lower() if s else "")
        yield db
