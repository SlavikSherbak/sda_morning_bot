import asyncio
from datetime import datetime, timedelta, time
from celery import shared_task
from django.utils import timezone as django_timezone
from django.conf import settings
import pytz
from asgiref.sync import sync_to_async
from core.models import TelegramUser, UserSettings, DailyInspiration, SentInspiration


def _was_inspiration_sent_today(telegram_user: TelegramUser, inspiration: DailyInspiration, language: str) -> bool:
    if settings.DEBUG:
        return False
    return SentInspiration.objects.filter(
        telegram_user=telegram_user,
        inspiration=inspiration,
        language=language,
    ).exists()


@shared_task
def send_inspirations_to_users():
    server_now = django_timezone.now()
    
    active_settings = UserSettings.objects.filter(
        is_active=True,
        telegram_user__is_active=True,
        selected_book__isnull=False,
    ).select_related("telegram_user", "selected_book")
    
    for settings_obj in active_settings:
        user_tz = settings_obj.timezone
        if not user_tz:
            user_tz = pytz.timezone("Europe/Kyiv")
        elif isinstance(user_tz, str):
            user_tz = pytz.timezone(user_tz)
        
        try:
            user_now = server_now.astimezone(user_tz)
        except (AttributeError, TypeError):
            user_tz = pytz.timezone("Europe/Kyiv")
            user_now = server_now.astimezone(user_tz)
        
        user_current_date = user_now.date()
        user_current_time = user_now.time()
        
        current_minute = user_current_time.minute
        window_start_minute = (current_minute // 5) * 5
        window_start_time = user_current_time.replace(minute=window_start_minute, second=0, microsecond=0)
        window_end_time = user_current_time.replace(second=0, microsecond=0)
        
        notification_time = settings_obj.notification_time
        
        if settings.DEBUG:
            time_in_window = notification_time <= user_current_time
        else:
            time_in_window = (
                window_start_time <= notification_time <= window_end_time
            )
        
        if time_in_window:
            inspiration = DailyInspiration.objects.filter(
                book=settings_obj.selected_book,
                date=user_current_date,
            ).first()
            
            if inspiration:
                if not _was_inspiration_sent_today(
                    settings_obj.telegram_user,
                    inspiration,
                    settings_obj.language
                ):
                    send_inspiration_to_user.delay(
                        settings_obj.telegram_user.telegram_id,
                        inspiration.id,
                        settings_obj.language,
                    )


@shared_task
def send_inspiration_to_user(telegram_id: int, inspiration_id: int, language: str):
    from bot.bot import bot
    from bot.utils import convert_html_to_telegram
    
    async def _send():
        try:
            def get_inspiration_data(insp_id: int, lang: str):
                inspiration = DailyInspiration.objects.select_related('book').get(id=insp_id)
                book = inspiration.book
                
                use_html = bool(inspiration.html_content and book.language == lang)
                
                if use_html:
                    content = convert_html_to_telegram(inspiration.html_content)
                    if not content or not content.strip():
                        content = inspiration.get_text_by_language(lang)
                else:
                    content = inspiration.get_text_by_language(lang)
                
                return content, book.title
            
            content, book_title = await sync_to_async(get_inspiration_data)(inspiration_id, language)
            
            from bot.templates.translations import get_text
            message = get_text(language, "inspiration_message", book_title=book_title, content=content)
            await bot.send_message(chat_id=telegram_id, text=message)
            
            if not settings.DEBUG:
                try:
                    telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)
                    inspiration = DailyInspiration.objects.get(id=inspiration_id)
                    SentInspiration.objects.get_or_create(
                        telegram_user=telegram_user,
                        inspiration=inspiration,
                        language=language,
                    )
                except (TelegramUser.DoesNotExist, DailyInspiration.DoesNotExist):
                    pass
        except Exception:
            pass
    
    asyncio.run(_send())
