from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os

from database.database import async_session
from database import crud
from admin.utils.auth import require_auth
from admin.utils.jinja_filters import setup_jinja_filters
from admin.utils.csrf import validate_csrf_token
from admin.utils.export import export_applications_to_xlsx

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


@router.get("", response_class=HTMLResponse)
async def list_applications(
    request: Request,
    user: str = Depends(require_auth),
    nomination_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """List all applications with filters."""
    per_page = 20
    skip = (page - 1) * per_page
    
    # Convert nomination_id to int or None
    nom_id = int(nomination_id) if nomination_id and nomination_id.isdigit() else None
    
    # Parse dates
    date_from_dt = parse_date(date_from)
    date_to_dt = parse_date(date_to)
    # Add end of day for date_to
    if date_to_dt:
        date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)
    
    # Clean search and city
    search_q = search.strip() if search else None
    city_q = city.strip() if city else None
    
    async with async_session() as db:
        applications = await crud.get_all_applications(
            db, 
            skip=skip, 
            limit=per_page,
            nomination_id=nom_id,
            search=search_q,
            city=city_q,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        nominations = await crud.get_all_nominations(db)
        total = await crud.get_applications_count(
            db,
            nomination_id=nom_id,
            search=search_q,
            city=city_q,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
        
        # Get unique cities for filter dropdown (optimized query)
        cities = await crud.get_unique_cities(db)
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse("applications/list.html", {
        "request": request,
        "user": user,
        "applications": applications,
        "nominations": nominations,
        "current_nomination": nom_id,
        "current_search": search_q or "",
        "current_city": city_q or "",
        "current_date_from": date_from or "",
        "current_date_to": date_to or "",
        "cities": cities,
        "page": page,
        "total_pages": total_pages,
        "total": total
    })


@router.get("/{application_id}", response_class=HTMLResponse)
async def view_application(
    request: Request,
    application_id: int,
    user: str = Depends(require_auth)
):
    """View single application details."""
    async with async_session() as db:
        application = await crud.get_application_by_id(db, application_id)
        if not application:
            return RedirectResponse(url="/applications", status_code=302)
    
    return templates.TemplateResponse("applications/detail.html", {
        "request": request,
        "user": user,
        "application": application
    })


@router.post("/{application_id}/delete")
async def delete_application(
    request: Request,
    application_id: int,
    user: str = Depends(require_auth)
):
    """Delete an application."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/applications", status_code=302)
    
    async with async_session() as db:
        await crud.delete_application(db, application_id)
    return RedirectResponse(url="/applications", status_code=302)


@router.get("/export/xlsx")
async def export_applications_xlsx(
    request: Request,
    user: str = Depends(require_auth),
    nomination_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    """Export filtered applications to Excel file."""
    nom_id = int(nomination_id) if nomination_id and nomination_id.isdigit() else None
    
    # Parse dates
    date_from_dt = parse_date(date_from)
    date_to_dt = parse_date(date_to)
    if date_to_dt:
        date_to_dt = date_to_dt.replace(hour=23, minute=59, second=59)
    
    # Clean search and city
    search_q = search.strip() if search else None
    city_q = city.strip() if city else None
    
    async with async_session() as db:
        # Get all applications with filters (no pagination for export)
        applications = await crud.get_all_applications(
            db, 
            skip=0, 
            limit=10000,  # Large limit for export
            nomination_id=nom_id,
            search=search_q,
            city=city_q,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
    
    # Generate Excel file
    excel_buffer = export_applications_to_xlsx(applications)
    
    # Generate filename with date
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"applications_{date_str}.xlsx"
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
