from aiogram import Router, F
from aiogram.types import Message, ContentType
from asgiref.sync import sync_to_async
import random
import re
from core.models import TelegramUser, UserSettings, DailyInspiration
from bot.keyboards import get_main_keyboard, get_location_keyboard
from bot.templates.translations import get_text, t
from bot.utils import get_user_language, detect_timezone_from_location, detect_timezone_from_language_code

router = Router()


@router.message(F.text.in_(["🎲 Випадковий день", "🎲 Случайный день", "🎲 Random Day"]))
async def random_day_handler(message: Message):
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        
        def get_user_settings(tg_user):
            try:
                settings = UserSettings.objects.select_related('selected_book').get(telegram_user=tg_user)
                selected_book = settings.selected_book
                user_language = settings.language
                
                if not selected_book:
                    return None, None, None, "no_book"
                
                inspirations = list(
                    DailyInspiration.objects
                    .select_related('book')
                    .filter(book=selected_book)
                    .only(
                        'html_content',
                        'translation_ukrainian',
                        'translation_russian',
                        'translation_english',
                        'original_text',
                        'date',
                        'book__title',
                        'book__language'
                    )
                )
                
                if not inspirations:
                    return None, None, selected_book.title, "no_inspirations"
                
                return settings, selected_book, inspirations, None
            except UserSettings.DoesNotExist:
                return None, None, None, "no_settings"
        
        settings, selected_book, inspirations, error = await sync_to_async(get_user_settings)(telegram_user)
        language = await get_user_language(message.from_user.id)
        
        if error == "no_settings":
            await message.answer(
                get_text(language, "error_no_settings"),
                reply_markup=get_main_keyboard(language)
            )
            return
        
        if error == "no_book":
            await message.answer(
                get_text(language, "error_no_book"),
                reply_markup=get_main_keyboard(language)
            )
            return
        
        if error == "no_inspirations":
            book_title = selected_book
            await message.answer(
                get_text(language, "error_no_inspirations", book_title=book_title),
                reply_markup=get_main_keyboard(language)
            )
            return
        
        def get_random_inspiration_data(inspirations_list, settings_obj, book_obj):
            random_inspiration = random.choice(inspirations_list)
            
            user_lang = settings_obj.language
            book_lang = book_obj.language
            
            html_content = random_inspiration.html_content
            translation_ukrainian = random_inspiration.translation_ukrainian
            translation_russian = random_inspiration.translation_russian
            translation_english = random_inspiration.translation_english
            original_text = random_inspiration.original_text
            book_title = random_inspiration.book.title
            inspiration_date = random_inspiration.date.strftime('%d.%m.%Y')
            
            if user_lang == 'uk' and translation_ukrainian:
                text = translation_ukrainian
            elif user_lang == 'ru' and translation_russian:
                text = translation_russian
            elif user_lang == 'en' and translation_english:
                text = translation_english
            else:
                text = original_text
            
            return {
                'html_content': html_content,
                'text': text,
                'book_title': book_title,
                'inspiration_date': inspiration_date,
                'book_language': book_lang,
                'user_language': user_lang,
            }
        
        inspiration_data = await sync_to_async(get_random_inspiration_data)(
            inspirations,
            settings,
            selected_book
        )
        
        html_content = inspiration_data['html_content']
        text = inspiration_data['text']
        book_title = inspiration_data['book_title']
        inspiration_date = inspiration_data['inspiration_date']
        book_language = inspiration_data['book_language']
        user_language = inspiration_data['user_language']
        
        use_html = bool(html_content and book_language == user_language)
        
        if use_html:
            from bot.utils import convert_html_to_telegram
            content = await sync_to_async(convert_html_to_telegram)(html_content)
            if not content or not content.strip():
                content = text
        else:
            content = text
        
        language = await get_user_language(message.from_user.id)
        message_text = get_text(
            language,
            "random_day",
            book_title=book_title,
            date=inspiration_date,
            content=content
        )
        
        await message.answer(
            message_text,
            reply_markup=get_main_keyboard(language)
        )
        
    except TelegramUser.DoesNotExist:
        language = await get_user_language(message.from_user.id)
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )
    except Exception as e:
        language = await get_user_language(message.from_user.id)
        await message.answer(
            get_text(language, "error_generic", error=str(e)),
            reply_markup=get_main_keyboard(language)
        )


@router.message(F.content_type == ContentType.LOCATION)
async def location_handler(message: Message):
    language = await get_user_language(message.from_user.id)
    
    try:
        latitude = message.location.latitude
        longitude = message.location.longitude
        
        detected_timezone = detect_timezone_from_location(latitude, longitude)
        timezone_str = detected_timezone.zone if hasattr(detected_timezone, 'zone') else str(detected_timezone)
        
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        from datetime import time
        
        settings, created = await sync_to_async(UserSettings.objects.get_or_create)(
            telegram_user=telegram_user,
            defaults={
                "notification_time": time(8, 0),
                "timezone": detected_timezone,
                "language": language,
            }
        )
        
        settings.timezone = detected_timezone
        await sync_to_async(settings.save)()
        
        await message.answer(
            get_text(language, "location_received", timezone=timezone_str),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )
    except Exception as e:
        await message.answer(
            get_text(language, "error_generic", error=str(e)),
            reply_markup=get_main_keyboard(language)
        )


@router.message(F.text.in_(["⏭️ Пропустити", "⏭️ Пропустить", "⏭️ Skip"]))
async def skip_location_handler(message: Message):
    language = await get_user_language(message.from_user.id)
    
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(telegram_id=message.from_user.id)
        language_code = message.from_user.language_code
        detected_timezone = detect_timezone_from_language_code(language_code)
        from datetime import time
        
        settings, created = await sync_to_async(UserSettings.objects.get_or_create)(
            telegram_user=telegram_user,
            defaults={
                "notification_time": time(8, 0),
                "timezone": detected_timezone,
                "language": language,
            }
        )
        
        if not settings.timezone:
            settings.timezone = detected_timezone
            await sync_to_async(settings.save)()
        
        await message.answer(
            get_text(language, "location_skipped"),
            reply_markup=get_main_keyboard(language)
        )
    except TelegramUser.DoesNotExist:
        await message.answer(
            get_text(language, "error_not_registered"),
            reply_markup=get_main_keyboard(language)
        )
    except Exception as e:
        await message.answer(
            get_text(language, "error_generic", error=str(e)),
            reply_markup=get_main_keyboard(language)
        )


@router.message()
async def echo_handler(message: Message):
    language = await get_user_language(message.from_user.id)
    await message.answer(
        get_text(language, "unknown_command"),
        reply_markup=get_main_keyboard(language)
    )

