import asyncio
import logging
from typing import List
import aiohttp
import feedparser

from parsers.base import ParsedOrder
from parsers.classifier import classify_text, extract_budget, extract_tg_contact
from parsers.deduplicator import clean_html, generate_hash

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"source": "FL.ru", "url": "https://www.fl.ru/rss/all.xml"},
    {"source": "Freelancehunt", "url": "https://freelancehunt.com/projects.rss"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

async def fetch_single_feed(session: aiohttp.ClientSession, feed_info: dict) -> List[ParsedOrder]:
    orders: List[ParsedOrder] = []
    source = feed_info["source"]
    url = feed_info["url"]

    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                logger.warning(f"Ошибка загрузки RSS {source}: HTTP {resp.status}")
                return orders
            content = await resp.text()
    except Exception as e:
        logger.warning(f"Сбой при запросе к RSS {source}: {e}")
        return orders

    feed = feedparser.parse(content)
    for entry in feed.entries:
        title = clean_html(getattr(entry, "title", "")).strip()
        link = getattr(entry, "link", "").strip()
        raw_desc = getattr(entry, "summary", "") or getattr(entry, "description", "")
        description = clean_html(raw_desc).strip()
        guid = getattr(entry, "id", None) or getattr(entry, "guid", None) or link

        if not title or not link:
            continue

        # Строгая фильтрация только по IT-направлениям
        category = classify_text(title, description)
        if not category:
            continue

        budget = extract_budget(f"{title} {description}")
        contact = extract_tg_contact(description)
        content_hash = generate_hash(title, description)

        orders.append(
            ParsedOrder(
                source=source,
                title=title,
                link=link,
                description=description[:800],
                budget=budget,
                category=category,
                content_hash=content_hash,
                contact=contact,
                external_id=str(guid),
            )
        )
    return orders

async def fetch_all_rss_orders() -> List[ParsedOrder]:
    all_orders: List[ParsedOrder] = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_single_feed(session, feed_info) for feed_info in RSS_FEEDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_orders.extend(res)
    return all_orders
