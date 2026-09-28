"""
Полный набор тестов FREELANCE RADAR.

Покрывает:
- дверь (gate): подписка + принятие условий
- хранилище пользователей (SQLite): настройки, уведомления, соглашения
- RAM-статистику (bot.state): регистрация заказов, аптайм
- дедупликацию (SeenOrdersCache): FIFO, вытеснение, обработка пустых хэшей
- классификатор: распределение по категориям, отсев офлайн-спама, бюджет, контакты
- парсеры: чистка HTML, безопасная обрезка, стабильные хэши, структура клавиатур
- main: обработка заказов с дедупликацией и таймауты сборщика

Запуск: pytest tests/ -v
"""
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from database.db import init_db
from database import repository
from bot.keyboards import (
    get_unified_gate_kb, get_terms_doc_kb, get_subscription_kb,
    main_menu_kb, settings_kb, push_order_kb, BLUE,
)
from bot.emoji import E, em, title


class TestFreelanceGate(unittest.IsolatedAsyncioTestCase):
    """Онбординг: подписка на канал + принятие условий."""

    async def asyncSetUp(self):
        await init_db()

    async def test_terms_acceptance_storage(self):
        import time
        uid = int(time.time() * 1000)
        self.assertFalse(await repository.is_terms_accepted(uid))
        await repository.record_terms_acceptance(uid)
        self.assertTrue(await repository.is_terms_accepted(uid))
        # Повторная запись не падает (INSERT OR REPLACE)
        await repository.record_terms_acceptance(uid)
        self.assertTrue(await repository.is_terms_accepted(uid))

    def test_unified_gate_kb_structure(self):
        from legal_texts import TERMS_URL
        kb = get_unified_gate_kb("https://t.me/vitnevoyte")
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0].text, "Подписаться на канал")
        self.assertEqual(rows[0][0].url, "https://t.me/vitnevoyte")
        self.assertEqual(rows[1][0].text, "Пользовательское соглашение")
        self.assertEqual(rows[1][0].url, TERMS_URL)
        self.assertEqual(rows[2][0].text, "Принять условия и войти")
        self.assertEqual(rows[2][0].callback_data, "action:accept_gate")
        self.assertEqual(rows[2][0].style, BLUE)

    def test_terms_doc_kb_structure(self):
        from legal_texts import TERMS_URL
        kb = get_terms_doc_kb()
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0].text, "Читать статью в Telegram")
        self.assertEqual(rows[0][0].url, TERMS_URL)
        self.assertEqual(rows[1][0].text, "Принять условия и войти")
        self.assertEqual(rows[1][0].callback_data, "action:accept_gate")
        self.assertEqual(rows[2][0].text, "Назад")
        self.assertEqual(rows[2][0].callback_data, "gate:back")

    def test_subscription_kb_structure(self):
        kb = get_subscription_kb("https://t.me/vitnevoyte")
        rows = kb.inline_keyboard
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0].text, "Подписаться на канал")
        self.assertEqual(rows[1][0].text, "Проверить подписку")
        self.assertEqual(rows[1][0].callback_data, "check_subscription")

    async def test_upsert_user_idempotent(self):
        uid = 555001
        await repository.upsert_user(uid, "old_name", "Old")
        await repository.upsert_user(uid, "new_name", "New")
        user = await repository.get_user(uid)
        self.assertEqual(user["username"], "new_name")
        self.assertEqual(user["first_name"], "New")


class TestUserRepository(unittest.IsolatedAsyncioTestCase):
    """SQLite-хранилище пользователей и настроек."""

    async def asyncSetUp(self):
        await init_db()

    async def test_user_subscriptions(self):
        uid = 777123
        await repository.upsert_user(uid, "testuser", "Test")
        await repository.update_user_categories(uid, ["dev", "design"])
        subscribers_dev = await repository.get_subscribed_users("dev")
        self.assertIn(uid, subscribers_dev)

        subscribers_video = await repository.get_subscribed_users("video")
        self.assertNotIn(uid, subscribers_video)

        # Выключение уведомлений
        new_state = await repository.toggle_notifications(uid)
        self.assertFalse(new_state)
        subscribers_dev_off = await repository.get_subscribed_users("dev")
        self.assertNotIn(uid, subscribers_dev_off)

        # Включение обратно
        new_state = await repository.toggle_notifications(uid)
        self.assertTrue(new_state)

    async def test_all_category_subscription(self):
        uid = 777124
        await repository.upsert_user(uid, "alluser", "All")
        await repository.update_user_categories(uid, ["all"])
        for cat in ("dev", "design", "smm", "copywriting", "video"):
            self.assertIn(uid, await repository.get_subscribed_users(cat))

    async def test_default_categories(self):
        uid = 777125
        await repository.upsert_user(uid, None, "Defaults")
        user = await repository.get_user(uid)
        cats = [c.strip() for c in user["categories"].split(",")]
        self.assertEqual(set(cats), {"dev", "design", "smm", "copywriting", "video"})
        self.assertEqual(user["notifications_enabled"], 1)

    async def test_stats_counters(self):
        uid_a = int(time.time() * 1000) + 1
        uid_b = int(time.time() * 1000) + 2
        total_before = await repository.count_users()
        await repository.upsert_user(uid_a, "stats1", "S1")
        await repository.upsert_user(uid_b, "stats2", "S2")
        total_after = await repository.count_users()
        self.assertGreaterEqual(total_after - total_before, 2)

        enabled_before = await repository.count_notif_enabled()
        await repository.toggle_notifications(uid_a)  # выкл
        self.assertEqual(await repository.count_notif_enabled(), enabled_before - 1)
        await repository.toggle_notifications(uid_a)  # снова вкл
        self.assertEqual(await repository.count_notif_enabled(), enabled_before)

    async def test_no_orders_table(self):
        """Заказы больше не хранятся в базе: таблица orders не существует."""
        from database.db import get_connection
        async with get_connection() as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
            )
            self.assertIsNone(await cursor.fetchone())


class TestBotState(unittest.IsolatedAsyncioTestCase):
    """RAM-статистика: заказы не пишутся в базу, счётчики живут в памяти."""

    def test_register_order_counts(self):
        from bot import state
        # Сброс через новый словарь не нужен: проверяем инкремент
        before = state.get_stats()["total_seen"]
        state.register_order("dev")
        state.register_order("dev")
        state.register_order("design")
        after = state.get_stats()
        self.assertEqual(after["total_seen"], before + 3)
        self.assertGreaterEqual(after["per_category"]["dev"], 2)
        self.assertGreaterEqual(after["per_category"]["design"], 1)

    def test_register_unknown_category(self):
        from bot import state
        before = state.get_stats()["total_seen"]
        state.register_order("unknown_cat")  # не должен упасть
        self.assertEqual(state.get_stats()["total_seen"], before + 1)

    def test_uptime_formatting(self):
        from bot.state import format_uptime
        self.assertEqual(format_uptime(30), "0 мин")
        self.assertEqual(format_uptime(300), "5 мин")
        self.assertEqual(format_uptime(7200), "2 ч 0 мин")
        self.assertEqual(format_uptime(90000), "1 д 1 ч")

    def test_get_stats_structure(self):
        from bot.state import get_stats
        s = get_stats()
        self.assertIn("uptime_seconds", s)
        self.assertIn("total_seen", s)
        self.assertIn("per_category", s)
        for cat in ("dev", "design", "smm", "copywriting", "video"):
            self.assertIn(cat, s["per_category"])


class TestSeenOrdersCache(unittest.TestCase):
    """Дедупликация: кольцевой кэш с вытеснением старых хэшей."""

    def test_deduplication(self):
        from parsers.deduplicator import SeenOrdersCache
        cache = SeenOrdersCache(max_size=3)
        self.assertTrue(cache.is_new("hash1"))
        self.assertTrue(cache.is_new("hash2"))
        self.assertTrue(cache.is_new("hash3"))

        # Дубликат должен отсекаться
        self.assertFalse(cache.is_new("hash1"))
        self.assertFalse(cache.is_new("hash2"))

        # При добавлении 4-го элемента самый старый (hash1) вытесняется
        self.assertTrue(cache.is_new("hash4"))
        self.assertEqual(len(cache), 3)
        self.assertNotIn("hash1", cache)
        self.assertIn("hash4", cache)

    def test_empty_and_none_hashes(self):
        from parsers.deduplicator import SeenOrdersCache
        cache = SeenOrdersCache(max_size=10)
        self.assertFalse(cache.is_new(""))
        self.assertFalse(cache.is_new(None))
        self.assertEqual(len(cache), 0)

    def test_memory_bound(self):
        """Кэш не растёт бесконечно: жёсткий потолок max_size."""
        from parsers.deduplicator import SeenOrdersCache
        cache = SeenOrdersCache(max_size=100)
        for i in range(5000):
            cache.is_new(f"h{i}")
        self.assertEqual(len(cache), 100)


class TestDeduplicationHelpers(unittest.TestCase):
    def test_generate_hash_stable(self):
        from parsers.deduplicator import generate_hash
        h1 = generate_hash("Тест заказа №1", "Описание тестового заказа")
        h2 = generate_hash("ТЕСТ ЗАКАЗА №1", "Описание тестового заказа")
        h3 = generate_hash("Совсем другой заказ", "Другое описание")
        self.assertEqual(h1, h2)  # регистр не важен
        self.assertNotEqual(h1, h3)

    def test_clean_html(self):
        from parsers.deduplicator import clean_html
        raw = "<p>Привет</p><br><b>Мир</b><div>&amp; ещё</div>"
        result = clean_html(raw)
        self.assertNotIn("<", result)
        self.assertIn("Привет", result)
        self.assertIn("& ещё", result)

    def test_safe_truncate_html_closes_tags(self):
        from parsers.deduplicator import safe_truncate_html
        long_html = "<b>Жирный текст " + "очень длинный " * 100 + "</b>"
        result = safe_truncate_html(long_html, max_len=100)
        self.assertLessEqual(len(result), 110)
        # BeautifulSoup закрывает открытые теги — баланс соблюдён
        self.assertEqual(result.count("<b>"), result.count("</b>"))


class TestClassifier(unittest.TestCase):
    def test_dev_order(self):
        from parsers.classifier import classify_text
        self.assertEqual(classify_text("Нужен Python разработчик", "Сделать бота на FastAPI, API интеграции"), "dev")

    def test_design_order(self):
        from parsers.classifier import classify_text
        self.assertEqual(classify_text("Требуется дизайнер", "Логотип и фирменный стиль в Figma"), "design")

    def test_smm_order(self):
        from parsers.classifier import classify_text
        self.assertEqual(classify_text("SMM специалист", "Ведение канала, контент-план, продвижение"), "smm")

    def test_copywriting_order(self):
        from parsers.classifier import classify_text
        self.assertEqual(classify_text("Копирайтер нужен", "Написать статью и посты для блога"), "copywriting")

    def test_video_order(self):
        from parsers.classifier import classify_text
        self.assertEqual(classify_text("Видеомонтажер", "Монтаж роликов для YouTube, субтитры"), "video")

    def test_offline_rejected(self):
        from parsers.classifier import classify_text
        self.assertIsNone(classify_text("Требуется повар", "В кафе, график 2/2, оплата ежедневно"))
        self.assertIsNone(classify_text("Курьер на личном авто", "Доставка документов, оплата за рейс"))

    def test_no_match_rejected(self):
        from parsers.classifier import classify_text
        self.assertIsNone(classify_text("Куплю гараж", "Недорого, район центра"))

    def test_title_boost(self):
        """Ключевик в заголовке весит больше, чем в теле."""
        from parsers.classifier import classify_text
        cat = classify_text("Разработчик Python", "и немного дизайна логотипов")
        self.assertEqual(cat, "dev")

    def test_budget_extraction(self):
        from parsers.classifier import extract_budget
        self.assertEqual(extract_budget("Бюджет: 5000 руб"), "5000 руб")
        self.assertEqual(extract_budget("оплата 1500 ₽ за статью"), "1500 ₽")
        self.assertEqual(extract_budget("Ничего не указано"), "По договоренности")

    def test_contact_extraction(self):
        from parsers.classifier import extract_tg_contact
        self.assertEqual(extract_tg_contact("Пишите: @customer123"), "customer123")
        self.assertEqual(extract_tg_contact("t.me/mycustomer123"), "mycustomer123")
        # Исключённые каналы не считаются контактами
        self.assertNotEqual(extract_tg_contact("Канал: @it_vacancies, пишите @realguy123"), "it_vacancies")
        self.assertIsNone(extract_tg_contact("Нет контактов"))

    def test_is_spam_compat(self):
        from parsers.classifier import is_spam
        self.assertTrue(is_spam("Требуется официант в ресторан"))
        self.assertFalse(is_spam("Нужен Python разработчик для API"))


class TestParsers(unittest.IsolatedAsyncioTestCase):
    def test_parsed_order_dataclass(self):
        from parsers.base import ParsedOrder
        o = ParsedOrder(
            source="Test", title="T", link="https://t.me/x/1", description="D",
            budget="100 руб", category="dev", content_hash="h",
        )
        self.assertEqual(o.contact, None)
        self.assertEqual(o.external_id, None)

    async def test_fetch_all_rss_orders_smoke(self):
        """Сборщик RSS возвращает список (может быть пустым при проблемах сети — это не падение)."""
        from parsers.rss_boards import fetch_all_rss_orders
        try:
            result = await asyncio.wait_for(fetch_all_rss_orders(), timeout=40)
            self.assertIsInstance(result, list)
        except asyncio.TimeoutError:
            self.skipTest("Сеть недоступна")

    async def test_fetch_all_channel_orders_smoke(self):
        from parsers.tg_web_scraper import fetch_all_channel_orders
        try:
            result = await asyncio.wait_for(fetch_all_channel_orders(), timeout=60)
            self.assertIsInstance(result, list)
        except asyncio.TimeoutError:
            self.skipTest("Сеть недоступна")


class TestMainLogic(unittest.IsolatedAsyncioTestCase):
    def test_process_new_order_dedup_and_counters(self):
        """process_new_order: первый вызов пушит, второй с тем же хэшем — нет."""
        from parsers.base import ParsedOrder
        import main as main_module
        from bot import state

        bot_mock = AsyncMock()
        order = ParsedOrder(
            source="Test", title="Уникальный заказ о тестах", link="https://t.me/x/2",
            description="Описание", budget="1 руб", category="dev",
            content_hash=f"test_hash_{time.time()}",
        )

        async def run():
            with patch.object(main_module, "notify_subscribers", new=AsyncMock()) as mock_notify:
                await main_module.process_new_order(bot_mock, order)
                await main_module.process_new_order(bot_mock, order)  # дубликат
                self.assertEqual(mock_notify.await_count, 1)

        asyncio.run(run())

    def test_await_with_timeout(self):
        """Зависший источник не блокирует цикл: обёртка возвращает [] по таймауту."""
        import main as main_module

        async def sleepy():
            await asyncio.sleep(30)

        async def run():
            result = await main_module.await_with_timeout(sleepy(), 0.1, "test")
            self.assertEqual(result, [])

        asyncio.run(run())

    def test_collector_worker_survives_errors(self):
        """Цикл сборщика не умирает от исключений источников."""
        import main as main_module
        import config

        bot_mock = MagicMock()

        async def failing():
            raise RuntimeError("network down")

        async def run():
            orig_interval = config.RSS_POLL_INTERVAL
            config.RSS_POLL_INTERVAL = 0.05
            with patch.object(main_module, "fetch_all_rss_orders", new=failing), \
                 patch.object(main_module, "fetch_all_channel_orders", new=failing):
                worker = asyncio.create_task(main_module.orders_collector_worker(bot_mock))
                await asyncio.sleep(0.2)
                self.assertFalse(worker.done())  # жив, несмотря на ошибки
                worker.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await worker
            config.RSS_POLL_INTERVAL = orig_interval

        asyncio.run(run())


class TestKeyboards(unittest.TestCase):
    def test_main_menu(self):
        kb = main_menu_kb()
        self.assertEqual(len(kb.inline_keyboard), 1)
        self.assertEqual(kb.inline_keyboard[0][0].callback_data, "settings")

    def test_push_order_kb_with_contact(self):
        kb = push_order_kb("https://t.me/x/1", contact="@customer")
        texts = [b.text for row in kb.inline_keyboard for b in row]
        self.assertTrue(any("Откликнуться" in t for t in texts))
        self.assertTrue(any("Источник" in t for t in texts))

    def test_push_order_kb_without_contact(self):
        kb = push_order_kb("https://t.me/x/1")
        texts = [b.text for row in kb.inline_keyboard for b in row]
        self.assertFalse(any("Откликнуться" in t for t in texts))

    def test_settings_kb_marks_active(self):
        kb = settings_kb(["dev"], True)
        texts = [b.text for row in kb.inline_keyboard for b in row]
        self.assertTrue(any("[ON]" in t for t in texts))
        self.assertTrue(any("[OFF]" in t for t in texts))
        self.assertTrue(any("Уведомления: Включены" in t for t in texts))


class TestEmoji(unittest.TestCase):
    def test_em_html_format(self):
        result = em(E.FIRE)
        self.assertTrue(result.startswith('<tg-emoji emoji-id="'))
        self.assertTrue(result.endswith("</tg-emoji>"))

    def test_title_format(self):
        result = title(E.BELL, "Заголовок")
        self.assertIn("<b>", result)
        self.assertIn("Заголовок", result)


if __name__ == "__main__":
    unittest.main()
