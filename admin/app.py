from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os

from config import settings
from admin.routes import applications, nominations, content, settings_routes, auth, logs, broadcasts, participants, backups
from admin.utils.auth import get_current_user

# Create FastAPI app
app = FastAPI(
    title="Конкурс - Админ-панель",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=settings.admin_secret_key)

# Mount static files (CSS, JS - public)
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Uploads path (NOT mounted as static - protected by auth)
uploads_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if not os.path.exists(uploads_path):
    os.makedirs(uploads_path)


@app.get("/uploads/{file_path:path}")
async def serve_upload(file_path: str, request: Request):
    """
    Serve uploaded files with authentication.
    Only logged-in admins can access uploaded files.
    """
    # Check authentication
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Sanitize path to prevent directory traversal
    # Remove any .. or absolute path attempts
    safe_path = file_path.replace('..', '').lstrip('/')
    
    # Build full path
    full_path = os.path.join(uploads_path, safe_path)
    
    # Verify the path is within uploads directory
    real_path = os.path.realpath(full_path)
    real_uploads = os.path.realpath(uploads_path)
    if not real_path.startswith(real_uploads):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check file exists
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(full_path)


# Include routers
app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])
app.include_router(participants.router, prefix="/participants", tags=["participants"])
app.include_router(nominations.router, prefix="/nominations", tags=["nominations"])
app.include_router(content.router, prefix="/content", tags=["content"])
app.include_router(broadcasts.router, prefix="/broadcasts", tags=["broadcasts"])
app.include_router(backups.router, prefix="/backups", tags=["backups"])
app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])


@app.get("/")
async def root():
    """Redirect to applications."""
    return RedirectResponse(url="/applications")


def create_admin_app() -> FastAPI:
    """Factory function to create admin app."""
    return app
