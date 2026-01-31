"""
CSRF protection utilities.
Generates and validates CSRF tokens stored in session.
"""
import secrets
from fastapi import Request, HTTPException


CSRF_TOKEN_KEY = "_csrf_token"


def generate_csrf_token(request: Request) -> str:
    """
    Generate a CSRF token and store it in the session.
    Returns the token for use in forms.
    """
    if CSRF_TOKEN_KEY not in request.session:
        request.session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return request.session[CSRF_TOKEN_KEY]


def validate_csrf_token(request: Request, token: str) -> bool:
    """
    Validate a CSRF token against the one in session.
    Returns True if valid, False otherwise.
    """
    session_token = request.session.get(CSRF_TOKEN_KEY)
    if not session_token or not token:
        return False
    return secrets.compare_digest(session_token, token)


async def verify_csrf_token(request: Request, csrf_token: str = None):
    """
    Dependency to verify CSRF token from form data.
    Raises HTTPException if invalid.
    """
    # Try to get token from form data
    if csrf_token is None:
        form = await request.form()
        csrf_token = form.get("csrf_token", "")
    
    if not validate_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    
    return True
