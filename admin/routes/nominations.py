from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import Optional
import os

from database.database import async_session
from database import crud
from admin.utils.auth import require_auth
from admin.utils.csrf import validate_csrf_token
from admin.utils.jinja_filters import setup_jinja_filters

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)


@router.get("", response_class=HTMLResponse)
async def list_nominations(request: Request, user: str = Depends(require_auth)):
    """List all nominations."""
    async with async_session() as db:
        nominations = await crud.get_all_nominations(db)
    
    return templates.TemplateResponse("nominations/list.html", {
        "request": request,
        "user": user,
        "nominations": nominations
    })


@router.get("/new", response_class=HTMLResponse)
async def new_nomination_form(request: Request, user: str = Depends(require_auth)):
    """Show form to create new nomination."""
    return templates.TemplateResponse("nominations/form.html", {
        "request": request,
        "user": user,
        "nomination": None
    })


@router.post("/new")
async def create_nomination(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    start_date: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    is_active: bool = Form(True),
    csrf_token: str = Form(""),
    user: str = Depends(require_auth)
):
    """Create new stage."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(url="/nominations", status_code=302)
    
    async with async_session() as db:
        start_date_dt = None
        deadline_dt = None
        
        if start_date:
            try:
                start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
                
        if deadline:
            try:
                deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                pass
        
        await crud.create_nomination(
            db,
            name=name,
            description=description if description else None,
            start_date=start_date_dt,
            deadline=deadline_dt
        )
    
    return RedirectResponse(url="/nominations", status_code=302)


@router.get("/{nomination_id}/edit", response_class=HTMLResponse)
async def edit_nomination_form(
    request: Request,
    nomination_id: int,
    user: str = Depends(require_auth)
):
    """Show form to edit nomination."""
    async with async_session() as db:
        nomination = await crud.get_nomination_by_id(db, nomination_id)
        if not nomination:
            return RedirectResponse(url="/nominations", status_code=302)
    
    return templates.TemplateResponse("nominations/form.html", {
        "request": request,
        "user": user,
        "nomination": nomination
    })


@router.post("/{nomination_id}/edit")
async def update_nomination(
    request: Request,
    nomination_id: int,
    name: str = Form(...),
    description: str = Form(""),
    start_date: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    is_active: bool = Form(False),
    csrf_token: str = Form(""),
    user: str = Depends(require_auth)
):
    """Update stage."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(url="/nominations", status_code=302)
    
    async with async_session() as db:
        start_date_dt = None
        deadline_dt = None
        
        if start_date:
            try:
                start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
                
        if deadline:
            try:
                deadline_dt = datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                pass
        
        await crud.update_nomination(
            db,
            nomination_id,
            name=name,
            description=description if description else None,
            start_date=start_date_dt,
            deadline=deadline_dt,
            is_active=is_active
        )
    
    return RedirectResponse(url="/nominations", status_code=302)


@router.post("/{nomination_id}/delete")
async def delete_nomination(
    request: Request,
    nomination_id: int,
    user: str = Depends(require_auth)
):
    """Delete nomination."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/nominations", status_code=302)
    
    async with async_session() as db:
        await crud.delete_nomination(db, nomination_id)
    
    return RedirectResponse(url="/nominations", status_code=302)
