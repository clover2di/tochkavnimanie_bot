from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from database.database import async_session
from database import crud
from bot.keyboards.menus import get_main_menu

router = Router()

# Тексты
GREETING_TEXT = "Привет! 🙌\n\nМы — всероссийский дизайн-челлендж среди школьников «Точка внимания».\n"


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    async with async_session() as db:
        # Get or create user
        user = await crud.get_user_by_telegram_id(db, message.from_user.id)
        if not user:
            user = await crud.create_user(
                db,
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
        
        # Get welcome text from database or use default
        welcome_text = await crud.get_bot_content(db, "welcome_message")
        if not welcome_text:
            welcome_text = GREETING_TEXT
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu()
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Show main menu."""
    await message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@router.message(F.text == "🏠 Главное меню")
async def btn_main_menu(message: Message):
    """Return to main menu via button."""
    await cmd_menu(message)
