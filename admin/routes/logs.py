from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os

from admin.utils.auth import require_auth
from admin.utils.jinja_filters import setup_jinja_filters

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates"))
setup_jinja_filters(templates)

# Path to log file
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "bot.log")


def read_log_lines(file_path: str, lines: int = 200, filter_level: Optional[str] = None) -> list:
    """Read last N lines from log file with optional level filter."""
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # Filter by level if specified
        if filter_level:
            all_lines = [line for line in all_lines if filter_level.upper() in line]
        
        # Get last N lines
        return all_lines[-lines:]
    except Exception as e:
        return [f"Ошибка чтения логов: {str(e)}"]


def parse_log_line(line: str) -> dict:
    """Parse log line into structured data."""
    # Expected format: 2026-01-29 12:34:56,789 - module - LEVEL - message
    try:
        parts = line.split(' - ', 3)
        if len(parts) >= 4:
            return {
                'timestamp': parts[0].strip(),
                'module': parts[1].strip(),
                'level': parts[2].strip(),
                'message': parts[3].strip(),
                'raw': line
            }
    except:
        pass
    
    return {
        'timestamp': '',
        'module': '',
        'level': 'INFO',
        'message': line.strip(),
        'raw': line
    }


@router.get("", response_class=HTMLResponse)
async def view_logs(
    request: Request,
    user: str = Depends(require_auth),
    lines: int = Query(200, ge=50, le=1000),
    level: Optional[str] = Query(None)
):
    """View application logs."""
    log_lines = read_log_lines(LOG_FILE, lines, level)
    
    # Parse lines
    parsed_logs = [parse_log_line(line) for line in log_lines]
    
    # Reverse to show newest first
    parsed_logs.reverse()
    
    # Get log file info
    log_info = {
        'exists': os.path.exists(LOG_FILE),
        'path': LOG_FILE,
        'size': 0
    }
    
    if log_info['exists']:
        log_info['size'] = os.path.getsize(LOG_FILE)
    
    return templates.TemplateResponse("logs/list.html", {
        "request": request,
        "user": user,
        "logs": parsed_logs,
        "log_info": log_info,
        "current_lines": lines,
        "current_level": level
    })
