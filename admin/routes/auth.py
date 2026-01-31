from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from config import settings
from admin.utils.auth import (
    verify_login, 
    get_current_user,
    check_login_rate_limit,
    record_failed_login,
    record_successful_login
)
from admin.utils.csrf import validate_csrf_token
from admin.utils.jinja_filters import setup_jinja_filters

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page."""
    # Check rate limit
    allowed, seconds = check_login_rate_limit(request)
    if not allowed:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error": f"Слишком много попыток входа. Попробуйте через {seconds} секунд."
            }
        )
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form("")):
    """Process login."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Ошибка безопасности. Попробуйте снова."}
        )
    
    # Check rate limit
    allowed, seconds = check_login_rate_limit(request)
    if not allowed:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error": f"Слишком много попыток входа. Попробуйте через {seconds} секунд."
            }
        )
    
    if verify_login(username, password):
        record_successful_login(request)
        request.session["user"] = username
        return RedirectResponse(url="/applications", status_code=302)
    
    # Record failed attempt
    blocked, info = record_failed_login(request)
    
    if blocked:
        error_msg = f"Слишком много неудачных попыток. Вход заблокирован на {info} секунд."
    else:
        error_msg = f"Неверный логин или пароль. Осталось попыток: {info}"
    
    return templates.TemplateResponse(
        "login.html", 
        {"request": request, "error": error_msg}
    )


@router.get("/logout")
async def logout(request: Request):
    """Process logout."""
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
