from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os

from database.database import async_session
from database import crud
from admin.utils.auth import require_auth
from admin.utils.jinja_filters import setup_jinja_filters
from admin.utils.export import export_participants_to_xlsx

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)


@router.get("", response_class=HTMLResponse)
async def list_participants(
    request: Request,
    user: str = Depends(require_auth),
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None)
):
    """List all participants with their stats."""
    per_page = 50
    skip = (page - 1) * per_page
    search_q = search.strip() if search else None
    
    try:
        async with async_session() as db:
            # Get participants with stats in a single optimized query
            participants_data = await crud.get_participants_with_stats(
                db, skip=skip, limit=per_page, search=search_q
            )
            total = await crud.get_participants_count(db, search=search_q)
        
        total_pages = max((total + per_page - 1) // per_page, 1)
        
        return templates.TemplateResponse("participants/list.html", {
            "request": request,
            "user": user,
            "participants": participants_data,
            "page": page,
            "total_pages": total_pages,
            "total": total,
            "search": search or ""
        })
    except Exception as e:
        import traceback
        print(f"Error in participants list: {e}")
        print(traceback.format_exc())
        raise


@router.get("/export/xlsx")
async def export_participants_xlsx(
    request: Request,
    user: str = Depends(require_auth)
):
    """Export all participants to Excel file."""
    async with async_session() as db:
        # Get all users with applications
        query = (
            select(User)
            .where(User.id.in_(select(Application.user_id).distinct()))
            .order_by(User.created_at.desc())
        )
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Get stats for each user
        participants_data = []
        for participant in users:
            app_count_query = select(func.count(Application.id)).where(
                Application.user_id == participant.id
            )
            app_count = await db.scalar(app_count_query) or 0
            
            last_app_query = (
                select(Application.created_at)
                .where(Application.user_id == participant.id)
                .order_by(Application.created_at.desc())
                .limit(1)
            )
            last_app_date = await db.scalar(last_app_query)
            
            participants_data.append({
                'user': participant,
                'application_count': app_count,
                'last_application_date': last_app_date
            })
    
    # Generate Excel file
    excel_buffer = export_participants_to_xlsx(participants_data)
    
    # Generate filename with date
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"participants_{date_str}.xlsx"
    
    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
