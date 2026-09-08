import asyncio
import logging
from typing import Callable, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat

import config
from parsers.base import ParsedOrder
from parsers.classifier import classify_text, is_spam, extract_budget
from parsers.deduplicator import generate_hash

logger = logging.getLogger(__name__)

DEFAULT_CHANNELS = [
    "freelancetaverna",
    "distantsiya",
    "normrabota",
    "forfreelancers",
    "smm_vacancies",
    "design_jobs",
    "it_vacancies",
    "work_in_media",
    "vdhl_good",
]

class TelegramListener:
    def __init__(self, on_new_order: Callable[[ParsedOrder], None]):
        self.on_new_order = on_new_order
        self.client: Optional[TelegramClient] = None
        self.is_running = False

    async def start(self) -> None:
        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
            logger.info("TELEGRAM_API_ID/HASH не заданы в .env. Юзербот для TG-каналов отключен.")
            return

        try:
            self.client = TelegramClient(
                config.SESSION_NAME,
                config.TELEGRAM_API_ID,
                config.TELEGRAM_API_HASH,
            )

            await self.client.start(phone=config.TELEGRAM_PHONE if config.TELEGRAM_PHONE else None)
            logger.info("Telethon клиент успешно авторизован.")

            # Регистрация слушателя событий
            @self.client.on(events.NewMessage())
            async def handle_message(event: events.NewMessage.Event):
                await self._process_event(event)

            self.is_running = True
            logger.info(f"Слушатель TG-каналов запущен.")
        except Exception as e:
            logger.warning(f"Не удалось запустить юзербота Telethon: {e}")

    async def _process_event(self, event: events.NewMessage.Event) -> None:
        text = event.raw_text or ""
        if len(text.strip()) < 30 or is_spam(text):
            return

        # Источник сообщения
        chat = await event.get_chat()
        source_title = getattr(chat, "title", "") or "Telegram"
        username = getattr(chat, "username", "")

        # Формирование постоянной ссылки на публикацию
        if username:
            link = f"https://t.me/{username}/{event.id}"
        else:
            link = f"https://t.me/c/{abs(getattr(chat, 'id', 0))}/{event.id}"

        # Заголовок (первая строка или первые 80 символов)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        title = lines[0][:100] if lines else "Новый заказ из Telegram"
        description = text[:900]

        budget = extract_budget(text)
        category = classify_text(title, text)
        content_hash = generate_hash(title, text)

        order = ParsedOrder(
            source=f"TG: {source_title}",
            title=title,
            link=link,
            description=description,
            budget=budget,
            category=category,
            content_hash=content_hash,
            external_id=str(event.id),
        )

        if asyncio.iscoroutinefunction(self.on_new_order):
            await self.on_new_order(order)
        else:
            self.on_new_order(order)

    async def stop(self) -> None:
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.is_running = False
