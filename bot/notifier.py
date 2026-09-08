import logging
import html
from aiogram import Bot
from bot.emoji import E, em, title
from bot.keyboards import push_order_kb, CATEGORY_NAMES
from parsers.base import ParsedOrder
from database import repository

logger = logging.getLogger(__name__)

async def notify_subscribers(bot: Bot, order: ParsedOrder, order_id: int) -> None:
    """Рассылает карточку нового заказа подписчикам категории."""
    user_ids = await repository.get_subscribed_users(order.category)
    if not user_ids:
        return

    cat_name = CATEGORY_NAMES.get(order.category, "IT & Freelance")
    safe_title = html.escape(order.title)
    safe_desc = html.escape(order.description[:400])
    safe_source = html.escape(order.source)
    safe_budget = html.escape(order.budget)

    contact_str = ""
    if order.contact:
        clean_contact = order.contact.lstrip("@")
        contact_str = f"\n{em(E.PROFILE)} <b>Отклик:</b> @{clean_contact}"

    text = (
        f"{title(E.FIRE, 'Новая IT-вакансия')}  •  {safe_source}\n\n"
        f"<b>{safe_title}</b>\n\n"
        f"{em(E.JOB)} <b>Направление:</b> {cat_name}\n"
        f"{em(E.COIN)} <b>Оплата:</b> {safe_budget}"
        f"{contact_str}\n\n"
        f"{safe_desc}\n"
    )

    kb = push_order_kb(order.link, contact=order.contact)

    for uid in user_ids:
        if await repository.is_delivered(order_id, uid):
            continue
        try:
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
