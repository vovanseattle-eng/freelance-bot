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


if __name__ == "__main__":
    unittest.main()
