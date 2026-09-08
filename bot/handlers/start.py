from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from bot.emoji import E, em, title
from bot.keyboards import main_menu_kb
from database import repository

router = Router()

def get_main_menu_text() -> str:
    """Единый текст главного экрана для /start и кнопки 'Назад'."""
    return (
        f"{title(E.STAR, 'IT Aggregator')}\n\n"
        f"{em(E.FIRE)} Мониторинг 35+ бирж и каналов в реальном времени.\n"
        f"{em(E.CHECK)} Только IT: разработка, дизайн, тексты, маркетинг.\n\n"
        f"{em(E.PROFILE)} Прямые контакты заказчиков для быстрого отклика."
    )

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    await repository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    await message.answer(get_main_menu_text(), reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    try:
        if call.message:
            await call.message.edit_text(get_main_menu_text(), reply_markup=main_menu_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.callback_query(F.data == "stats")
async def cb_stats(call: CallbackQuery) -> None:
    try:
        total_orders = await repository.count_orders()
        dev_count = await repository.count_orders("dev")
        design_count = await repository.count_orders("design")
        smm_count = await repository.count_orders("smm")
        copy_count = await repository.count_orders("copywriting")
        video_count = await repository.count_orders("video")

        text = (
            f"{title(E.STATS, 'Статистика базы')}\n\n"
            f"{em(E.TOP)} Всего предложений: <b>{total_orders}</b>\n\n"
            f"{em(E.CODE)} Разработка: <b>{dev_count}</b>\n"
            f"{em(E.DESIGN)} Дизайн: <b>{design_count}</b>\n"
            f"{em(E.SMM)} Маркетинг / SMM: <b>{smm_count}</b>\n"
            f"{em(E.WRITE)} Копирайтинг: <b>{copy_count}</b>\n"
            f"{em(E.MEDIA)} Видеомонтаж: <b>{video_count}</b>"
        )
        if call.message:
            await call.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.message(F.entities)
async def handle_user_emojis(message: Message) -> None:
    found = []
    for entity in message.entities or []:
        if entity.type == "custom_emoji":
            char = message.text[entity.offset : entity.offset + entity.length]
            found.append(f"{char} ID: <code>{entity.custom_emoji_id}</code>")
    if found:
        await message.answer(
            f"{title(E.SPARKLE, 'Обнаружены анимированные эмодзи')}:\n\n" + "\n".join(found),
            parse_mode="HTML",
        )
