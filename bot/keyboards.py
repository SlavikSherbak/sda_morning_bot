from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.templates.translations import t


def get_location_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=t(language, "share_location"),
                    request_location=True
                )
            ],
            [
                KeyboardButton(text=t(language, "skip")),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard


def get_main_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t(language, "my_settings")),
                KeyboardButton(text=t(language, "my_profile")),
            ],
            [
                KeyboardButton(text=t(language, "set_time")),
                KeyboardButton(text=t(language, "select_book")),
            ],
            [
                KeyboardButton(text=t(language, "select_language")),
                KeyboardButton(
                    text=t(language, "share_location"),
                    request_location=True
                ),
            ],
            [
                KeyboardButton(text=t(language, "help")),
            ],
            [
                KeyboardButton(text=t(language, "random_day")),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=t(language, "select_action"),
    )
    return keyboard


def get_cancel_keyboard(language: str = "uk") -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(language, "cancel"))],
        ],
        resize_keyboard=True,
    )
    return keyboard


async def get_books_keyboard(language: str = "uk", book_language: str = None) -> InlineKeyboardMarkup:
    from asgiref.sync import sync_to_async
    from core.models import Book
    
    books_query = Book.objects.filter(is_active=True)
    if book_language:
        books_query = books_query.filter(language=book_language)
    
    books = await sync_to_async(list)(books_query)
    
    keyboard_buttons = []
    for book in books:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"📖 {book.title}",
                callback_data=f"book_{book.id}"
            )
        ])
    
    keyboard_buttons.append([
        InlineKeyboardButton(text=t(language, "back"), callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def get_languages_keyboard(language: str = "uk") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(language, "ukrainian"), callback_data="lang_uk"),
            ],
            [
                InlineKeyboardButton(text=t(language, "english"), callback_data="lang_en"),
            ],
            [
                InlineKeyboardButton(text=t(language, "russian"), callback_data="lang_ru"),
            ],
            [
                InlineKeyboardButton(text=t(language, "back"), callback_data="back_to_main"),
            ],
        ]
    )
    return keyboard


def get_book_languages_keyboard(language: str = "uk") -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(language, "ukrainian"), callback_data="book_lang_uk"),
            ],
            [
                InlineKeyboardButton(text=t(language, "english"), callback_data="book_lang_en"),
            ],
            [
                InlineKeyboardButton(text=t(language, "russian"), callback_data="book_lang_ru"),
            ],
            [
                InlineKeyboardButton(text=t(language, "back"), callback_data="back_to_main"),
            ],
        ]
    )
    return keyboard

