from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from asgiref.sync import sync_to_async
from datetime import time
from core.models import TelegramUser, UserSettings, Book
from core.constants import LANGUAGE_CHOICES
from bot.keyboards import (
    get_main_keyboard,
    get_cancel_keyboard,
    get_books_keyboard,
    get_languages_keyboard,
    get_book_languages_keyboard,
)
from bot.templates.translations import get_text, t
from bot.utils import get_user_language


router = Router()


class SettingsStates(StatesGroup):
    waiting_for_time = State()
    waiting_for_book_language = State()
    waiting_for_book = State()


@router.message(F.text.in_(["❌ Скасувати", "❌ Отменить", "❌ Cancel"]))
async def cancel_handler(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer(
            get_text(language, "cancel"),
            reply_markup=get_main_keyboard(language)
        )
    else:
        await message.answer(
            get_text(language, "no_active_operation"),
            reply_markup=get_main_keyboard(language)
        )


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    language = await get_user_language(message.from_user.id)
    language_code = message.from_user.language_code
    try:
        def get_settings_data(tg_user, user_language_code):
            from bot.utils import detect_timezone_from_language_code
            
            detected_tz = detect_timezone_from_language_code(user_language_code) if user_language_code else detect_timezone_from_language_code("uk")
            
            settings, created = UserSettings.objects.select_related('selected_book').prefetch_related('selected_books').get_or_create(
                telegram_user=tg_user,
                defaults={
                    "notification_time": time(8, 0),
                    "timezone": detected_tz,
                    "language": language,
                }
            )
            
            if not settings.timezone:
                settings.timezone = detected_tz
                settings.save()
            
            notification_time_str = settings.notification_time.strftime('%H:%M')
            if settings.timezone:
                if hasattr(settings.timezone, 'zone'):
                    timezone_str = settings.timezone.zone
                else:
                    timezone_str = str(settings.timezone)
            else:
                timezone_str = "Europe/Kyiv"
            
            selected_books = list(settings.selected_books.all())
            if selected_books:
                book_titles = "\n".join([f"📖 {book.title}" for book in selected_books])
            elif settings.selected_book:
                book_titles = f"📖 {settings.selected_book.title}"
            else:
                book_titles = t(language, "not_specified")
            
            language_display = dict(LANGUAGE_CHOICES)[settings.language]
            status = t(language, "active") if settings.is_active else t(language, "inactive")
            
            return notification_time_str, timezone_str, book_titles, language_display, status
        
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        notification_time_str, timezone_str, book_title, language_display, status = await sync_to_async(get_settings_data)(telegram_user, language_code)
        
        settings_text = get_text(
            language,
            "settings",
            notification_time=notification_time_str,
            timezone=timezone_str,
            book_title=book_title,
            language_name=language_display,
            status=status
        )
        await message.answer(
            settings_text.strip(),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )


@router.message(F.text.in_(["📋 Мої налаштування", "📋 Мои настройки", "📋 My Settings"]))
async def cmd_settings_button(message: Message):
    language = await get_user_language(message.from_user.id)
    language_code = message.from_user.language_code
    try:
        def get_settings_data(tg_user, user_language_code):
            from bot.utils import detect_timezone_from_language_code
            
            detected_tz = detect_timezone_from_language_code(user_language_code) if user_language_code else detect_timezone_from_language_code("uk")
            
            settings, created = UserSettings.objects.select_related('selected_book').prefetch_related('selected_books').get_or_create(
                telegram_user=tg_user,
                defaults={
                    "notification_time": time(8, 0),
                    "timezone": detected_tz,
                    "language": language,
                }
            )
            
            if not settings.timezone:
                settings.timezone = detected_tz
                settings.save()
            
            notification_time_str = settings.notification_time.strftime('%H:%M')
            if settings.timezone:
                if hasattr(settings.timezone, 'zone'):
                    timezone_str = settings.timezone.zone
                else:
                    timezone_str = str(settings.timezone)
            else:
                timezone_str = "Europe/Kyiv"
            
            # Перевіряємо чи є обрані книги в ManyToMany полі
            selected_books = list(settings.selected_books.all())
            if selected_books:
                book_titles = "\n".join([f"📖 {book.title}" for book in selected_books])
            elif settings.selected_book:
                # Fallback на стару систему
                book_titles = f"📖 {settings.selected_book.title}"
            else:
                book_titles = t(language, "not_specified")
            
            language_display = dict(LANGUAGE_CHOICES)[settings.language]
            status = t(language, "active") if settings.is_active else t(language, "inactive")
            
            return notification_time_str, timezone_str, book_titles, language_display, status
        
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        notification_time_str, timezone_str, book_title, language_display, status = await sync_to_async(get_settings_data)(telegram_user, language_code)
        
        settings_text = get_text(
            language,
            "settings",
            notification_time=notification_time_str,
            timezone=timezone_str,
            book_title=book_title,
            language_name=language_display,
            status=status
        )
        await message.answer(
            settings_text.strip(),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )


@router.message(Command("set_time"))
async def cmd_set_time(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await message.answer(
        get_text(language, "set_time"),
        reply_markup=get_cancel_keyboard(language)
    )
    await state.set_state(SettingsStates.waiting_for_time)


@router.message(F.text.in_(["⏰ Налаштувати час", "⏰ Настроить время", "⏰ Set Time"]))
async def cmd_set_time_button(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await message.answer(
        get_text(language, "set_time"),
        reply_markup=get_cancel_keyboard(language)
    )
    await state.set_state(SettingsStates.waiting_for_time)


@router.message(SettingsStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    cancel_text = t(language, "cancel")
    
    if message.text == cancel_text:
        await state.clear()
        await message.answer(
            get_text(language, "cancel"),
            reply_markup=get_main_keyboard(language)
        )
        return
    
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(":"))
        
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Невірний формат часу")
        
        notification_time = time(hour, minute)
        
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        from bot.utils import detect_timezone_from_language_code
        
        language_code = message.from_user.language_code
        detected_timezone = detect_timezone_from_language_code(language_code)
        
        settings, created = await sync_to_async(UserSettings.objects.get_or_create)(
            telegram_user=telegram_user,
            defaults={
                "notification_time": notification_time,
                "timezone": detected_timezone,
                "language": language,
            }
        )
        
        if not created:
            settings.notification_time = notification_time
            if not settings.timezone:
                settings.timezone = detected_timezone
            await sync_to_async(settings.save)()
        
        await message.answer(
            get_text(language, "time_saved", time=notification_time.strftime('%H:%M')),
            reply_markup=get_main_keyboard(language)
        )
        await state.clear()
    except (ValueError, AttributeError):
        await message.answer(
            get_text(language, "time_invalid"),
            reply_markup=get_cancel_keyboard(language)
        )


@router.message(Command("set_book"))
async def cmd_set_book(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await message.answer(
        get_text(language, "select_book_language"),
        reply_markup=get_book_languages_keyboard(language)
    )
    await state.set_state(SettingsStates.waiting_for_book_language)


@router.message(F.text.in_(["📚 Обрати книгу", "📚 Выбрать книгу", "📚 Select Book"]))
async def cmd_set_book_button(message: Message, state: FSMContext):
    language = await get_user_language(message.from_user.id)
    await message.answer(
        get_text(language, "select_book_language"),
        reply_markup=get_book_languages_keyboard(language)
    )
    await state.set_state(SettingsStates.waiting_for_book_language)


@router.callback_query(F.data.startswith("book_lang_"))
async def process_book_language(callback: CallbackQuery, state: FSMContext):
    book_lang_code = callback.data.split("_")[2]
    language = await get_user_language(callback.from_user.id)
    
    try:
        books_count = await sync_to_async(Book.objects.filter(is_active=True, language=book_lang_code).count)()
        
        if books_count == 0:
            await callback.message.edit_text(
                get_text(language, "no_books")
            )
            await callback.answer()
            await state.clear()
            return
        
        def get_selected_books(tg_id):
            telegram_user = TelegramUser.objects.get(telegram_id=tg_id)
            settings = UserSettings.objects.filter(telegram_user=telegram_user).first()
            if settings:
                return list(settings.selected_books.values_list('id', flat=True))
            return []
        
        selected_book_ids = await sync_to_async(get_selected_books)(callback.from_user.id)
        
        keyboard = await get_books_keyboard(language, book_language=book_lang_code, selected_book_ids=selected_book_ids)
        await callback.message.edit_text(
            get_text(language, "select_book")
        )
        await state.update_data(book_language=book_lang_code, selected_book_ids=selected_book_ids)
        await state.set_state(SettingsStates.waiting_for_book)
        await callback.answer()
    except Exception as e:
        await callback.answer(
            get_text(language, "error_generic", error=str(e)),
            show_alert=True
        )


@router.callback_query(F.data.startswith("book_"))
async def process_book(callback: CallbackQuery, state: FSMContext):
    if callback.data == "books_done":
        return
    
    book_id = int(callback.data.split("_")[1])
    language = await get_user_language(callback.from_user.id)
    
    try:
        state_data = await state.get_data()
        selected_book_ids = state_data.get('selected_book_ids', [])
        book_language = state_data.get('book_language')
        
        if book_id in selected_book_ids:
            selected_book_ids.remove(book_id)
        else:
            selected_book_ids.append(book_id)
        
        await state.update_data(selected_book_ids=selected_book_ids)
        
        keyboard = await get_books_keyboard(language, book_language=book_language, selected_book_ids=selected_book_ids)
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.answer(
            get_text(language, "error_generic", error=str(e)),
            show_alert=True
        )


@router.callback_query(F.data == "books_done")
async def process_books_done(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    
    try:
        state_data = await state.get_data()
        selected_book_ids = state_data.get('selected_book_ids', [])
        
        if not selected_book_ids:
            await callback.answer(
                get_text(language, "no_books_selected"),
                show_alert=True
            )
            return
        
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=callback.from_user.id)
        from bot.utils import detect_timezone_from_language_code
        
        language_code = callback.from_user.language_code
        detected_timezone = detect_timezone_from_language_code(language_code)
        
        settings, created = await sync_to_async(UserSettings.objects.get_or_create)(
            telegram_user=telegram_user,
            defaults={
                "notification_time": time(8, 0),
                "timezone": detected_timezone,
                "language": language,
            }
        )
        
        def update_selected_books(settings_obj, book_ids):
            settings_obj.selected_books.set(book_ids)
            if book_ids:
                first_book = Book.objects.filter(id__in=book_ids).first()
                settings_obj.selected_book = first_book
            if not settings_obj.timezone:
                settings_obj.timezone = detected_timezone
            settings_obj.save()
        
        await sync_to_async(update_selected_books)(settings, selected_book_ids)
        
        def get_book_titles(book_ids):
            books = Book.objects.filter(id__in=book_ids)
            return [book.title for book in books]
        
        book_titles = await sync_to_async(get_book_titles)(selected_book_ids)
        books_list = "\n".join([f"📖 {title}" for title in book_titles])
        
        await callback.message.edit_text(
            get_text(language, "books_selected", books_list=books_list)
        )
        await callback.answer()
        await state.clear()
        
    except TelegramUser.DoesNotExist:
        await callback.answer(
            get_text(language, "error_not_registered"),
            show_alert=True
        )
    except Exception as e:
        await callback.answer(
            get_text(language, "error_generic", error=str(e)),
            show_alert=True
        )


@router.message(Command("set_language"))
async def cmd_set_language(message: Message):
    language = await get_user_language(message.from_user.id)
    keyboard = get_languages_keyboard(language)
    await message.answer(
        get_text(language, "select_language"),
        reply_markup=keyboard
    )


@router.message(F.text.in_(["🌐 Обрати мову", "🌐 Выбрать язык", "🌐 Select Language"]))
async def cmd_set_language_button(message: Message):
    language = await get_user_language(message.from_user.id)
    keyboard = get_languages_keyboard(language)
    await message.answer(
        get_text(language, "select_language"),
        reply_markup=keyboard
    )


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    language = await get_user_language(callback.from_user.id)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        t(language, "main_menu") + "\n\n" + t(language, "select_action"),
        reply_markup=get_main_keyboard(language)
    )
    await callback.answer()
