from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from database.database import async_session
from database import crud
from admin.utils.auth import require_auth
from admin.utils.csrf import validate_csrf_token
from admin.utils.jinja_filters import setup_jinja_filters

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)

# Default content keys with default values
# Format: key -> (title, description, default_value)
DEFAULT_CONTENT = {
    "greeting": (
        "Приветственное сообщение", 
        "Сообщение при /start",
        "Привет! 🙌\n\nМы — всероссийский дизайн-челлендж среди школьников «Точка внимания»."
    ),
    "get_fio": (
        "Запрос ФИО", 
        "Запрос ФИО участника",
        "Напиши, пожалуйста, фамилию, имя и отчество полностью."
    ),
    "get_city": (
        "Запрос города", 
        "Запрос города",
        "Отлично! Теперь укажи, пожалуйста, из какого ты населенного пункта?"
    ),
    "get_school": (
        "Запрос школы", 
        "Запрос организации/школы",
        "Хорошо! Теперь полное название твоей школы (лицея, гимназии и т.д.)."
    ),
    "get_grade": (
        "Запрос класса", 
        "Запрос класса обучения",
        "В каком классе ты учишься?"
    ),
    "get_stage": (
        "Выбор этапа", 
        "Сообщение при выборе этапа",
        "На задание какого этапа ты отправляешь ответ? Выбери: 1, 2 или 3"
    ),
    "get_photos": (
        "Запрос фотографий", 
        "Сообщение перед загрузкой фото",
        "Теперь пришли, пожалуйста, 5 фотографий, которые отражают ход твоих мыслей.\nОтправь фото. После получения 5 фото, перейдем дальше."
    ),
    "get_comment": (
        "Запрос комментария", 
        "Сообщение для добавления комментария",
        "Теперь пришли голосовое или напиши текстовый комментарий к твоему ответу."
    ),
    "finish": (
        "Заявка отправлена", 
        "Текст после успешной отправки заявки",
        "Спасибо! Ваша заявка сформирована и отправлена администраторам.\nМожете воспользоваться /start для новой заявки."
    ),
    "applications_closed": (
        "Приём закрыт", 
        "Текст когда приём заявок закрыт",
        "К сожалению, приём заявок сейчас закрыт."
    ),
    "stage_not_found": (
        "Этап не найден", 
        "Сообщение если этап не найден",
        "ℹ️ Этап не найден"
    ),
    "stage_timeout": (
        "Этап закрыт", 
        "Сообщение если время этапа истекло",
        "ℹ️ Время этапа истекло. Вы не можете его выбрать"
    ),
    "error_not_photo": (
        "Ошибка: не фото", 
        "Если отправили не фото",
        "❗️ Вы попытались отправить не фото. Попробуйте еще раз"
    ),
    "error_photo_count": (
        "Ошибка: много фото", 
        "Если превышен лимит фото",
        "🫠 Необходимо загрузить до {count} фотографий. Но если отправишь и 3 не страшно))"
    ),
    "error_voice_length": (
        "Ошибка: голосовое", 
        "Если голосовое слишком длинное",
        "ℹ️ Ваше голосовое превышает 1 минуту. Отправьте еще раз но в пределах 1 минуты"
    ),
}


@router.get("", response_class=HTMLResponse)
async def list_content(request: Request, user: str = Depends(require_auth)):
    """List all bot content."""
    async with async_session() as db:
        content_list = await crud.get_all_bot_content(db)
        
        # Create dict for easier lookup
        content_dict = {c.key: c.value for c in content_list}
    
    return templates.TemplateResponse("content/list.html", {
        "request": request,
        "user": user,
        "content_dict": content_dict,
        "default_content": DEFAULT_CONTENT
    })


@router.get("/{key}/edit", response_class=HTMLResponse)
async def edit_content_form(
    request: Request,
    key: str,
    user: str = Depends(require_auth)
):
    """Show form to edit content."""
    async with async_session() as db:
        value = await crud.get_bot_content(db, key)
    
    content_info = DEFAULT_CONTENT.get(key, (key, "", ""))
    title = content_info[0]
    description = content_info[1]
    default_value = content_info[2] if len(content_info) > 2 else ""
    
    return templates.TemplateResponse("content/form.html", {
        "request": request,
        "user": user,
        "key": key,
        "value": value or "",
        "default_value": default_value,
        "title": title,
        "description": description
    })


@router.post("/{key}/edit")
async def update_content(
    request: Request,
    key: str,
    value: str = Form(...),
    csrf_token: str = Form(""),
    user: str = Depends(require_auth)
):
    """Update content."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(url="/content", status_code=302)
    
    async with async_session() as db:
        content_info = DEFAULT_CONTENT.get(key, (key, "", ""))
        description = content_info[1]
        await crud.set_bot_content(db, key, value, description)
    
    return RedirectResponse(url="/content", status_code=302)


@router.get("/{key}/reset")
async def reset_content(
    request: Request,
    key: str,
    user: str = Depends(require_auth)
):
    """Reset content to default value."""
    async with async_session() as db:
        await crud.delete_bot_content(db, key)
    
    return RedirectResponse(url="/content", status_code=302)
