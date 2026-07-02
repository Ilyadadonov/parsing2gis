from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils import PRIORITY_CITIES


def cities_keyboard():
    builder = InlineKeyboardBuilder()
    for city in PRIORITY_CITIES:
        builder.add(InlineKeyboardButton(text=city, callback_data=f"city:{city}"))
    builder.adjust(3)
    return builder.as_markup()

def confirm_city_keyboard(city):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Да, начать сбор", callback_data=f"confirm:{city}"))
    builder.add(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()

def existing_city_keyboard(city):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔄 Обновить базу", callback_data=f"update:{city}"))
    builder.add(InlineKeyboardButton(text="📄 Открыть существующую", callback_data=f"open:{city}"))
    return builder.as_markup()
