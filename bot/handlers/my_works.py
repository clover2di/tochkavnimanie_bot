from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import json
from datetime import timedelta

from database.database import async_session
from database import crud
from bot.keyboards.menus import get_main_menu, get_application_detail_keyboard

router = Router()


@router.message(F.text == "📋 Мои работы")
@router.message(Command("my_works"))
async def show_my_works(message: Message):
    """Show user's applications."""
    async with async_session() as db:
        user = await crud.get_user_by_telegram_id(db, message.from_user.id)
        
        if not user:
            await message.answer(
                "У вас пока нет поданных заявок.",
                reply_markup=get_main_menu()
            )
            return
        
        applications = await crud.get_user_applications(db, user.id)
        
        if not applications:
            await message.answer(
                "У вас пока нет поданных заявок.\nНажмите «📝 Подать заявку» чтобы участвовать!",
                reply_markup=get_main_menu()
            )
            return
        
        text = "📋 <b>Ваши заявки:</b>\n\n"
        
        for i, app in enumerate(applications, 1):
            # Count files
            files_count = 0
            if app.photos:
                try:
                    files_count = len(json.loads(app.photos))
                except:
                    pass
            
            # Comment type
            comment_type = "📝 текст" if app.comment_text else ("🎤 голосовое" if app.voice_file_id else "нет")
            
            # Format date with timezone
            date_str = (app.created_at + timedelta(hours=5)).strftime('%d.%m.%Y %H:%M')
            
            text += (
                f"<b>{i}. {app.nomination.name}</b>\n"
                f"   📎 Файлов: {files_count}\n"
                f"   💬 Комментарий: {comment_type}\n"
                f"   📅 Дата: {date_str}\n"
            )
            
            text += "\n"
    
    await message.answer(text, reply_markup=get_main_menu())
