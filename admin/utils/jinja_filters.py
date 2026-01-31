"""Custom Jinja2 filters for admin templates."""
import json
from typing import Any
from datetime import datetime, timedelta

from admin.utils.csrf import generate_csrf_token


def from_json(value: str) -> Any:
    """Parse JSON string to Python object.
    
    Args:
        value: JSON string to parse
        
    Returns:
        Parsed Python object (list, dict, etc.) or empty list if failed
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def format_datetime(value) -> str:
    """Format datetime to readable string with +5 hours timezone offset.
    
    Args:
        value: datetime object
        
    Returns:
        Formatted string like "30.01.2026 12:00"
    """
    if not value:
        return "—"
    if isinstance(value, datetime):
        # Add 5 hours for timezone offset
        adjusted = value + timedelta(hours=5)
        return adjusted.strftime('%d.%m.%Y %H:%M')
    return str(value)


def csrf_token_input(request) -> str:
    """Generate hidden input with CSRF token.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        HTML hidden input string
    """
    token = generate_csrf_token(request)
    return f'<input type="hidden" name="csrf_token" value="{token}">'


def setup_jinja_filters(templates):
    """Add custom filters to Jinja2 templates.
    
    Args:
        templates: Jinja2Templates instance
    """
    templates.env.filters['from_json'] = from_json
    templates.env.filters['format_datetime'] = format_datetime
    templates.env.globals['csrf_token_input'] = csrf_token_input
