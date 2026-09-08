import asyncio
import logging
import re
from typing import List
import aiohttp
from bs4 import BeautifulSoup

import config
from parsers.base import ParsedOrder
from parsers.classifier import classify_text, extract_budget, extract_tg_contact
from parsers.deduplicator import generate_hash

logger = logging.getLogger(__name__)

# База из 50 проверенных активных IT и фриланс Telegram-каналов
TARGET_CHANNELS = [
    # Разработка и IT (Web, Backend, Frontend, QA, Mobile, Data Science, Gamedev)
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
    "proglib_jobs",
    "startup_jobs",
    "jobforjunior",
    "gamedev_jobs",
    "it_zakazy",

    # Дизайн, UI/UX, Графика
    "design_jobs",
    "uiux_jobs",
    "designer_ru",
    "designhunters",
    "fl_design",

    # Маркетинг, SMM, Продукт, Трафик, SEO
    "smm_vacancies",
    "marketing_jobs",
    "seojobs",
    "product_jobs",
    "tenchat_jobs",
    "rabota_digital",

    # Копирайтинг и Тексты
    "text_jobs",

    # Фриланс и удаленная работа с прямыми контактами заказчиков
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
    "zakazy_freelance",
    "freelancechoice",
    "freelancebazar",
    "freelance_zakaz",
    "freelance_feed",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def extract_post_data(text_el) -> tuple[str, str, str]:
    """Преобразует сырой HTML поста в красивый текст с сохранением ссылок и структуры."""
    el = BeautifulSoup(str(text_el), "html.parser").select_one(".tgme_widget_message_text")
    if not el:
        return "", "", ""

    # Заменяем <br> на нормальный перенос строки
    for br in el.find_all("br"):
        br.replace_with("\n")

    # Обрабатываем ссылки: сохраняем внешние кликабельные href
    for a in el.find_all("a"):
        href = a.get("href", "")
        text = a.get_text()
        if href.startswith("http"):
            a.attrs = {"href": href}
        else:
            # Ссылки поиска по тегам (?q=%23...) заменяем на обычный текст
            a.replace_with(text)

    # Оставляем только безопасные теги форматирования Telegram: a, b, i, code
    for tag in el.find_all(True):
        if tag.name not in ["a", "b", "strong", "i", "em", "code"]:
            tag.unwrap()
        elif tag.name in ["b", "strong"]:
            tag.name = "b"
            tag.attrs = {}
        elif tag.name in ["i", "em"]:
            tag.name = "i"
            tag.attrs = {}
        elif tag.name == "code":
            tag.attrs = {}

    plain_text = el.get_text().strip()
    raw_lines = [l.strip() for l in plain_text.split("\n") if l.strip()]

    # Умный заголовок: ищем первую строку с реальным текстом (пропускаем смайлики типа ⛏, 🔹, ⚡)
    title = ""
    for l in raw_lines:
        clean_l = re.sub(r"[^\w\s]", "", l).strip()
        if len(clean_l) >= 4:
            title = l[:100]
            break
    if not title and raw_lines:
        title = raw_lines[0][:100]

    # Красивый HTML-текст для отображения в Telegram
    formatted_html = el.decode_contents().strip()
    # Склеиваем оторванную пунктуацию (когда точка или запятая на новой строке)
    formatted_html = re.sub(r"\n\s*([.,!?:;])", r"\1", formatted_html)
    # Нормализуем пустые строки (не больше двух подряд)
    formatted_html = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", formatted_html)

    # Если в начале описания дублируется заголовок — убираем дубль
    if title:
        pattern = re.escape(title)
        formatted_html = re.sub(r"^" + pattern + r"\s*", "", formatted_html, flags=re.IGNORECASE).strip()

    return title, plain_text, formatted_html

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

        title, plain_text, formatted_body = extract_post_data(text_el)
        if len(plain_text) < 30:
            continue

        if not title:
            title = f"Заказ из @{channel}"

        # Строгая фильтрация: только IT / Digital
        category = classify_text(title, plain_text)
        if not category:
            continue

        node = w.select_one(".tgme_widget_message")
        post_attr = node.get("data-post", "") if node else ""
        link = f"https://t.me/{post_attr}" if post_attr else f"https://t.me/{channel}"

        budget = extract_budget(plain_text)
        contact = extract_tg_contact(plain_text)
        content_hash = generate_hash(title, plain_text)

        # Сохраняем красивое форматированное тело поста с ссылками
        orders.append(
            ParsedOrder(
                source=f"TG: @{channel}",
                title=title,
                link=link,
                description=formatted_body,
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
