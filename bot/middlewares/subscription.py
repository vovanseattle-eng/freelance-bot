import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, FSInputFile, InputMediaAnimation

import config
from bot.keyboards import get_subscription_kb
from bot.services.subscription import check_user_subscription, format_subscription_required_text

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """Outer Middleware для обязательной проверки подписки на канал @vitnevoyte."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if not user or user.is_bot:
            return await handler(event, data)

        # 1. Разрешаем события онбординга и правовой информации
        if isinstance(event, CallbackQuery) and event.data in (
            "check_subscription",
            "action:accept_gate",
            "legal:terms",
            "gate:back",
        ):
            return await handler(event, data)

        raw_text = getattr(event, "text", None)
        if raw_text:
            cmd = raw_text.split()[0].split("@")[0].lower()
            if cmd in ("/terms", "/help"):
                return await handler(event, data)

        bot = data.get("bot")
        if not bot:
            return await handler(event, data)

        is_sub = await check_user_subscription(bot, user.id)
        if is_sub:
            return await handler(event, data)

        from legal_texts import UNIFIED_GATE_SCREEN
        from bot.keyboards import get_unified_gate_kb

        text = UNIFIED_GATE_SCREEN
        kb = get_unified_gate_kb(config.CHANNEL_URL)


        if isinstance(event, CallbackQuery):
            await event.answer("Для использования бота необходимо подписаться на канал!", show_alert=True)
            if event.message:
                cached_id = config.get_cached_file_id("menu")
                if (event.message.animation or event.message.photo or event.message.video) and cached_id:
                    try:
                        await event.message.edit_media(
                            media=InputMediaAnimation(media=cached_id, caption=text, parse_mode="HTML"),
                            reply_markup=kb,
                        )
                        return
                    except Exception:
                        pass
                try:
                    await event.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
                    return
                except Exception:
                    pass
                try:
                    await event.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
                    return
                except Exception:
                    pass
            return

        if isinstance(event, Message):
            cached_id = config.get_cached_file_id("menu")
            if cached_id:
                try:
                    await event.answer_animation(
                        animation=cached_id,
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                    return
                except Exception:
                    pass
            elif config.MENU_GIF_PATH.exists():
                try:
                    sent = await event.answer_animation(
                        animation=FSInputFile(config.MENU_GIF_PATH),
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML",
                    )
                    if sent.animation:
                        config.save_cached_file_id("menu", sent.animation.file_id)
                    return
                except Exception:
                    pass
            await event.answer(text=text, reply_markup=kb, parse_mode="HTML")
            return

        return
