"""Живое состояние агрегатора: счётчики заказов и кэш дедупликации в RAM.

Заказы НЕ пишутся в базу: всё живёт в памяти (кольцевой кэш на 2000 хэшей
~ 150 КБ + счётчики). Экономит диск и память VPS, база остаётся только
для пользователей и их настроек.
"""
import time

from parsers.deduplicator import SeenOrdersCache

IT_CATEGORIES = ("dev", "design", "smm", "copywriting", "video")

# Момент старта процесса (unix time)
START_TIME: float = time.time()

# Кольцевой кэш последних 2000 хэшей (~150 КБ RAM) — защита от повторных пушей
seen_orders = SeenOrdersCache(max_size=2000)

# Счётчики уникальных заказов с момента запуска
_category_counter: dict[str, int] = {c: 0 for c in IT_CATEGORIES}
_total_seen: int = 0


def register_order(category: str) -> None:
    """Фиксирует новый уникальный заказ в RAM-счётчиках."""
    global _total_seen
    _total_seen += 1
    if category in _category_counter:
        _category_counter[category] += 1


def get_stats() -> dict:
    """Снимок статистики для экрана «Статистика»."""
    return {
        "uptime_seconds": max(0, int(time.time() - START_TIME)),
        "total_seen": _total_seen,
        "per_category": dict(_category_counter),
    }


def format_uptime(seconds: int) -> str:
    """Компактный человекочитаемый аптайм."""
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days} д {hours} ч"
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"
