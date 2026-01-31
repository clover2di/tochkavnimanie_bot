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

# Default settings
DEFAULT_SETTINGS = {
    "accepting_applications": ("Приём заявок", "bool", "true"),
    "max_applications_per_user": ("Макс. заявок от пользователя", "int", "10"),
}


@router.get("", response_class=HTMLResponse)
async def list_settings(request: Request, user: str = Depends(require_auth)):
    """List all settings."""
    async with async_session() as db:
        settings_list = await crud.get_all_settings(db)
        settings_dict = {s.key: s.value for s in settings_list}
    
    return templates.TemplateResponse("settings/list.html", {
        "request": request,
        "user": user,
        "settings_dict": settings_dict,
        "default_settings": DEFAULT_SETTINGS
    })


@router.post("/update")
async def update_settings(request: Request, user: str = Depends(require_auth)):
    """Update settings."""
    form_data = await request.form()
    
    # Verify CSRF token
    if not validate_csrf_token(request, form_data.get("csrf_token", "")):
        return RedirectResponse(url="/settings", status_code=302)
    
    async with async_session() as db:
        for key, (title, value_type, default) in DEFAULT_SETTINGS.items():
            value = form_data.get(key, default)
            
            # Handle checkbox for boolean
            if value_type == "bool":
                value = "true" if form_data.get(key) else "false"
            
            await crud.set_setting(db, key, str(value), value_type, title)
    
    return RedirectResponse(url="/settings", status_code=302)
