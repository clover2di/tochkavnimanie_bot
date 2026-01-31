from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from collections import defaultdict
import time
import hmac
import bcrypt
from config import settings


# Rate limiting storage for login attempts
# {ip_address: {'attempts': int, 'last_attempt': float, 'blocked_until': float}}
_login_attempts = defaultdict(lambda: {'attempts': 0, 'last_attempt': 0, 'blocked_until': 0})

# Settings
MAX_LOGIN_ATTEMPTS = 5          # Max attempts before block
LOGIN_BLOCK_DURATION = 300      # Block for 5 minutes (300 seconds)
ATTEMPT_RESET_TIME = 600        # Reset attempts after 10 minutes of no activity


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded IP (behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_login_rate_limit(request: Request) -> tuple[bool, int]:
    """
    Check if login is allowed for this IP.
    Returns (allowed: bool, seconds_remaining: int)
    """
    ip = get_client_ip(request)
    now = time.time()
    data = _login_attempts[ip]
    
    # Check if blocked
    if data['blocked_until'] > now:
        return False, int(data['blocked_until'] - now)
    
    # Reset old attempts
    if now - data['last_attempt'] > ATTEMPT_RESET_TIME:
        data['attempts'] = 0
    
    return True, 0


def record_failed_login(request: Request) -> tuple[bool, int]:
    """
    Record a failed login attempt.
    Returns (blocked: bool, seconds_blocked: int)
    """
    ip = get_client_ip(request)
    now = time.time()
    data = _login_attempts[ip]
    
    data['attempts'] += 1
    data['last_attempt'] = now
    
    if data['attempts'] >= MAX_LOGIN_ATTEMPTS:
        data['blocked_until'] = now + LOGIN_BLOCK_DURATION
        data['attempts'] = 0
        return True, LOGIN_BLOCK_DURATION
    
    remaining_attempts = MAX_LOGIN_ATTEMPTS - data['attempts']
    return False, remaining_attempts


def record_successful_login(request: Request):
    """Clear login attempts on successful login."""
    ip = get_client_ip(request)
    if ip in _login_attempts:
        del _login_attempts[ip]


def verify_login(username: str, password: str) -> bool:
    """Verify admin login credentials using secure comparison."""
    # Check username with constant-time comparison
    if not hmac.compare_digest(username.encode(), settings.admin_username.encode()):
        return False
    
    # If password hash is set, use bcrypt verification
    if settings.admin_password_hash:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                settings.admin_password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    # Fallback to plaintext comparison (deprecated)
    return hmac.compare_digest(password.encode(), settings.admin_password.encode())


def get_current_user(request: Request) -> str | None:
    """Get current logged in user from session."""
    return request.session.get("user")


async def require_auth(request: Request) -> str:
    """Dependency to require authentication."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user
