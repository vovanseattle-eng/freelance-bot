from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaAnimation
from aiogram.filters import CommandStart

from bot.emoji import E, em, title
from bot.keyboards import main_menu_kb
from database import repository
import config

router = Router()

def get_main_menu_text() -> str:
    """Единый текст главного экрана для /start и кнопки 'Назад'."""
    return (
        f"{title(E.STAR, 'IT Aggregator')}\n\n"
        f"{em(E.FIRE)} Мониторинг 50+ бирж и каналов в реальном времени.\n"
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

    caption = get_main_menu_text()
    if config.MENU_GIF_PATH.exists():
        cached_id = config.get_cached_file_id("menu")
        media_input = cached_id or FSInputFile(config.MENU_GIF_PATH)
        try:
            sent = await message.answer_animation(
                animation=media_input,
                caption=caption,
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            if sent.animation and not cached_id:
                config.save_cached_file_id("menu", sent.animation.file_id)
        except Exception:
            sent = await message.answer_animation(
                animation=FSInputFile(config.MENU_GIF_PATH),
                caption=caption,
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            if sent.animation:
                config.save_cached_file_id("menu", sent.animation.file_id)
    else:
        await message.answer(caption, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery) -> None:
    try:
        if not call.message:
            return
        caption = get_main_menu_text()
        cached_id = config.get_cached_file_id("menu")

        # Если сообщение уже с анимацией/медиа, обновляем подпись или медиа
        if call.message.animation or call.message.photo or call.message.video:
            if config.MENU_GIF_PATH.exists():
                media_input = cached_id or FSInputFile(config.MENU_GIF_PATH)
                media = InputMediaAnimation(
                    media=media_input,
                    caption=caption,
                    parse_mode="HTML",
                )
                try:
                    await call.message.edit_media(media=media, reply_markup=main_menu_kb())
                    return
                except Exception:
                    pass
            await call.message.edit_caption(caption=caption, reply_markup=main_menu_kb(), parse_mode="HTML")
        else:
            # Если предыдущее сообщение было чисто текстовым (например, из ленты), отправляем новое меню с гифкой и удаляем старое
            if config.MENU_GIF_PATH.exists():
                try:
                    await call.message.delete()
                except Exception:
                    pass
                media_input = cached_id or FSInputFile(config.MENU_GIF_PATH)
                sent = await call.message.answer_animation(
                    animation=media_input,
                    caption=caption,
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
                if sent.animation and not cached_id:
                    config.save_cached_file_id("menu", sent.animation.file_id)
            else:
                await call.message.edit_text(caption, reply_markup=main_menu_kb(), parse_mode="HTML")
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
            if call.message.animation or call.message.photo or call.message.video:
                await call.message.edit_caption(caption=text, reply_markup=main_menu_kb(), parse_mode="HTML")
            else:
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
