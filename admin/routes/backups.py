from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os

from admin.utils.auth import require_auth
from admin.utils.csrf import validate_csrf_token
from admin.utils.jinja_filters import setup_jinja_filters
from database.backup import backup_manager, create_manual_backup

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)


@router.get("", response_class=HTMLResponse)
async def list_backups(
    request: Request,
    user: str = Depends(require_auth),
    message: str = Query(None)
):
    """List all backups."""
    backups = backup_manager.list_backups()
    
    return templates.TemplateResponse("backups/list.html", {
        "request": request,
        "user": user,
        "backups": backups,
        "message": message
    })


@router.post("/create")
async def create_backup(
    request: Request,
    user: str = Depends(require_auth)
):
    """Create a new backup."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/backups", status_code=302)
    
    backup_path = create_manual_backup()
    
    if backup_path:
        message = "Бэкап успешно создан!"
    else:
        message = "Ошибка при создании бэкапа"
    
    return RedirectResponse(url=f"/backups?message={message}", status_code=302)


@router.get("/download/{filename}")
async def download_backup(
    request: Request,
    filename: str,
    user: str = Depends(require_auth)
):
    """Download a backup file."""
    # Security: ensure filename is safe
    if ".." in filename or "/" in filename or "\\" in filename:
        return RedirectResponse(url="/backups", status_code=302)
    
    backup_path = os.path.join(backup_manager.backup_dir, filename)
    
    if not os.path.exists(backup_path):
        return RedirectResponse(url="/backups?message=Файл не найден", status_code=302)
    
    return FileResponse(
        backup_path,
        media_type="application/octet-stream",
        filename=filename
    )


@router.post("/delete/{filename}")
async def delete_backup(
    request: Request,
    filename: str,
    user: str = Depends(require_auth)
):
    """Delete a backup file."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/backups", status_code=302)
    
    # Security: ensure filename is safe
    if ".." in filename or "/" in filename or "\\" in filename:
        return RedirectResponse(url="/backups", status_code=302)
    
    backup_path = os.path.join(backup_manager.backup_dir, filename)
    
    if backup_manager.delete_backup(backup_path):
        message = "Бэкап удалён"
    else:
        message = "Ошибка при удалении бэкапа"
    
    return RedirectResponse(url=f"/backups?message={message}", status_code=302)
