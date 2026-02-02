import asyncio
import logging
from datetime import datetime, timedelta, time
from celery import shared_task
from django.utils import timezone as django_timezone
from django.conf import settings
import pytz
from asgiref.sync import sync_to_async
from core.models import TelegramUser, UserSettings, DailyInspiration, SentInspiration

logger = logging.getLogger(__name__)


def _was_inspiration_sent_today(telegram_user: TelegramUser, inspiration: DailyInspiration, language: str) -> bool:
    """Перевіряє чи вже було надіслано натхнення користувачу."""
    if settings.DEBUG:
        logger.debug(
            f"[DEBUG MODE] Пропускаємо перевірку SentInspiration для користувача {telegram_user.telegram_id}"
        )
        return False
    
    was_sent = SentInspiration.objects.filter(
        telegram_user=telegram_user,
        inspiration=inspiration,
        language=language,
    ).exists()
    
    logger.debug(
        f"Перевірка SentInspiration для користувача {telegram_user.telegram_id}: "
        f"натхнення_id={inspiration.id}, мова={language}, вже_надіслано={was_sent}"
    )
    
    return was_sent


@shared_task
def send_inspirations_to_users():
    """
    Основна задача для відправки натхнень користувачам.
    Викликається кожні 5 хвилин через Celery Beat.
    """
    server_now = django_timezone.now()
    logger.info("=" * 80)
    logger.info(f"🚀 ПОЧАТОК виконання задачі send_inspirations_to_users")
    logger.info(f"⏰ Час на сервері: {server_now} (UTC)")
    logger.info(f"🔧 DEBUG режим: {settings.DEBUG}")
    logger.info("=" * 80)
    
    # Логуємо статистику по натхненням в БД
    try:
        from django.db.models import Count
        from core.models import Book
        
        total_inspirations = DailyInspiration.objects.count()
        logger.info(f"📚 Статистика натхнень в БД:")
        logger.info(f"   Всього натхнень: {total_inspirations}")
        
        if total_inspirations > 0:
            # Статистика по книгам
            books_with_inspirations = Book.objects.annotate(
                inspirations_count=Count('daily_inspirations')
            ).filter(inspirations_count__gt=0)
            
            for book in books_with_inspirations:
                logger.info(f"   📖 {book.title}: {book.inspirations_count} натхнень")
            
            # Натхнення на сьогодні
            today_inspirations = DailyInspiration.objects.filter(
                date=server_now.date()
            ).count()
            logger.info(f"   📅 Натхнень на сьогодні ({server_now.date()}): {today_inspirations}")
            
            # Перевіряємо натхнення для найближчих дат
            from datetime import timedelta
            tomorrow = server_now.date() + timedelta(days=1)
            yesterday = server_now.date() - timedelta(days=1)
            
            tomorrow_count = DailyInspiration.objects.filter(date=tomorrow).count()
            yesterday_count = DailyInspiration.objects.filter(date=yesterday).count()
            
            logger.info(f"   📅 Натхнень на вчора ({yesterday}): {yesterday_count}")
            logger.info(f"   📅 Натхнень на завтра ({tomorrow}): {tomorrow_count}")
        else:
            logger.warning("   ⚠️ В БД немає жодного натхнення! Потрібно спарсити книги.")
    except Exception as e:
        logger.error(f"   ❌ Помилка при отриманні статистики натхнень: {e}")
    
    logger.info("-" * 80)
    
    # Отримуємо всіх активних користувачів з налаштуваннями
    from django.db.models import Q, Count
    
    active_settings = UserSettings.objects.filter(
        is_active=True,
        telegram_user__is_active=True,
    ).annotate(
        books_count=Count("selected_books")
    ).filter(
        Q(selected_book__isnull=False) | Q(books_count__gt=0)
    ).select_related("telegram_user", "selected_book").prefetch_related("selected_books")
    
    total_users = active_settings.count()
    logger.info(f"📊 Знайдено активних користувачів з налаштуваннями: {total_users}")
    
    if total_users == 0:
        logger.warning("⚠️ Немає активних користувачів з налаштуваннями!")
        logger.info("=" * 80)
        return
    
    users_processed = 0
    users_in_window = 0
    users_no_inspiration = 0
    users_already_sent = 0
    users_scheduled = 0
    
    for settings_obj in active_settings:
        users_processed += 1
        telegram_user = settings_obj.telegram_user
        telegram_id = telegram_user.telegram_id
        
        logger.info("-" * 80)
        logger.info(f"👤 Обробка користувача #{users_processed}/{total_users}")
        logger.info(f"   Telegram ID: {telegram_id}")
        logger.info(f"   Ім'я: {telegram_user.first_name} {telegram_user.last_name or ''}")
        logger.info(f"   Username: @{telegram_user.username or 'N/A'}")
        
        # Визначаємо часову зону користувача
        user_tz = settings_obj.timezone
        original_tz = user_tz
        
        if not user_tz:
            logger.warning(f"   ⚠️ Часова зона не встановлена, використовуємо Europe/Kyiv за замовчуванням")
            user_tz = pytz.timezone("Europe/Kyiv")
        elif isinstance(user_tz, str):
            logger.debug(f"   Часова зона (рядок): {user_tz}")
            user_tz = pytz.timezone(user_tz)
        
        # Конвертуємо поточний час у часову зону користувача
        try:
            user_now = server_now.astimezone(user_tz)
            logger.info(f"   🌍 Часова зона: {user_tz}")
        except (AttributeError, TypeError) as e:
            logger.error(f"   ❌ Помилка при конвертації часової зони {original_tz}: {e}")
            logger.warning(f"   ⚠️ Використовуємо Europe/Kyiv як fallback")
            user_tz = pytz.timezone("Europe/Kyiv")
            user_now = server_now.astimezone(user_tz)
        
        user_current_date = user_now.date()
        user_current_time = user_now.time()
        
        logger.info(f"   📅 Поточна дата користувача: {user_current_date}")
        logger.info(f"   🕐 Поточний час користувача: {user_current_time.strftime('%H:%M:%S')}")

        window_end_datetime = user_now
        window_start_datetime = window_end_datetime - timedelta(minutes=5)
        
        window_start_time = window_start_datetime.time()
        window_end_time = window_end_datetime.time()
        
        notification_time = settings_obj.notification_time
        logger.info(f"   ⏰ Час нотифікації: {notification_time.strftime('%H:%M:%S')}")
        logger.info(f"   ⏱️ Вікно часу: {window_start_time.strftime('%H:%M:%S')} - {window_end_time.strftime('%H:%M:%S')}")
        
        # Перевіряємо чи час нотифікації потрапляє у вікно
        if settings.DEBUG:
            time_in_window = notification_time <= user_current_time
            logger.info(f"   🔧 DEBUG режим: перевіряємо {notification_time} <= {user_current_time}: {time_in_window}")
        else:
            notification_datetime = window_end_datetime.replace(
                hour=notification_time.hour,
                minute=notification_time.minute,
                second=0,
                microsecond=0
            )

            if notification_datetime > window_end_datetime:
                notification_datetime = notification_datetime - timedelta(days=1)

            time_in_window = window_start_datetime <= notification_datetime <= window_end_datetime
            logger.info(f"   ✅ Час у вікні: {time_in_window}")
        
        if not time_in_window:
            logger.info(f"   ⏭️ Час нотифікації НЕ у вікні, пропускаємо користувача")
            continue
        
        users_in_window += 1
        logger.info(f"   ✅ Час нотифікації У ВІКНІ! Шукаємо натхнення...")
        
        selected_books_list = list(settings_obj.selected_books.all())
        
        if not selected_books_list and settings_obj.selected_book:
            selected_books_list = [settings_obj.selected_book]
            logger.info(f"   📚 Використовується fallback: 1 книга з поля selected_book")
        
        if not selected_books_list:
            users_no_inspiration += 1
            logger.error(f"   ❌ У користувача немає обраних книг!")
            continue
        
        logger.info(f"   📚 Кількість обраних книг: {len(selected_books_list)}")
        
        language = settings_obj.language
        logger.info(f"   🌐 Мова користувача: {language}")
        
        inspirations_to_send = []
        for selected_book in selected_books_list:
            logger.info(f"   📖 Обробка книги: {selected_book.title} (ID: {selected_book.id})")
            logger.info(f"   🔍 Шукаємо натхнення для дати: {user_current_date}")
            
            inspiration = DailyInspiration.objects.filter(
                book=selected_book,
                date=user_current_date,
            ).first()
            
            if not inspiration:
                logger.error(
                    f"   ❌ Натхнення НЕ ЗНАЙДЕНО для книги '{selected_book.title}' "
                    f"на дату {user_current_date}!"
                )
                logger.error(
                    f"   💡 Можливі причини:"
                    f"\n      - Натхнення не було створено для цієї дати"
                    f"\n      - Книга не була спарсена"
                    f"\n      - Помилка при парсингу книги"
                )
                continue
            
            logger.info(f"   ✅ Натхнення знайдено! ID: {inspiration.id}")
            logger.info(f"   📝 Превью: {inspiration.original_text[:100]}...")
            
            was_sent = _was_inspiration_sent_today(
                telegram_user,
                inspiration,
                language
            )
            
            if was_sent:
                logger.warning(
                    f"   ⚠️ Натхнення з книги '{selected_book.title}' вже було надіслано, пропускаємо"
                )
                continue
            
            inspirations_to_send.append(inspiration)
        
        if not inspirations_to_send:
            if len(selected_books_list) > 0:
                users_already_sent += 1
                logger.warning(f"   ⚠️ Всі натхнення вже були надіслані користувачу")
            else:
                users_no_inspiration += 1
            continue
        
        for inspiration in inspirations_to_send:
            users_scheduled += 1
            logger.info(f"   🚀 Планується відправка натхнення з книги '{inspiration.book.title}'!")
            logger.info(f"   📤 Викликаємо задачу send_inspiration_to_user...")
            
            try:
                send_inspiration_to_user.delay(
                    telegram_id,
                    inspiration.id,
                    language,
                )
                logger.info(f"   ✅ Задачу успішно заплановано в чергу Celery")
            except Exception as e:
                logger.error(f"   ❌ Помилка при плануванні задачі: {e}", exc_info=True)
    
    # Підсумок виконання
    logger.info("=" * 80)
    logger.info("📊 ПІДСУМОК виконання задачі send_inspirations_to_users:")
    logger.info(f"   Всього оброблено користувачів: {users_processed}")
    logger.info(f"   Користувачів у часовому вікні: {users_in_window}")
    logger.info(f"   Користувачів без натхнення: {users_no_inspiration}")
    logger.info(f"   Користувачів, яким вже надіслано: {users_already_sent}")
    logger.info(f"   Заплановано відправок: {users_scheduled}")
    logger.info("=" * 80)
    logger.info("✅ ЗАВЕРШЕННЯ виконання задачі send_inspirations_to_users")
    logger.info("=" * 80)


@shared_task
def send_inspiration_to_user(telegram_id: int, inspiration_id: int, language: str):
    """
    Задача для відправки конкретного натхнення конкретному користувачу.
    Викликається з send_inspirations_to_users.
    """
    from bot.bot import bot
    from bot.utils import convert_html_to_telegram
    import logging

    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info(f"📨 ПОЧАТОК відправки натхнення користувачу")
    logger.info(f"   Telegram ID: {telegram_id}")
    logger.info(f"   Натхнення ID: {inspiration_id}")
    logger.info(f"   Мова: {language}")
    logger.info("=" * 60)
    
    async def _send():
        try:
            # Функція для отримання даних натхнення з БД
            def get_inspiration_data(insp_id: int, lang: str):
                logger.info(f"🔍 Отримуємо дані натхнення з БД...")
                
                try:
                    inspiration = DailyInspiration.objects.select_related('book').get(id=insp_id)
                    logger.info(f"   ✅ Натхнення знайдено: {inspiration}")
                except DailyInspiration.DoesNotExist:
                    logger.error(f"   ❌ Натхнення з ID {insp_id} не знайдено в БД!")
                    raise
                
                book = inspiration.book
                logger.info(f"   📖 Книга: {book.title}")
                logger.info(f"   📅 Дата натхнення: {inspiration.date}")
                
                # Спробуємо використати HTML контент якщо він існує
                use_html = bool(inspiration.html_content)
                logger.info(f"   📝 HTML контент присутній: {use_html}")
                
                content = None
                if use_html:
                    logger.info(f"   🔄 Конвертуємо HTML в Telegram формат...")
                    try:
                        content = convert_html_to_telegram(inspiration.html_content)
                        logger.info(f"   ✅ HTML успішно сконвертовано, довжина: {len(content)} символів")
                    except Exception as e:
                        logger.error(f"   ❌ Помилка при конвертації HTML: {e}")
                    
                # Якщо немає HTML контенту або конвертація не вдалась - fallback на текст
                if not content or not content.strip():
                    logger.info(f"   🔄 Fallback: використовуємо текст для мови {lang}...")
                    content = inspiration.get_text_by_language(lang)
                    if content:
                        logger.info(f"   ✅ Текст для мови {lang} знайдено, довжина: {len(content)} символів")
                    else:
                        logger.warning(f"   ⚠️ Текст для мови {lang} відсутній")
                
                # Фінальний fallback на оригінальний текст
                if not content or not content.strip():
                    logger.warning(f"   ⚠️ Fallback: використовуємо оригінальний текст...")
                    content = inspiration.original_text
                    logger.info(f"   ✅ Оригінальний текст, довжина: {len(content)} символів")
                
                return content, book.title
            
            # Отримуємо контент натхнення
            content, book_title = await sync_to_async(get_inspiration_data)(inspiration_id, language)
            
            if not content or not content.strip():
                logger.error(
                    f"❌ КРИТИЧНА ПОМИЛКА: Натхнення {inspiration_id} не має контенту для мови {language}!"
                )
                return

            # Формуємо повідомлення
            logger.info(f"📝 Формуємо повідомлення за шаблоном...")
            from bot.templates.translations import get_text
            message = get_text(language, "inspiration_message", book_title=book_title, content=content)
            logger.info(f"   ✅ Повідомлення сформовано, довжина: {len(message)} символів")
            logger.debug(f"   Превью повідомлення: {message[:200]}...")
            
            message_sent = False
            
            # Спроба відправити повідомлення
            logger.info(f"📤 Відправляємо повідомлення в Telegram...")
            try:
                await bot.send_message(chat_id=telegram_id, text=message)
                message_sent = True
                logger.info(f"   ✅ Повідомлення успішно відправлено!")
            except Exception as e:
                logger.error(f"   ❌ Помилка при відправці: {e}")
                
                # Якщо помилка парсингу HTML - пробуємо очистити повідомлення
                if "can't parse entities" in str(e).lower() or "parse" in str(e).lower():
                    logger.warning(f"   ⚠️ Помилка парсингу HTML, пробуємо очистити повідомлення...")
                    import re
                    clean_message = re.sub('<[^<]+?>', '', message)
                    logger.info(f"   🔄 Очищене повідомлення, довжина: {len(clean_message)} символів")
                    
                    try:
                        await bot.send_message(chat_id=telegram_id, text=clean_message)
                        message_sent = True
                        logger.info(f"   ✅ Очищене повідомлення успішно відправлено!")
                    except Exception as e2:
                        logger.error(f"   ❌ Не вдалось відправити навіть очищене повідомлення: {e2}")
                        logger.error(f"   💡 Можливо користувач заблокував бота або видалив чат")
                        return
                else:
                    logger.error(f"   💡 Можливо користувач заблокував бота або видалив чат")
                    return
            
            # Зберігаємо запис про відправку
            if message_sent:
                logger.info(f"💾 Зберігаємо запис про відправку...")
                
                if not settings.DEBUG:
                    try:
                        # ВСІ Django ORM запити мають бути всередині sync функції
                        def _save_sent_inspiration():
                            telegram_user = TelegramUser.objects.get(telegram_id=telegram_id)
                            inspiration = DailyInspiration.objects.get(id=inspiration_id)
                            
                            sent_inspiration, created = SentInspiration.objects.get_or_create(
                                telegram_user=telegram_user,
                                inspiration=inspiration,
                                language=language,
                            )
                            return sent_inspiration, created
                        
                        sent_inspiration, created = await sync_to_async(_save_sent_inspiration)()
                        
                        if created:
                            logger.info(
                                f"   ✅ Запис SentInspiration створено: "
                                f"user={telegram_id}, inspiration={inspiration_id}, language={language}"
                            )
                        else:
                            logger.warning(
                                f"   ⚠️ Запис SentInspiration вже існував: "
                                f"user={telegram_id}, inspiration={inspiration_id}, language={language}"
                            )
                    except Exception as e:
                        # Перевіряємо тип помилки через рядкове представлення
                        error_str = str(e)
                        if "TelegramUser" in error_str and "DoesNotExist" in error_str:
                            logger.error(f"   ❌ TelegramUser {telegram_id} не знайдено при збереженні SentInspiration!")
                        elif "DailyInspiration" in error_str and "DoesNotExist" in error_str:
                            logger.error(f"   ❌ DailyInspiration {inspiration_id} не знайдено при збереженні SentInspiration!")
                        else:
                            logger.error(
                                f"   ❌ Помилка при збереженні SentInspiration: {e}",
                                exc_info=True
                            )
                else:
                    logger.info(
                        f"   🔧 DEBUG режим: пропускаємо збереження SentInspiration"
                    )
            else:
                logger.error(
                    f"❌ Повідомлення НЕ було відправлено, не зберігаємо запис SentInspiration"
                )
                
            logger.info("=" * 60)
            logger.info(f"✅ ЗАВЕРШЕННЯ відправки натхнення користувачу {telegram_id}")
            logger.info("=" * 60)
                
        except Exception as e:
            logger.error("=" * 60)
            logger.exception(
                f"❌ КРИТИЧНА ПОМИЛКА в send_inspiration_to_user для користувача {telegram_id}: {e}"
            )
            logger.error("=" * 60)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(_send())
    finally:
        pass
