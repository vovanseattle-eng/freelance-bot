from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaAnimation
from aiogram.filters import CommandStart, Command

from bot.emoji import E, em, title
from bot.keyboards import main_menu_kb
from database import repository
import config

router = Router()

async def get_main_menu_text() -> str:
    """Единый стильный текст главного экрана с блочным выделением blockquote."""
    total_orders = await repository.count_orders()
    return (
        f"{em(E.FIRE)} <b>FREELANCE RADAR · IT ORDERS</b>\n"
        f"<i>Мониторинг 50+ бирж и каналов в реальном времени</i>\n\n"
        f"<b>Быстрый поиск заказов:</b>\n"
        f"<blockquote>"
        f"Отправьте любое ключевое слово в чат.\n"
        f"Например: <code>Python</code>, <code>Бот</code>, <code>Figma</code>, <code>Reels</code>, <code>Тильда</code>"
        f"</blockquote>\n\n"
        f"<b>Параметры агрегатора:</b>\n"
        f"<blockquote>"
        f"{em(E.STATS)} <b>База:</b> <code>{total_orders} заказов</code>\n"
        f"{em(E.CHECK)} <b>Фильтр:</b> <code>Только IT / Digital</code>\n"
        f"{em(E.PROFILE)} <b>Контакты:</b> <code>Прямой отклик заказчику</code>\n"
        f"{em(E.LIGHTNING)} <b>Мониторинг:</b> <code>24/7 в реальном времени</code>"
        f"</blockquote>"
    )

@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message) -> None:
    user = message.from_user
    if not user:
        return

    await repository.upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    caption = await get_main_menu_text()
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
        caption = await get_main_menu_text()
        cached_id = config.get_cached_file_id("menu")

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
            f"{em(E.STATS)} <b>Статистика базы IT-заказов</b>\n\n"
            f"<blockquote>"
            f"{em(E.TOP)} <b>Всего предложений:</b> <code>{total_orders}</code>\n\n"
            f"{em(E.CODE)} <b>Разработка:</b> <code>{dev_count}</code>\n"
            f"{em(E.DESIGN)} <b>Дизайн:</b> <code>{design_count}</code>\n"
            f"{em(E.SMM)} <b>Маркетинг / SMM:</b> <code>{smm_count}</code>\n"
            f"{em(E.WRITE)} <b>Копирайтинг:</b> <code>{copy_count}</code>\n"
            f"{em(E.MEDIA)} <b>Видеомонтаж:</b> <code>{video_count}</code>"
            f"</blockquote>"
        )
        if not call.message:
            return

        stats_id = config.get_cached_file_id("stats")
        if call.message.animation or call.message.photo or call.message.video:
            if stats_id:
                try:
                    await call.message.edit_media(
                        media=InputMediaAnimation(media=stats_id, caption=text, parse_mode="HTML"),
                        reply_markup=main_menu_kb(),
                    )
                    return
                except Exception:
                    pass
            await call.message.edit_caption(caption=text, reply_markup=main_menu_kb(), parse_mode="HTML")
        else:
            if stats_id:
                try:
                    await call.message.delete()
                except Exception:
                    pass
                await call.message.answer_animation(
                    animation=stats_id,
                    caption=text,
                    reply_markup=main_menu_kb(),
                    parse_mode="HTML",
                )
            else:
                await call.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    finally:
        await call.answer()

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    total_orders = await repository.count_orders()
    dev_count = await repository.count_orders("dev")
    design_count = await repository.count_orders("design")
    smm_count = await repository.count_orders("smm")
    copy_count = await repository.count_orders("copywriting")
    video_count = await repository.count_orders("video")

    text = (
        f"{em(E.STATS)} <b>Статистика базы IT-заказов</b>\n\n"
        f"<blockquote>"
        f"{em(E.TOP)} <b>Всего предложений:</b> <code>{total_orders}</code>\n\n"
        f"{em(E.CODE)} <b>Разработка:</b> <code>{dev_count}</code>\n"
        f"{em(E.DESIGN)} <b>Дизайн:</b> <code>{design_count}</code>\n"
        f"{em(E.SMM)} <b>Маркетинг / SMM:</b> <code>{smm_count}</code>\n"
        f"{em(E.WRITE)} <b>Копирайтинг:</b> <code>{copy_count}</code>\n"
        f"{em(E.MEDIA)} <b>Видеомонтаж:</b> <code>{video_count}</code>"
        f"</blockquote>"
    )
    stats_id = config.get_cached_file_id("stats")
    if stats_id:
        try:
            await message.answer_animation(
                animation=stats_id,
                caption=text,
                reply_markup=main_menu_kb(),
                parse_mode="HTML",
            )
            return
        except Exception:
            pass
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery) -> None:
    from bot.services.subscription import check_user_subscription, clear_user_subscription_cache

    user_id = callback.from_user.id
    clear_user_subscription_cache(user_id)

    if not callback.bot:
        return

    is_sub = await check_user_subscription(callback.bot, user_id)
    if is_sub:
        await callback.answer("Подписка подтверждена!", show_alert=False)
        caption = await get_main_menu_text()
        cached_id = config.get_cached_file_id("menu")
        if callback.message:
            if (callback.message.animation or callback.message.photo or callback.message.video) and cached_id:
                try:
                    await callback.message.edit_media(
                        media=InputMediaAnimation(media=cached_id, caption=caption, parse_mode="HTML"),
                        reply_markup=main_menu_kb(),
                    )
                    return
                except Exception:
                    pass
            try:
                await callback.message.edit_caption(caption=caption, reply_markup=main_menu_kb(), parse_mode="HTML")
                return
            except Exception:
                pass
            try:
                await callback.message.edit_text(text=caption, reply_markup=main_menu_kb(), parse_mode="HTML")
                return
            except Exception:
                pass
    else:
        await callback.answer(
            f"Вы пока не подписались на @{config.CHANNEL_USERNAME}! Пожалуйста, перейдите в канал и нажмите «Подписаться».",
            show_alert=True,
        )


