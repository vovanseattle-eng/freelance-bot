import asyncio
import logging
from typing import List
import aiohttp
from bs4 import BeautifulSoup

import config
from parsers.base import ParsedOrder
from parsers.classifier import classify_text, extract_budget, extract_tg_contact
from parsers.deduplicator import generate_hash

logger = logging.getLogger(__name__)

# Расширенный список проверенных IT и Digital каналов с прямыми контактами заказчиков
TARGET_CHANNELS = [
    # Разработка и IT (Web, Backend, Frontend, QA, Mobile)
    "it_vacancies",
    "tproger_jobs",
    "forwebdev",
    "mobile_jobs",
    "qa_jobs",
    "devs_jobs",
    "jobgeeks",
    "devjobs",
    "front_jobs",
    "webfrl",
    "itmozg",
    "habr_career",
    "it_hunters",
    "datasciencejobs",
    "work_it",
    "it_vakansii_jobs",
    "remote_it_jobs",
    "remoteit",

    # Дизайн и UI/UX
    "design_jobs",
    "uiux_jobs",
    "designer_ru",

    # Маркетинг, SMM, Трафик, SEO
    "smm_vacancies",
    "marketing_jobs",
    "seojobs",
    "product_jobs",

    # Копирайтинг и Тексты
    "text_jobs",

    # Фриланс и удаленная работа с прямыми контактами
    "freelancetaverna",
    "distantsiya",
    "forfreelancers",
    "normrabota",
    "theyseeku",
    "digital_rabota",
    "young_relocate",
    "remotejob",
    "freelance_rabota",
    "freelance_projects",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

async def fetch_channel_posts(session: aiohttp.ClientSession, channel: str) -> List[ParsedOrder]:
    orders: List[ParsedOrder] = []
    url = f"https://t.me/s/{channel}"
    proxy = config.TELEGRAM_PROXY or "http://127.0.0.1:10809"

    try:
        async with session.get(url, headers=HEADERS, proxy=proxy, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return orders
            html = await resp.text()
    except Exception as e:
        logger.debug(f"Канал @{channel}: {e}")
        return orders

    soup = BeautifulSoup(html, "html.parser")
    widgets = soup.select(".tgme_widget_message_wrap")

    for w in widgets:
        text_el = w.select_one(".tgme_widget_message_text")
        if not text_el:
            continue

        raw_text = text_el.get_text(separator="\n").strip()
        if len(raw_text) < 30:
            continue

        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        title = lines[0][:100] if lines else f"Заказ из @{channel}"

        # Строгая фильтрация: только IT / Digital
        category = classify_text(title, raw_text)
        if not category:
            continue

        node = w.select_one(".tgme_widget_message")
        post_attr = node.get("data-post", "") if node else ""
        link = f"https://t.me/{post_attr}" if post_attr else f"https://t.me/{channel}"

        budget = extract_budget(raw_text)
        contact = extract_tg_contact(raw_text)
        content_hash = generate_hash(title, raw_text)

        orders.append(
            ParsedOrder(
                source=f"TG: @{channel}",
                title=title,
                link=link,
                description=raw_text[:800],
                budget=budget,
                category=category,
                content_hash=content_hash,
                contact=contact,
                external_id=post_attr or link,
            )
        )

    return orders

async def fetch_all_channel_orders() -> List[ParsedOrder]:
    all_orders: List[ParsedOrder] = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_channel_posts(session, ch) for ch in TARGET_CHANNELS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                all_orders.extend(res)
    return all_orders
