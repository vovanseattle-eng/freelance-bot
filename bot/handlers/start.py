from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaAnimation
from aiogram.filters import CommandStart, Command

from bot.emoji import E, em, title
from bot.keyboards import main_menu_kb
from bot.state import get_stats, format_uptime
from database import repository
import config

router = Router()

async def get_main_menu_text() -> str:
    """Единый стильный текст главного экрана с блочным выделением blockquote."""
    return (
        f"{em(E.FIRE)} <b>FREELANCE RADAR · IT ORDERS</b>\n"
        f"<i>Мгновенные уведомления о свежих IT-заказах и вакансиях</i>\n\n"
        f"<b>Параметры агрегатора:</b>\n"
        f"<blockquote>"
        f"{em(E.LIGHTNING)} <b>Мониторинг:</b> <code>50+ бирж и каналов 24/7</code>\n"
        f"{em(E.CHECK)} <b>Фильтр:</b> <code>Только IT / Digital</code>\n"
        f"{em(E.PROFILE)} <b>Контакты:</b> <code>Прямой отклик заказчику</code>\n"
        f"{em(E.BELL)} <b>Уведомления:</b> <code>Мгновенный пуш в чат</code>"
        f"</blockquote>\n\n"
        f"<i>Нажмите кнопку «Настройка уведомлений» ниже, чтобы выбрать интересующие вас направления.</i>"
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

    from bot.services.subscription import check_user_subscription
    is_sub = await check_user_subscription(message.bot, user.id)
    accepted = await repository.is_terms_accepted(user.id)

    if not is_sub or not accepted:
        from legal_texts import UNIFIED_GATE_SCREEN
        from bot.keyboards import get_unified_gate_kb
        caption = UNIFIED_GATE_SCREEN
        kb = get_unified_gate_kb(config.CHANNEL_URL)
    else:
        caption = await get_main_menu_text()
        kb = main_menu_kb()

    if config.MENU_GIF_PATH.exists():
        cached_id = config.get_cached_file_id("menu")
        media_input = cached_id or FSInputFile(config.MENU_GIF_PATH)
        try:
            sent = await message.answer_animation(
                animation=media_input,
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
            if sent.animation and not cached_id:
                config.save_cached_file_id("menu", sent.animation.file_id)
        except Exception:
            sent = await message.answer_animation(
                animation=FSInputFile(config.MENU_GIF_PATH),
                caption=caption,
                reply_markup=kb,
                parse_mode="HTML",
            )
            if sent.animation:
                config.save_cached_file_id("menu", sent.animation.file_id)
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


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
        text = await build_stats_text()
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


async def build_stats_text() -> str:
    """Живая статистика: аптайм и счётчики заказов в RAM + число пользователей из базы."""
    stats = get_stats()
    pc = stats["per_category"]
    total_users = await repository.count_users()
    notif_users = await repository.count_notif_enabled()
    return (
        f"{em(E.STATS)} <b>Статистика агрегатора</b>\n\n"
        f"<blockquote>"
        f"{em(E.TOP)} <b>Аптайм бота:</b> <code>{format_uptime(stats['uptime_seconds'])}</code>\n\n"
        f"{em(E.FIRE)} <b>Новых заказов за аптайм:</b> <code>{stats['total_seen']}</code>\n\n"
        f"{em(E.CODE)} <b>Разработка:</b> <code>{pc['dev']}</code>\n"
        f"{em(E.DESIGN)} <b>Дизайн:</b> <code>{pc['design']}</code>\n"
        f"{em(E.SMM)} <b>Маркетинг / SMM:</b> <code>{pc['smm']}</code>\n"
        f"{em(E.WRITE)} <b>Копирайтинг:</b> <code>{pc['copywriting']}</code>\n"
        f"{em(E.MEDIA)} <b>Видеомонтаж:</b> <code>{pc['video']}</code>\n\n"
        f"{em(E.PROFILE)} <b>Пользователей:</b> <code>{total_users}</code>\n"
        f"{em(E.BELL)} <b>С уведомлениями:</b> <code>{notif_users}</code>"
        f"</blockquote>\n\n"
        f"<i>Заказы не хранятся в базе — только мгновенные пуши подписчикам.</i>"
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    text = await build_stats_text()

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


@router.callback_query(F.data.in_({"action:accept_gate", "check_subscription"}))
async def cb_accept_gate(callback: CallbackQuery) -> None:
    from bot.services.subscription import check_user_subscription, clear_user_subscription_cache

    user_id = callback.from_user.id
    clear_user_subscription_cache(user_id)

    if not callback.bot:
        return

    is_sub = await check_user_subscription(callback.bot, user_id)
    if is_sub:
        await repository.record_terms_acceptance(user_id)
        await callback.answer("Подписка подтверждена, доступ открыт!", show_alert=False)
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
            f"Для доступа к боту необходимо подписаться на наш канал @{config.CHANNEL_USERNAME}!",
            show_alert=True,
        )


@router.message(Command("terms"))
@router.callback_query(F.data == "legal:terms")
async def show_terms(event: Message | CallbackQuery) -> None:
    from legal_texts import TERMS_TEXT
    from bot.keyboards import get_terms_doc_kb
    if isinstance(event, CallbackQuery):
        if event.message:
            try:
                await event.message.edit_caption(caption=TERMS_TEXT, reply_markup=get_terms_doc_kb(), parse_mode="HTML")
            except Exception:
                await event.message.edit_text(text=TERMS_TEXT, reply_markup=get_terms_doc_kb(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text=TERMS_TEXT, reply_markup=get_terms_doc_kb(), parse_mode="HTML")


@router.callback_query(F.data == "gate:back")
async def cb_gate_back(callback: CallbackQuery) -> None:
    from legal_texts import UNIFIED_GATE_SCREEN
    from bot.keyboards import get_unified_gate_kb
    if callback.message:
        try:
            await callback.message.edit_caption(caption=UNIFIED_GATE_SCREEN, reply_markup=get_unified_gate_kb(config.CHANNEL_URL), parse_mode="HTML")
        except Exception:
            await callback.message.edit_text(text=UNIFIED_GATE_SCREEN, reply_markup=get_unified_gate_kb(config.CHANNEL_URL), parse_mode="HTML")
    await callback.answer()



