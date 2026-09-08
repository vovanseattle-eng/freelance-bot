from typing import Optional, List, Dict, Any
from database.db import get_connection

VALID_IT_CATEGORIES = ("dev", "design", "smm", "copywriting", "video")

async def save_order(
    source: str,
    title: str,
    link: str,
    category: str,
    content_hash: str,
    external_id: Optional[str] = None,
    description: Optional[str] = None,
    budget: Optional[str] = None,
    contact: Optional[str] = None,
) -> Optional[int]:
    """Сохраняет заказ. Возвращает ID если добавлен, или None если дубликат."""
    async with get_connection() as db:
        try:
            cursor = await db.execute(
                """
                INSERT INTO orders (external_id, source, title, description, budget, contact, link, category, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (external_id, source, title, description or "", budget or "Договорная", contact, link, category, content_hash),
            )
            await db.commit()
            return cursor.lastrowid
        except Exception:
            return None

async def get_orders(category: Optional[str] = None, limit: int = 5, offset: int = 0) -> List[Dict[str, Any]]:
    async with get_connection() as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        if category and category in VALID_IT_CATEGORIES:
            cursor = await db.execute(
                "SELECT * FROM orders WHERE category = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                (category, limit, offset),
            )
        else:
            # Только IT категории
            placeholders = ",".join("?" for _ in VALID_IT_CATEGORIES)
            cursor = await db.execute(
                f"SELECT * FROM orders WHERE category IN ({placeholders}) ORDER BY id DESC LIMIT ? OFFSET ?",
                (*VALID_IT_CATEGORIES, limit, offset),
            )
        return await cursor.fetchall()

async def count_orders(category: Optional[str] = None) -> int:
    async with get_connection() as db:
        if category and category in VALID_IT_CATEGORIES:
            cursor = await db.execute("SELECT COUNT(*) FROM orders WHERE category = ?", (category,))
        else:
            placeholders = ",".join("?" for _ in VALID_IT_CATEGORIES)
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM orders WHERE category IN ({placeholders})",
                VALID_IT_CATEGORIES,
            )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def get_order_by_id(order_id: int) -> Optional[Dict[str, Any]]:
    async with get_connection() as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cursor.fetchone()

async def search_orders(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    pattern = f"%{query.strip()}%"
    async with get_connection() as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        placeholders = ",".join("?" for _ in VALID_IT_CATEGORIES)
        cursor = await db.execute(
            f"""
            SELECT * FROM orders 
            WHERE (title LIKE ? OR description LIKE ?)
              AND category IN ({placeholders})
            ORDER BY id DESC LIMIT ?
            """,
            (pattern, pattern, *VALID_IT_CATEGORIES, limit),
        )
        return await cursor.fetchall()

async def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    async with get_connection() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with get_connection() as db:
        db.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def update_user_categories(user_id: int, categories: List[str]) -> None:
    cat_str = ",".join(categories)
    async with get_connection() as db:
        await db.execute("UPDATE users SET categories = ? WHERE user_id = ?", (cat_str, user_id))
        await db.commit()

async def toggle_notifications(user_id: int) -> bool:
    async with get_connection() as db:
        cursor = await db.execute("SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        new_val = 0 if (row and row[0] == 1) else 1
        await db.execute("UPDATE users SET notifications_enabled = ? WHERE user_id = ?", (new_val, user_id))
        await db.commit()
        return bool(new_val)

async def get_subscribed_users(category: str) -> List[int]:
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT user_id, categories FROM users WHERE notifications_enabled = 1"
        )
        rows = await cursor.fetchall()
        result = []
        for uid, cats in rows:
            cat_list = [c.strip() for c in (cats or "").split(",") if c.strip()]
            if category in cat_list or "all" in cat_list:
                result.append(uid)
        return result

async def is_delivered(order_id: int, user_id: int) -> bool:
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT 1 FROM order_deliveries WHERE order_id = ? AND user_id = ?",
            (order_id, user_id),
        )
        return await cursor.fetchone() is not None

async def mark_delivered(order_id: int, user_id: int) -> None:
    async with get_connection() as db:
        await db.execute(
            "INSERT OR IGNORE INTO order_deliveries (order_id, user_id) VALUES (?, ?)",
            (order_id, user_id),
        )
        await db.commit()
