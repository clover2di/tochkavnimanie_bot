from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import Nomination


def get_main_menu() -> ReplyKeyboardMarkup:
    """Create main menu keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Подать заявку")],
            [KeyboardButton(text="📋 Мои работы"), KeyboardButton(text="ℹ️ Информация")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_cancel_menu() -> ReplyKeyboardMarkup:
    """Create cancel keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Create skip/cancel keyboard."""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_stages_keyboard(stages: List[Nomination], show_change_profile: bool = False) -> InlineKeyboardMarkup:
    """Create stages inline keyboard with stage names."""
    buttons = []
    
    # Sort by order and create buttons with names
    for stage in sorted(stages, key=lambda x: x.order):
        buttons.append([
            InlineKeyboardButton(
                text=stage.name,
                callback_data=f"stage_{stage.id}"
            )
        ])
    
    if show_change_profile:
        buttons.append([
            InlineKeyboardButton(text="✏️ Изменить данные", callback_data="change_profile")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_application")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_nominations_keyboard(nominations: List[Nomination]) -> InlineKeyboardMarkup:
    """Create nominations inline keyboard (alias for stages)."""
    return get_stages_keyboard(nominations)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Create confirmation keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")
            ]
        ]
    )
    return keyboard


def get_application_detail_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Create application detail keyboard."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📎 Открыть файл",
                    callback_data=f"view_file_{application_id}"
                )
            ]
        ]
    )
    return keyboard
