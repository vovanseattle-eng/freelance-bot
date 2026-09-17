import unittest
import asyncio
from database.db import init_db
from database import repository
from bot.keyboards import get_unified_gate_kb, get_terms_doc_kb, BLUE


class TestFreelanceGate(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await init_db()

    async def test_terms_acceptance_storage(self):
        import time
        uid = int(time.time() * 1000)
        self.assertFalse(await repository.is_terms_accepted(uid))
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


    def test_seen_orders_cache_deduplication(self):
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


if __name__ == "__main__":
    unittest.main()

