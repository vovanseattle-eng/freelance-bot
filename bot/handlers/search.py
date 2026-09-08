import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaAnimation
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.emoji import E, em
from bot.keyboards import back_to_menu_kb, push_order_kb
from database import repository
import config

router = Router()

class SearchState(StatesGroup):
    waiting_query = State()

async def execute_search(message: Message, query: str) -> None:
    query = (query or "").strip()
    if len(query) < 2:
        await message.answer(
            f"{em(E.INFO)} <b>Запрос слишком короткий</b>\n"
            f"<blockquote>Введите минимум 2 символа для поиска.</blockquote>",
            reply_markup=back_to_menu_kb(),
            parse_mode="HTML",
        )
        return

    orders = await repository.search_orders(query, limit=5)

    if not orders:
        text = (
            f"{em(E.SEARCH)} <b>Результаты поиска</b>\n\n"
            f"<blockquote>"
            f"По запросу «<code>{html.escape(query)}</code>» подходящих IT-заказов не найдено.\n"
            f"Попробуйте другое ключевое слово (например: <code>бот</code>, <code>Figma</code>, <code>сайт</code>, <code>Python</code>)."
            f"</blockquote>"
        )
        await message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        return

    header_text = (
        f"{em(E.SEARCH)} <b>Результаты поиска:</b> «<code>{html.escape(query)}</code>»\n"
        f"<i>Найдено свежих IT-предложений: {len(orders)}</i>"
    )
    await message.answer(header_text, parse_mode="HTML")

    for ord_item in orders:
        safe_title = html.escape(ord_item["title"])
        safe_budget = html.escape(ord_item.get("budget") or "По договоренности")
        safe_source = html.escape(ord_item.get("source") or "Биржа")
        contact = ord_item.get("contact")

        contact_line = ""
        if contact:
            clean_contact = html.escape(contact.lstrip("@"))
            contact_line = f"\n{em(E.PROFILE)} <b>Контакт:</b> <code>@{clean_contact}</code>"

        card_text = (
            f"<b>{safe_title}</b>\n\n"
            f"<blockquote>"
            f"{em(E.COIN)} <b>Бюджет:</b> <code>{safe_budget}</code>\n"
            f"{em(E.TAG)} <b>Источник:</b> <code>{safe_source}</code>{contact_line}"
            f"</blockquote>"
        )
        await message.answer(
            card_text,
            reply_markup=push_order_kb(ord_item["link"], contact=contact),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    await message.answer("Главное меню:", reply_markup=back_to_menu_kb())

@router.callback_query(F.data == "search_prompt")
async def cb_search_prompt(call: CallbackQuery, state: FSMContext) -> None:
    try:
        await state.set_state(SearchState.waiting_query)
        text = (
            f"{em(E.SEARCH)} <b>Поиск IT-заказов</b>\n\n"
            f"<blockquote>"
            f"Введите поисковый запрос в чат.\n"
            f"Примеры: <code>Python</code>, <code>Telegram бот</code>, <code>Figma</code>, <code>Reels</code>, <code>Тильда</code>"
            f"</blockquote>"
        )
        if not call.message:
            return

        search_id = config.get_cached_file_id("search")
        if call.message.animation or call.message.photo or call.message.video:
            if search_id:
                try:
                    await call.message.edit_media(
                        media=InputMediaAnimation(media=search_id, caption=text, parse_mode="HTML"),
                        reply_markup=back_to_menu_kb(),
                    )
                    return
                except Exception:
                    pass
            await call.message.edit_caption(caption=text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
        else:
            if search_id:
                try:
                    await call.message.delete()
                except Exception:
                    pass
                await call.message.answer_animation(
                    animation=search_id,
                    caption=text,
                    reply_markup=back_to_menu_kb(),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    raw_text = (message.text or "").strip()
    parts = raw_text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        await execute_search(message, parts[1].strip())
    else:
        await state.set_state(SearchState.waiting_query)
        text = (
            f"{em(E.SEARCH)} <b>Поиск IT-заказов</b>\n\n"
            f"<blockquote>"
            f"Введите поисковый запрос (например: <code>Python</code>, <code>Бот</code>, <code>Дизайн</code>, <code>Figma</code>):"
            f"</blockquote>"
        )
        await message.answer(text, reply_markup=back_to_menu_kb(), parse_mode="HTML")

@router.message(SearchState.waiting_query)
async def handle_search_state_query(message: Message, state: FSMContext) -> None:
    await state.clear()
    await execute_search(message, message.text or "")

@router.message(F.text, ~F.text.startswith("/"))
async def handle_direct_text_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await execute_search(message, message.text or "")
