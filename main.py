import asyncio
import logging
import sys

# Настройка UTF-8 для корректного логирования эмодзи в консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonCommands

import config
from database.db import init_db
from database import repository
from parsers.rss_boards import fetch_all_rss_orders
from parsers.tg_web_scraper import fetch_all_channel_orders
from parsers.base import ParsedOrder
from bot.notifier import notify_subscribers
from bot.handlers import start, feed, settings, search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("freelance_aggregator")

async def process_new_order(bot: Bot, order: ParsedOrder) -> None:
    """Сохраняет IT-заказ в базу и отправляет пуш подписчикам при успехе."""
    order_id = await repository.save_order(
        source=order.source,
        title=order.title,
        link=order.link,
        category=order.category,
        content_hash=order.content_hash,
        external_id=order.external_id,
        description=order.description,
        budget=order.budget,
        contact=order.contact,
    )
    if order_id:
        contact_info = f" [Контакт: @{order.contact}]" if order.contact else ""
        logger.info(f"Новая вакансия [{order.category}] из {order.source}: {order.title[:45]}{contact_info}")
        await notify_subscribers(bot, order, order_id)

async def orders_collector_worker(bot: Bot) -> None:
    """Фоновый сбор вакансий только по IT из бирж и Telegram-каналов."""
    logger.info("Запущен сборщик IT вакансий (биржи + TG-каналы).")
    while True:
        try:
            # 1. Биржи
            rss_orders = await fetch_all_rss_orders()
            for ord_item in rss_orders:
                await process_new_order(bot, ord_item)

            # 2. Специализированные Telegram-каналы
            tg_orders = await fetch_all_channel_orders()
            for ord_item in tg_orders:
                await process_new_order(bot, ord_item)
        except Exception as e:
            logger.error(f"Ошибка в цикле сборщика: {e}")
        await asyncio.sleep(config.RSS_POLL_INTERVAL)

async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает системные команды и кнопку Меню у поля ввода."""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="search", description="Поиск IT-заказов"),
        BotCommand(command="feed", description="Лента по категориям"),
        BotCommand(command="settings", description="Фильтры и уведомления"),
        BotCommand(command="stats", description="Статистика базы"),
    ]
    try:
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        logger.warning(f"Не удалось установить команды бота: {e}")

async def start_health_server() -> None:
    port_str = config.os.getenv("PORT")
    if not port_str:
        return
    try:
        from aiohttp import web
        port = int(port_str)
        app = web.Application()
        app.router.add_get("/", lambda r: web.Response(text="Freelance Bot is running!"))
        app.router.add_get("/health", lambda r: web.Response(text="OK"))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Render health-check HTTP сервер запущен на порту {port}")
    except Exception as e:
        logger.warning(f"Не удалось запустить health-check сервер: {e}")

async def main() -> None:
    logger.info("Инициализация базы данных...")
    await init_db()

    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN не указан в .env! Завершение работы.")
        return

    await start_health_server()

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(feed.router)
    dp.include_router(settings.router)
    dp.include_router(search.router)

    logger.info("IT Фриланс-агрегатор успешно запущен!")

    while True:
        proxy_url = None
        if config.TELEGRAM_PROXY:
            try:
                import socket
                from urllib.parse import urlparse
                p = urlparse(config.TELEGRAM_PROXY)
                host = p.hostname or "127.0.0.1"
                port = p.port or 10809
                with socket.create_connection((host, port), timeout=1.5):
                    proxy_url = config.TELEGRAM_PROXY
            except Exception:
                pass

        if proxy_url:
            logger.info(f"Подключение через прокси: {proxy_url}")
        else:
            logger.info("Прокси 10809 не отвечает, попытка прямого подключения...")

        session = AiohttpSession(proxy=proxy_url) if proxy_url else None
        bot = Bot(
            token=config.BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        await set_bot_commands(bot)

        collector = asyncio.create_task(orders_collector_worker(bot))
        try:
            await dp.start_polling(bot)
        except (KeyboardInterrupt, SystemExit):
            collector.cancel()
            await bot.session.close()
            break
        except Exception as e:
            logger.warning(f"Ошибка соединения с Telegram ({type(e).__name__}: {e}). Переподключение через 5 сек...")
            collector.cancel()
            try:
                await bot.session.close()
            except Exception:
                pass
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
