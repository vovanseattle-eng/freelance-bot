import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.emoji import E, em, title
from bot.keyboards import back_to_menu_kb, push_order_kb
from database import repository

router = Router()

class SearchState(StatesGroup):
    waiting_query = State()

@router.callback_query(F.data == "search_prompt")
async def cb_search_prompt(call: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(SearchState.waiting_query)
        text = (
            f"{title(E.EDIT, 'Поиск IT-заказов')}\n\n"
            f"Введите поисковый запрос (например: <code>Python</code>, <code>Figma</code>, <code>Reels</code>, <code>React</code>):"
        )
        if call.message:
            if call.message.animation or call.message.photo or call.message.video:
                await call.message.edit_caption(caption=text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
            else:
                await call.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.message(SearchState.waiting_query)
async def handle_search_query(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Запрос слишком короткий. Введите минимум 2 символа.")
        return

    await state.clear()
    orders = await repository.search_orders(query, limit=5)

    if not orders:
        text = (
            f"{title(E.INFO, 'Результаты поиска')}\n\n"
            f"По запросу «<b>{html.escape(query)}</b>» подходящих IT-заказов не найдено.\n"
            f"Попробуйте другое ключевое слово."
        )
        await message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        return

    await message.answer(
        f"{title(E.FILE, 'Найдено по запросу')} «<b>{html.escape(query)}</b>» ({len(orders)}):\n",
        parse_mode="HTML",
    )

    for ord_item in orders:
        safe_title = html.escape(ord_item["title"])
        safe_budget = html.escape(ord_item["budget"] or "По договоренности")
        safe_source = html.escape(ord_item["source"])
        contact = ord_item.get("contact")

        contact_text = ""
        if contact:
            clean_contact = contact.lstrip("@")
            contact_text = f" • {em(E.PROFILE)} @{clean_contact}"

        card_text = (
            f"<b>{safe_title}</b>\n"
            f"{em(E.COIN)} {safe_budget} • {em(E.TAG)} {safe_source}{contact_text}"
        )
        await message.answer(
            card_text,
            reply_markup=push_order_kb(ord_item["link"], contact=contact),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    await message.answer("Главное меню:", reply_markup=back_to_menu_kb())
