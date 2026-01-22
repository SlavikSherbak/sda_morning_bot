from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from asgiref.sync import sync_to_async
from datetime import time
from core.models import TelegramUser, UserSettings
from bot.keyboards import get_main_keyboard, get_languages_keyboard, get_location_keyboard
from bot.templates.translations import get_text
from bot.utils import get_user_language, detect_timezone_from_language_code, detect_timezone_from_location

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language_code = message.from_user.language_code

    telegram_user, created = await sync_to_async(TelegramUser.objects.update_or_create)(
        telegram_id=telegram_id,
        defaults={
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": True,
        },
    )
    
    try:
        settings = await sync_to_async(UserSettings.objects.get)(telegram_user=telegram_user)
        language = settings.language
    except UserSettings.DoesNotExist:
        language = "uk"
        await message.answer(
            get_text(language, "select_language"),
            reply_markup=get_languages_keyboard(language)
        )
        return

    registration_message = get_text(
        language,
        "start_new_user" if created else "start_existing_user"
    )
    
    welcome_text = get_text(
        language,
        "start",
        name=first_name or username or "користувач",
        registration_message=registration_message
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(language)
    )
    await state.clear()


@router.message(Command("help"))
async def cmd_help(message: Message):
    language = await get_user_language(message.from_user.id)
    help_text = get_text(language, "help")
    await message.answer(help_text, reply_markup=get_main_keyboard(language))


@router.message(F.text.in_(["ℹ️ Допомога", "ℹ️ Справка", "ℹ️ Help"]))
async def cmd_help_button(message: Message):
    language = await get_user_language(message.from_user.id)
    help_text = get_text(language, "help")
    await message.answer(help_text, reply_markup=get_main_keyboard(language))


@router.message(Command("status"))
async def cmd_status(message: Message):
    language = await get_user_language(message.from_user.id)
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        
        from core.models import UserSettings
        from bot.templates.translations import t
        try:
            settings = await sync_to_async(UserSettings.objects.get)(telegram_user=telegram_user)
            settings_status = t(language, "settings_created")
        except UserSettings.DoesNotExist:
            settings_status = t(language, "settings_not_created")
        
        status_text = get_text(
            language,
            "profile",
            telegram_id=telegram_user.telegram_id,
            first_name=telegram_user.first_name or t(language, "not_specified"),
            username=telegram_user.username or t(language, "not_specified"),
            status=t(language, "active") if telegram_user.is_active else t(language, "inactive"),
            settings_status=settings_status
        )
        await message.answer(
            status_text.strip(),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )


@router.message(F.text.in_(["👤 Мій профіль", "👤 Мой профиль", "👤 My Profile"]))
async def cmd_profile_button(message: Message):
    language = await get_user_language(message.from_user.id)
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        
        from core.models import UserSettings
        from bot.templates.translations import t
        try:
            settings = await sync_to_async(UserSettings.objects.get)(telegram_user=telegram_user)
            settings_status = t(language, "settings_created")
        except UserSettings.DoesNotExist:
            settings_status = t(language, "settings_not_created")
        
        status_text = get_text(
            language,
            "profile",
            telegram_id=telegram_user.telegram_id,
            first_name=telegram_user.first_name or t(language, "not_specified"),
            username=telegram_user.username or t(language, "not_specified"),
            status=t(language, "active") if telegram_user.is_active else t(language, "inactive"),
            settings_status=settings_status
        )
        await message.answer(
            status_text.strip(),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )


@router.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("_")[1]
    
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=callback.from_user.id)
        language_code = callback.from_user.language_code
        detected_timezone = detect_timezone_from_language_code(language_code)
        
        settings, created = await sync_to_async(UserSettings.objects.get_or_create)(
            telegram_user=telegram_user,
            defaults={
                "notification_time": time(8, 0),
                "timezone": detected_timezone,
                "language": lang_code,
            }
        )
        
        if not created:
            settings.language = lang_code
            if not settings.timezone:
                settings.timezone = detected_timezone
            await sync_to_async(settings.save)()
        
        from core.constants import LANGUAGE_CHOICES
        lang_name = dict(LANGUAGE_CHOICES)[lang_code]
        
        message_text = callback.message.text or ""
        if "Оберіть мову" in message_text or "Выберите язык" in message_text or "Select language" in message_text:
            await callback.message.edit_text(
                get_text(lang_code, "language_selected", 
                        language_name=lang_name,
                        language_name_lower=lang_name.lower())
            )
        else:
            first_name = callback.from_user.first_name or callback.from_user.username or "користувач"
            registration_message = get_text(lang_code, "start_new_user")
            
            welcome_text = get_text(
                lang_code,
                "start",
                name=first_name,
                registration_message=registration_message
            )
            
            await callback.message.edit_text(welcome_text)
            await callback.message.answer(
                get_text(lang_code, "language_selected", 
                        language_name=lang_name,
                        language_name_lower=lang_name.lower()),
                reply_markup=get_main_keyboard(lang_code)
            )
        
        if created:
            timezone_zone = settings.timezone.zone if hasattr(settings.timezone, 'zone') else str(settings.timezone)
            if not timezone_zone or timezone_zone == "Europe/Kyiv":
                await callback.message.answer(
                    get_text(lang_code, "request_location"),
                    reply_markup=get_location_keyboard(lang_code)
                )
        
        await callback.answer()
        await state.clear()
    except TelegramUser.DoesNotExist:
        await callback.answer("❌ Помилка: користувач не знайдений", show_alert=True)

