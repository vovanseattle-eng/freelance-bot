import html
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaAnimation, FSInputFile

from bot.emoji import E, em, title
from bot.keyboards import feed_categories_kb, order_card_kb, CATEGORY_NAMES
from parsers.deduplicator import safe_truncate_html
from database import repository
import config

router = Router()

@router.callback_query(F.data == "feed_menu")
async def cb_feed_menu(call: CallbackQuery) -> None:
    try:
        text = (
            f"{title(E.FILE, 'Каталог вакансий')}\n\n"
            f"Выберите интересующее вас IT направление:"
        )
        if not call.message:
            return

        catalog_id = config.get_cached_file_id("catalog")
        if call.message.animation or call.message.photo or call.message.video:
            if catalog_id:
                try:
                    await call.message.edit_media(
                        media=InputMediaAnimation(media=catalog_id, caption=text, parse_mode="HTML"),
                        reply_markup=feed_categories_kb(),
                    )
                    return
                except Exception:
                    pass
            await call.message.edit_caption(caption=text, reply_markup=feed_categories_kb(), parse_mode="HTML")
        else:
            if catalog_id:
                try:
                    await call.message.delete()
                except Exception:
                    pass
                await call.message.answer_animation(
                    animation=catalog_id,
                    caption=text,
                    reply_markup=feed_categories_kb(),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(text, reply_markup=feed_categories_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.callback_query(F.data.startswith("feed:"))
async def cb_feed_category(call: CallbackQuery) -> None:
    try:
        parts = call.data.split(":")
        if len(parts) != 3:
            return

        category = parts[1]
        offset = int(parts[2])

        total = await repository.count_orders(category if category != "all" else None)
        if total == 0:
            text = (
                f"{title(E.INFO, 'База обновляется')}\n\n"
                f"В выбранном направлении пока нет сохраненных предложений.\n"
                f"Сборщик проверяет источники каждые 60 секунд."
            )
            if call.message:
                if call.message.animation or call.message.photo or call.message.video:
                    await call.message.edit_caption(caption=text, reply_markup=feed_categories_kb(), parse_mode="HTML")
                else:
                    await call.message.edit_text(text, reply_markup=feed_categories_kb(), parse_mode="HTML")
            return

        offset = max(0, min(offset, total - 1))
        orders = await repository.get_orders(category=category, limit=1, offset=offset)
        if not orders:
            await call.answer("Заказ не найден", show_alert=True)
            return

        order = orders[0]
        cat_label = CATEGORY_NAMES.get(order["category"], "IT & Freelance")
        safe_title = html.escape(order["title"])
        safe_budget = html.escape(order["budget"] or "По договоренности")
        safe_source = html.escape(order["source"])
        contact = order.get("contact")

        contact_text = ""
        if contact:
            clean_contact = contact.lstrip("@")
            contact_text = f"\n{em(E.PROFILE)} <b>Контакт:</b> @{clean_contact}"

        desc_html = safe_truncate_html(order["description"] or "", max_len=750)

        text = (
            f"{title(E.JOB, cat_label)}  •  {offset + 1} / {total}\n\n"
            f"<b>{safe_title}</b>\n\n"
            f"{em(E.COIN)} <b>Оплата:</b> {safe_budget}\n"
            f"{em(E.LINK)} <b>Источник:</b> <a href=\"{order['link']}\">{safe_source}</a>"
            f"{contact_text}\n\n"
            f"{desc_html}\n"
        )

        kb = order_card_kb(order["link"], category, offset, total, contact=contact)
        if call.message:
            if call.message.animation or call.message.photo or call.message.video:
                try:
                    await call.message.delete()
                except Exception:
                    pass
                await call.message.answer(
                    text,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            else:
                await call.message.edit_text(
                    text,
                    reply_markup=kb,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
    finally:
        await call.answer()
