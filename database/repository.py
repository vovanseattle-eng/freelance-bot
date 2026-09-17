import re
from typing import Optional, List, Dict, Any
from database.db import get_connection

VALID_IT_CATEGORIES = ("dev", "design", "smm", "copywriting", "video")

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


async def is_terms_accepted(user_id: int) -> bool:
    """Проверяет принятие условий сервиса пользователем."""
    async with get_connection() as db:
        cursor = await db.execute(
            "SELECT 1 FROM terms_acceptances WHERE user_id = ?",
            (user_id,),
        )
        return await cursor.fetchone() is not None


async def record_terms_acceptance(user_id: int) -> None:
    """Сохраняет факт принятия условий сервиса."""
    async with get_connection() as db:
        await db.execute(
            "INSERT OR REPLACE INTO terms_acceptances (user_id) VALUES (?)",
            (user_id,),
        )
        await db.commit()

