from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os
import uuid
import asyncio
import logging
import aiofiles

from database.database import async_session
from database import crud
from database.models import BroadcastStatus
from admin.utils.auth import require_auth
from admin.utils.csrf import validate_csrf_token
from admin.utils.jinja_filters import setup_jinja_filters

# Max broadcast image size (5 MB)
MAX_BROADCAST_IMAGE_SIZE = 5 * 1024 * 1024

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
logger = logging.getLogger(__name__)
setup_jinja_filters(templates)

# Directory for broadcast images
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "broadcasts")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("", response_class=HTMLResponse)
async def list_broadcasts(request: Request, user: str = Depends(require_auth)):
    """List all broadcast messages."""
    async with async_session() as db:
        broadcasts = await crud.get_all_broadcasts(db)
    
    return templates.TemplateResponse("broadcasts/list.html", {
        "request": request,
        "user": user,
        "broadcasts": broadcasts
    })


@router.get("/new", response_class=HTMLResponse)
async def new_broadcast_form(request: Request, user: str = Depends(require_auth)):
    """Show form to create new broadcast."""
    return templates.TemplateResponse("broadcasts/form.html", {
        "request": request,
        "user": user,
        "broadcast": None
    })


@router.post("/new")
async def create_broadcast(
    request: Request,
    text: str = Form(...),
    image: Optional[UploadFile] = File(None),
    csrf_token: str = Form(""),
    user: str = Depends(require_auth)
):
    """Create new broadcast message."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(url="/broadcasts", status_code=302)
    
    image_path = None
    
    # Save image if uploaded
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            content = await image.read()
            # Check file size
            if len(content) > MAX_BROADCAST_IMAGE_SIZE:
                async with async_session() as db:
                    nominations = await crud.get_all_nominations(db)
                return templates.TemplateResponse("broadcasts/form.html", {
                    "request": request,
                    "user": user,
                    "error": "Файл слишком большой (макс. 5 МБ)"
                })
            
            filename = f"{uuid.uuid4()}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(content)
            
            image_path = filepath
    
    async with async_session() as db:
        broadcast = await crud.create_broadcast(db, text=text, image_path=image_path)
    
    return RedirectResponse(url="/broadcasts", status_code=302)


@router.get("/{broadcast_id}/edit", response_class=HTMLResponse)
async def edit_broadcast_form(
    request: Request,
    broadcast_id: int,
    user: str = Depends(require_auth)
):
    """Show form to edit broadcast."""
    async with async_session() as db:
        broadcast = await crud.get_broadcast_by_id(db, broadcast_id)
        if not broadcast:
            return RedirectResponse(url="/broadcasts", status_code=302)
    
    return templates.TemplateResponse("broadcasts/form.html", {
        "request": request,
        "user": user,
        "broadcast": broadcast
    })


@router.post("/{broadcast_id}/edit")
async def update_broadcast(
    request: Request,
    broadcast_id: int,
    text: str = Form(...),
    image: Optional[UploadFile] = File(None),
    csrf_token: str = Form(""),
    user: str = Depends(require_auth)
):
    """Update broadcast message."""
    # Verify CSRF token
    if not validate_csrf_token(request, csrf_token):
        return RedirectResponse(url="/broadcasts", status_code=302)
    
    update_data = {"text": text}
    
    # Save new image if uploaded
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            content = await image.read()
            # Check file size
            if len(content) > MAX_BROADCAST_IMAGE_SIZE:
                async with async_session() as db:
                    broadcast = await crud.get_broadcast_by_id(db, broadcast_id)
                return templates.TemplateResponse("broadcasts/form.html", {
                    "request": request,
                    "user": user,
                    "broadcast": broadcast,
                    "error": "Файл слишком большой (макс. 5 МБ)"
                })
            
            filename = f"{uuid.uuid4()}{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(content)
            
            update_data["image_path"] = filepath
    
    async with async_session() as db:
        await crud.update_broadcast(db, broadcast_id, **update_data)
    
    return RedirectResponse(url="/broadcasts", status_code=302)


@router.post("/{broadcast_id}/delete")
async def delete_broadcast(
    request: Request,
    broadcast_id: int,
    user: str = Depends(require_auth)
):
    """Delete broadcast message."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/broadcasts", status_code=302)
    
    async with async_session() as db:
        broadcast = await crud.get_broadcast_by_id(db, broadcast_id)
        if broadcast and broadcast.image_path and os.path.exists(broadcast.image_path):
            try:
                os.remove(broadcast.image_path)
            except OSError as e:
                logger.warning(f"Failed to delete broadcast image: {e}")
        await crud.delete_broadcast(db, broadcast_id)
    
    return RedirectResponse(url="/broadcasts", status_code=302)


async def send_broadcast_task(broadcast_id: int):
    """Background task to send broadcast to all users."""
    from bot.main import bot
    
    # Get broadcast info and user list with short-lived session
    async with async_session() as db:
        broadcast = await crud.get_broadcast_by_id(db, broadcast_id)
        if not broadcast:
            return
        
        # Store needed data before closing session
        broadcast_text = broadcast.text
        broadcast_image_path = broadcast.image_path
        
        # Get all users
        user_ids = await crud.get_all_user_telegram_ids(db)
        total = len(user_ids)
        
        await crud.update_broadcast(
            db, broadcast_id,
            status=BroadcastStatus.SENDING,
            total_count=total
        )
    
    sent = 0
    failed = 0
    
    # Send messages in batches, updating status periodically
    batch_size = 50
    for i, user_id in enumerate(user_ids):
        try:
            if broadcast_image_path and os.path.exists(broadcast_image_path):
                from aiogram.types import FSInputFile
                photo = FSInputFile(broadcast_image_path)
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=broadcast_text,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=user_id,
                    text=broadcast_text,
                    parse_mode="HTML"
                )
            sent += 1
            logger.info(f"Broadcast {broadcast_id}: sent to {user_id}")
        except Exception as e:
            failed += 1
            logger.warning(f"Broadcast {broadcast_id}: failed to send to {user_id}: {e}")
        
        # Small delay to avoid flood limits
        await asyncio.sleep(0.05)
        
        # Update progress every batch
        if (i + 1) % batch_size == 0:
            async with async_session() as db:
                await crud.update_broadcast(
                    db, broadcast_id,
                    sent_count=sent,
                    failed_count=failed
                )
    
    # Update final status with new session
    async with async_session() as db:
        await crud.update_broadcast(
            db, broadcast_id,
            status=BroadcastStatus.SENT,
            sent_count=sent,
            failed_count=failed,
            sent_at=datetime.now()
        )
    
    logger.info(f"Broadcast {broadcast_id} completed: {sent} sent, {failed} failed")


@router.post("/{broadcast_id}/send")
async def send_broadcast(
    request: Request,
    broadcast_id: int,
    background_tasks: BackgroundTasks,
    user: str = Depends(require_auth)
):
    """Start sending broadcast to all users."""
    # Verify CSRF token
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token", "")):
        return RedirectResponse(url="/broadcasts", status_code=302)
    
    async with async_session() as db:
        broadcast = await crud.get_broadcast_by_id(db, broadcast_id)
        if not broadcast or broadcast.status == BroadcastStatus.SENDING:
            return RedirectResponse(url="/broadcasts", status_code=302)
    
    # Start background task
    background_tasks.add_task(send_broadcast_task, broadcast_id)
    
    return RedirectResponse(url="/broadcasts", status_code=302)
