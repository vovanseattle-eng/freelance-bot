import logging
import html
from aiogram import Bot
from aiogram.types import FSInputFile
from bot.emoji import E, em, title
from bot.keyboards import push_order_kb, CATEGORY_NAMES
from parsers.base import ParsedOrder
from parsers.deduplicator import safe_truncate_html
from database import repository
import config

logger = logging.getLogger(__name__)

_cached_notif_file_id = None

async def notify_subscribers(bot: Bot, order: ParsedOrder, order_id: int) -> None:
    """Рассылает карточку нового заказа подписчикам категории с анимированной GIF-шапкой."""
    global _cached_notif_file_id
    user_ids = await repository.get_subscribed_users(order.category)
    if not user_ids:
        return

    cat_name = CATEGORY_NAMES.get(order.category, "IT & Freelance")
    safe_title = html.escape(order.title)
    safe_source = html.escape(order.source)
    safe_budget = html.escape(order.budget or "По договоренности")

    contact_str = ""
    if order.contact:
        clean_contact = order.contact.lstrip("@")
        contact_str = f"\n{em(E.PROFILE)} <b>Отклик:</b> @{clean_contact}"

    # Безопасное сохранение форматирования и ссылок в теле
    desc_html = safe_truncate_html(order.description or "", max_len=750)

    text = (
        f"{title(E.FIRE, 'Новая IT-вакансия')}  •  <a href=\"{order.link}\">{safe_source}</a>\n\n"
        f"<b>{safe_title}</b>\n\n"
        f"{em(E.JOB)} <b>Направление:</b> {cat_name}\n"
        f"{em(E.COIN)} <b>Оплата:</b> {safe_budget}"
        f"{contact_str}\n\n"
        f"{desc_html}\n"
    )

    kb = push_order_kb(order.link, contact=order.contact)

    has_gif = config.NOTIF_GIF_PATH.exists()

    for uid in user_ids:
        if await repository.is_delivered(order_id, uid):
            continue
        try:
            if has_gif:
                media_input = _cached_notif_file_id or FSInputFile(config.NOTIF_GIF_PATH)
                try:
                    sent = await bot.send_animation(
                        chat_id=uid,
                        animation=media_input,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                    if sent.animation:
                        _cached_notif_file_id = sent.animation.file_id
                except Exception:
                    sent = await bot.send_animation(
                        chat_id=uid,
                        animation=FSInputFile(config.NOTIF_GIF_PATH),
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=kb,
                    )
                    if sent.animation:
                        _cached_notif_file_id = sent.animation.file_id
            else:
                await bot.send_message(
                    chat_id=uid,
                    text=text,
                    parse_mode="HTML",
                    reply_markup=kb,
                    disable_web_page_preview=True,
                )
            await repository.mark_delivered(order_id, uid)
        except Exception as e:
            logger.debug(f"Не удалось отправить пуш пользователю {uid}: {e}")
