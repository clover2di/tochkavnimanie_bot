from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime
import json

from database.database import async_session
from database import crud
from bot.keyboards.menus import (
    get_main_menu, 
    get_cancel_menu, 
    get_stages_keyboard
)
from bot.utils.local_storage import save_file, create_user_folder
from bot.utils.validation import validate_fio, validate_city, validate_school, validate_grade
from config import settings

router = Router()

# === ТЕКСТЫ БОТА ===
TEXTS = {
    "greeting": "Привет! 🙌\n\nМы — всероссийский дизайн-челлендж среди школьников «Точка внимания».\n",
    "get_fio": "Напиши, пожалуйста, фамилию, имя и отчество полностью.",
    "get_city": "Отлично! Теперь укажи, пожалуйста, из какого ты населенного пункта?",
    "get_school": "Хорошо! Теперь полное название твоей школы (лицея, гимназии и т.д.).",
    "get_grade": "В каком классе ты учишься?",
    "get_stage": "На задание какого этапа ты отправляешь ответ?",
    "get_photos": "Теперь пришли, пожалуйста, до 5 фотографий или PDF-файлов, которые отражают ход твоих мыслей.\n\n📌 Максимальный размер одного файла: {max_size} МБ\n📌 Минимум: 3 файла, максимум: 5 файлов\n\nОтправь фото или документ.",
    "get_comment": "Теперь пришли голосовое или напиши текстовый комментарий к твоему ответу.",
    
    "stage_not_found": "ℹ️ Этап не найден",
    "stage_timeout": "ℹ️ Время этапа истекло. Вы не можете его выбрать",
    
    "error_not_photo": "❗️ Пожалуйста, отправь фотографию или PDF-файл",
    "error_photo_count": "🫠 Максимум {count} файлов. Отправь комментарий.",
    "error_photo_null": "😱 Вы не загрузили файлы",
    "error_voice_length": "ℹ️ Ваше голосовое превышает 1 минуту. Отправь еще раз но в пределах 1 минуты",
    "error_file_too_large": "❗️ Файл слишком большой! Максимальный размер: {max_size} МБ",
    "error_wrong_format": "❗️ Неподдерживаемый формат файла. Отправь фото или PDF.",
    
    "finish": "Спасибо! Твоя заявка сформирована и отправлена администраторам.\nМожете воспользоваться /start для новой заявки.",
    
    "application_notify": "🎯 <b>Новая заявка #{id}</b>\n\nПользователь: {user}\nФИО: <b>{name}</b>\nГород/поселок: <b>{city}</b>\nШкола: <b>{school}</b>\nКласс: <b>{grade}</b>\nЭтап: <b>{stage}</b>\n",
}

# Максимум файлов
MAX_FILES = 5
MIN_FILES = 3
MAX_VOICE_DURATION = 60  # секунд


class ApplicationForm(StatesGroup):
    """States for application submission."""
    entering_fio = State()
    entering_city = State()
    entering_school = State()
    entering_grade = State()
    choosing_stage = State()
    uploading_photos = State()
    entering_comment = State()


@router.message(F.text == "📝 Подать заявку")
async def start_application(message: Message, state: FSMContext):
    """Start the application process."""
    async with async_session() as db:
        # Check if applications are open
        accepting = await crud.get_setting(db, "accepting_applications", "true")
        if accepting.lower() != "true":
            await message.answer("К сожалению, приём заявок сейчас закрыт.")
            return
        
        # Get or create user
        user = await crud.get_or_create_user(db, message.from_user.id, message.from_user.username)
        await state.update_data(user_id=user.id)
        
        # Check if user already has profile data filled
        if user.full_name and user.city and user.school and user.grade:
            # User already has data, skip to stage selection
            await state.update_data(
                full_name=user.full_name,
                city=user.city,
                school=user.school,
                grade=user.grade
            )
            
            stages = await crud.get_available_nominations(db)
            if not stages:
                await message.answer("В данный момент нет доступных этапов для подачи заявки.")
                await state.clear()
                return
            
            await state.set_state(ApplicationForm.choosing_stage)
            await message.answer(
                f"👋 Привет, {user.full_name}!\n\n"
                f"📍 {user.city}, {user.school}, {user.grade} класс\n\n"
                f"{TEXTS['get_stage']}",
                reply_markup=get_stages_keyboard(stages, show_change_profile=True)
            )
            return
    
    # No profile data, ask for it
    await state.set_state(ApplicationForm.entering_fio)
    await message.answer(TEXTS["get_fio"], reply_markup=get_cancel_menu())


@router.message(ApplicationForm.entering_fio)
async def process_fio(message: Message, state: FSMContext):
    """Process FIO input."""
    if message.text == "❌ Отмена":
        await cancel_application(message, state)
        return
    
    # Validate FIO
    is_valid, result, normalized = validate_fio(message.text)
    
    if not is_valid:
        await message.answer(result)
        return
    
    await state.update_data(full_name=normalized)
    await state.set_state(ApplicationForm.entering_city)
    await message.answer(TEXTS["get_city"])


@router.message(ApplicationForm.entering_city)
async def process_city(message: Message, state: FSMContext):
    """Process city input."""
    if message.text == "❌ Отмена":
        await cancel_application(message, state)
        return
    
    # Validate city
    is_valid, result, normalized = validate_city(message.text)
    
    if not is_valid:
        await message.answer(result)
        return
    
    await state.update_data(city=normalized)
    await state.set_state(ApplicationForm.entering_school)
    await message.answer(TEXTS["get_school"])


@router.message(ApplicationForm.entering_school)
async def process_school(message: Message, state: FSMContext):
    """Process school input."""
    if message.text == "❌ Отмена":
        await cancel_application(message, state)
        return
    
    # Validate school
    is_valid, result, normalized = validate_school(message.text)
    
    if not is_valid:
        await message.answer(result)
        return
    
    await state.update_data(school=normalized)
    await state.set_state(ApplicationForm.entering_grade)
    await message.answer(TEXTS["get_grade"])


@router.message(ApplicationForm.entering_grade)
async def process_grade(message: Message, state: FSMContext):
    """Process grade input."""
    if message.text == "❌ Отмена":
        await cancel_application(message, state)
        return
    
    # Validate grade
    is_valid, result, normalized = validate_grade(message.text)
    
    if not is_valid:
        await message.answer(result)
        return
    
    await state.update_data(grade=normalized)
    
    async with async_session() as db:
        stages = await crud.get_available_nominations(db)
    
    if not stages:
        await message.answer("В данный момент нет доступных этапов для подачи заявки.")
        await state.clear()
        return
    
    await state.set_state(ApplicationForm.choosing_stage)
    await message.answer(TEXTS["get_stage"], reply_markup=get_stages_keyboard(stages))


@router.callback_query(ApplicationForm.choosing_stage, F.data.startswith("stage_"))
async def process_stage_choice(callback: CallbackQuery, state: FSMContext):
    """Process stage selection."""
    stage_id = int(callback.data.split("_")[1])
    
    async with async_session() as db:
        stage = await crud.get_nomination_by_id(db, stage_id)
        
        if not stage:
            await callback.answer(TEXTS["stage_not_found"], show_alert=True)
            return
        
        # Check if stage is within time period
        now = datetime.now()
        if stage.start_date and now < stage.start_date:
            await callback.answer("ℹ️ Этот этап ещё не начался", show_alert=True)
            return
            
        if stage.deadline and now > stage.deadline:
            await callback.answer(TEXTS["stage_timeout"], show_alert=True)
            return
        
        await state.update_data(
            stage_id=stage.id, 
            stage_name=stage.name
        )
    
    # Initialize files list
    await state.update_data(files=[], file_ids=[])
    
    await state.set_state(ApplicationForm.uploading_photos)
    await callback.message.edit_text(f"✅ Выбран этап: {stage.name}")
    await callback.message.answer(
        TEXTS["get_photos"].format(max_size=settings.max_file_size_mb), 
        reply_markup=get_cancel_menu()
    )
    await callback.answer()


@router.callback_query(ApplicationForm.choosing_stage, F.data == "cancel_application")
async def cancel_stage_choice(callback: CallbackQuery, state: FSMContext):
    """Cancel stage selection."""
    await state.clear()
    await callback.message.edit_text("❌ Подача заявки отменена.")
    await callback.message.answer("Выберите действие:", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(ApplicationForm.choosing_stage, F.data == "change_profile")
async def change_profile_data(callback: CallbackQuery, state: FSMContext):
    """Allow user to re-enter profile data."""
    await state.set_state(ApplicationForm.entering_fio)
    await callback.message.edit_text("✏️ Давайте обновим ваши данные.")
    await callback.message.answer(TEXTS["get_fio"], reply_markup=get_cancel_menu())
    await callback.answer()


@router.message(ApplicationForm.uploading_photos, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Process photo upload."""
    data = await state.get_data()
    files = data.get('files', [])
    file_ids = data.get('file_ids', [])
    
    if len(files) >= MAX_FILES:
        await message.answer(TEXTS["error_photo_count"].format(count=MAX_FILES))
        return
    
    # Get the largest photo
    photo = message.photo[-1]
    
    # Check file size
    if photo.file_size and photo.file_size > settings.max_file_size_bytes:
        await message.answer(TEXTS["error_file_too_large"].format(max_size=settings.max_file_size_mb))
        return
    
    file_ids.append(photo.file_id)
    files.append({
        'file_id': photo.file_id,
        'file_unique_id': photo.file_unique_id,
        'type': 'photo',
        'extension': '.jpg'
    })
    
    await state.update_data(files=files, file_ids=file_ids)
    await _send_file_status(message, state, files)


@router.message(ApplicationForm.uploading_photos, F.document)
async def process_document(message: Message, state: FSMContext):
    """Process PDF document or image sent as document."""
    data = await state.get_data()
    files = data.get('files', [])
    file_ids = data.get('file_ids', [])
    
    if len(files) >= MAX_FILES:
        await message.answer(TEXTS["error_photo_count"].format(count=MAX_FILES))
        return
    
    document = message.document
    file_name = document.file_name or ""
    file_name_lower = file_name.lower()
    
    # Check if it's PDF or image
    is_pdf = file_name_lower.endswith('.pdf')
    is_image = any(file_name_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'])
    
    if not is_pdf and not is_image:
        await message.answer(TEXTS["error_wrong_format"])
        return
    
    # Check file size
    if document.file_size > settings.max_file_size_bytes:
        await message.answer(TEXTS["error_file_too_large"].format(max_size=settings.max_file_size_mb))
        return
    
    # Determine extension
    if is_pdf:
        ext = '.pdf'
        file_type = 'document'
    else:
        ext = '.' + file_name_lower.rsplit('.', 1)[-1] if '.' in file_name_lower else '.jpg'
        file_type = 'photo'
    
    file_ids.append(document.file_id)
    files.append({
        'file_id': document.file_id,
        'file_unique_id': document.file_unique_id,
        'type': file_type,
        'extension': ext,
        'file_name': file_name
    })
    
    await state.update_data(files=files, file_ids=file_ids)
    await _send_file_status(message, state, files)


async def _send_file_status(message: Message, state: FSMContext, files: list):
    """Send file upload status message."""
    remaining = MAX_FILES - len(files)
    
    if len(files) >= MIN_FILES:
        if remaining > 0:
            await message.answer(
                f"✅ Файл {len(files)}/{MAX_FILES} получен.\n"
                f"Можете отправить ещё {remaining} или напишите/запишите комментарий."
            )
            await state.set_state(ApplicationForm.entering_comment)
            await message.answer(TEXTS["get_comment"])
        else:
            await message.answer(f"✅ Все {MAX_FILES} файлов получены!")
            await state.set_state(ApplicationForm.entering_comment)
            await message.answer(TEXTS["get_comment"])
    else:
        await message.answer(f"✅ Файл {len(files)}/{MAX_FILES} получен. Отправьте ещё минимум {MIN_FILES - len(files)}.")


@router.message(ApplicationForm.uploading_photos, F.text == "❌ Отмена")
async def cancel_photo_upload(message: Message, state: FSMContext):
    """Cancel during photo upload."""
    await cancel_application(message, state)


@router.message(ApplicationForm.uploading_photos)
async def process_invalid_file(message: Message, state: FSMContext):
    """Handle invalid messages during file upload."""
    data = await state.get_data()
    files = data.get('files', [])
    
    # If minimum files collected, allow text/voice as comment
    if len(files) >= MIN_FILES:
        await state.set_state(ApplicationForm.entering_comment)
        # Re-process as comment
        if message.voice:
            await process_voice_comment(message, state)
        elif message.text and message.text != "❌ Отмена":
            await process_text_comment(message, state)
        elif message.text == "❌ Отмена":
            await cancel_application(message, state)
        return
    
    await message.answer(TEXTS["error_not_photo"])


@router.message(ApplicationForm.entering_comment, F.voice)
async def process_voice_comment(message: Message, state: FSMContext):
    """Process voice comment."""
    voice = message.voice
    
    # Check duration (max 1 minute)
    if voice.duration > MAX_VOICE_DURATION:
        await message.answer(TEXTS["error_voice_length"])
        return
    
    await state.update_data(
        voice_file_id=voice.file_id,
        comment_text=None
    )
    
    await finish_application(message, state)


@router.message(ApplicationForm.entering_comment, F.text)
async def process_text_comment(message: Message, state: FSMContext):
    """Process text comment."""
    if message.text == "❌ Отмена":
        await cancel_application(message, state)
        return
    
    await state.update_data(
        comment_text=message.text,
        voice_file_id=None
    )
    
    await finish_application(message, state)


@router.message(ApplicationForm.entering_comment, F.photo)
async def process_extra_photo(message: Message, state: FSMContext):
    """Process additional photos during comment stage."""
    data = await state.get_data()
    files = data.get('files', [])
    file_ids = data.get('file_ids', [])
    
    if len(files) >= MAX_FILES:
        await message.answer(
            f"У вас уже {MAX_FILES} файлов. Теперь отправьте комментарий (текст или голосовое)."
        )
        return
    
    # Accept extra photo
    photo = message.photo[-1]
    file_ids.append(photo.file_id)
    files.append({
        'file_id': photo.file_id,
        'file_unique_id': photo.file_unique_id,
        'type': 'photo',
        'extension': '.jpg'
    })
    
    await state.update_data(files=files, file_ids=file_ids)
    
    remaining = MAX_FILES - len(files)
    if remaining > 0:
        await message.answer(f"✅ Файл {len(files)}/{MAX_FILES}. Можете отправить ещё или напишите комментарий.")
    else:
        await message.answer(f"✅ Все {MAX_FILES} файлов! Теперь отправьте комментарий.")


@router.message(ApplicationForm.entering_comment, F.document)
async def process_extra_document(message: Message, state: FSMContext):
    """Process additional PDF or image during comment stage."""
    data = await state.get_data()
    files = data.get('files', [])
    file_ids = data.get('file_ids', [])
    
    if len(files) >= MAX_FILES:
        await message.answer(
            f"У вас уже {MAX_FILES} файлов. Теперь отправьте комментарий (текст или голосовое)."
        )
        return
    
    document = message.document
    file_name = document.file_name or ""
    file_name_lower = file_name.lower()
    
    # Check if it's PDF or image
    is_pdf = file_name_lower.endswith('.pdf')
    is_image = any(file_name_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'])
    
    if not is_pdf and not is_image:
        await message.answer(TEXTS["error_wrong_format"])
        return
    
    if document.file_size > settings.max_file_size_bytes:
        await message.answer(TEXTS["error_file_too_large"].format(max_size=settings.max_file_size_mb))
        return
    
    # Determine extension
    if is_pdf:
        ext = '.pdf'
        file_type = 'document'
    else:
        ext = '.' + file_name_lower.rsplit('.', 1)[-1] if '.' in file_name_lower else '.jpg'
        file_type = 'photo'
    
    file_ids.append(document.file_id)
    files.append({
        'file_id': document.file_id,
        'file_unique_id': document.file_unique_id,
        'type': file_type,
        'extension': ext,
        'file_name': file_name
    })
    
    await state.update_data(files=files, file_ids=file_ids)
    
    remaining = MAX_FILES - len(files)
    if remaining > 0:
        await message.answer(f"✅ Файл {len(files)}/{MAX_FILES}. Можете отправить ещё или напишите комментарий.")
    else:
        await message.answer(f"✅ Все {MAX_FILES} файлов! Теперь отправьте комментарий.")


async def finish_application(message: Message, state: FSMContext):
    """Finish and save the application."""
    await message.answer("⏳ Сохраняем вашу заявку...")
    
    data = await state.get_data()
    
    async with async_session() as db:
        # Update user profile
        user = await crud.get_user_by_telegram_id(db, message.from_user.id)
        if user:
            await crud.update_user(
                db, user.id,
                full_name=data.get('full_name'),
                city=data.get('city'),
                school=data.get('school'),
                grade=data.get('grade')
            )
        
        # Save files locally (photos and PDFs)
        files_web_paths = []
        try:
            from bot.main import bot
            
            username = message.from_user.username or str(message.from_user.id)
            folder_path = await create_user_folder(username)
            
            for i, file_data in enumerate(data.get('files', []), 1):
                file_info = await bot.get_file(file_data['file_id'])
                file_bytes = await bot.download_file(file_info.file_path)
                
                ext = file_data.get('extension', '.jpg')
                file_name = f"stage{data.get('stage_id')}_file{i}{ext}"
                _, web_url = await save_file(
                    file_bytes.read(),
                    file_name,
                    folder_path
                )
                files_web_paths.append(web_url)
        except Exception as e:
            import logging
            logging.error(f"Failed to save files locally: {e}")
        
        # Save voice locally if exists
        voice_web_path = None
        if data.get('voice_file_id'):
            try:
                file_info = await bot.get_file(data['voice_file_id'])
                file_bytes = await bot.download_file(file_info.file_path)
                
                file_name = f"stage{data.get('stage_id')}_comment.ogg"
                _, voice_web_path = await save_file(
                    file_bytes.read(),
                    file_name,
                    folder_path
                )
            except Exception as e:
                import logging
                logging.error(f"Failed to save voice locally: {e}")
        
        # Create application
        application = await crud.create_application(
            db,
            user_id=user.id,
            nomination_id=data['stage_id'],
            photos=json.dumps([f['file_id'] for f in data.get('files', [])]),
            photos_remote_paths=json.dumps(files_web_paths),
            comment_text=data.get('comment_text'),
            voice_file_id=data.get('voice_file_id'),
            voice_remote_path=voice_web_path
        )
        
        # Format notification for admins
        notification = TEXTS["application_notify"].format(
            id=application.id,
            user=f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id),
            name=data.get('full_name'),
            city=data.get('city'),
            school=data.get('school'),
            grade=data.get('grade'),
            stage=data.get('stage_name')
        )
        
        # TODO: Send notification to admin chat
        import logging
        logging.info(f"New application: {notification}")
    
    await state.clear()
    await message.answer(TEXTS["finish"], reply_markup=get_main_menu())


@router.message(F.text == "❌ Отмена")
async def cancel_application(message: Message, state: FSMContext):
    """Cancel application process."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Подача заявки отменена.", reply_markup=get_main_menu())
    else:
        await message.answer("Выберите действие:", reply_markup=get_main_menu())
