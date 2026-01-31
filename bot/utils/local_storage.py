"""
Local file storage module.
Handles file uploads and folder management on local filesystem.
"""
import os
import re
import aiofiles
from typing import Tuple
from datetime import datetime

from config import settings


# Base upload directory
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def get_uploads_dir() -> str:
    """Get base uploads directory, create if not exists."""
    if not os.path.exists(UPLOADS_DIR):
        os.makedirs(UPLOADS_DIR)
    return UPLOADS_DIR


def sanitize_folder_name(name: str) -> str:
    """
    Sanitize folder name to prevent path traversal attacks.
    - Removes dangerous characters like ../ and \\
    - Only allows alphanumeric, underscore, hyphen, and @
    - Limits length to 64 characters
    """
    # Remove any path separators and traversal attempts
    name = name.replace('/', '').replace('\\', '').replace('..', '')
    
    # Only allow safe characters: alphanumeric, underscore, hyphen, @
    name = re.sub(r'[^a-zA-Z0-9_\-@]', '_', name)
    
    # Limit length
    name = name[:64]
    
    # Ensure it's not empty
    if not name or name == '@':
        name = 'unknown_user'
    
    return name


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and malicious files.
    """
    # Remove any path separators
    filename = os.path.basename(filename)
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')
    
    # Only allow safe characters in name part
    name, ext = os.path.splitext(filename)
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    
    # Validate extension
    ext = ext.lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.pdf', '.ogg']
    if ext not in allowed_extensions:
        ext = '.bin'
    
    # Limit length
    name = name[:50]
    
    return f"{name}{ext}" if name else f"file{ext}"


async def create_user_folder(username: str) -> str:
    """
    Create a folder for user.
    Returns folder path.
    """
    base_dir = get_uploads_dir()
    
    # Sanitize username to prevent path traversal
    safe_username = sanitize_folder_name(username)
    user_folder = os.path.join(base_dir, f"@{safe_username}")
    
    # Verify the path is still within uploads directory (extra safety)
    real_user_folder = os.path.realpath(user_folder)
    real_base_dir = os.path.realpath(base_dir)
    if not real_user_folder.startswith(real_base_dir):
        raise ValueError("Invalid folder path detected")
    
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    
    return user_folder


async def save_file(
    file_content: bytes,
    file_name: str,
    folder_path: str
) -> Tuple[str, str]:
    """
    Save file to local storage.
    Returns tuple of (file_path, web_url).
    """
    # Sanitize filename
    safe_name = sanitize_filename(file_name)
    name, ext = os.path.splitext(safe_name)
    
    # Add timestamp to filename to avoid duplicates
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{name}_{timestamp}{ext}"
    
    # Full local path
    file_path = os.path.join(folder_path, new_filename)
    
    # Verify the path is within uploads directory
    real_file_path = os.path.realpath(file_path)
    real_uploads = os.path.realpath(UPLOADS_DIR)
    if not real_file_path.startswith(real_uploads):
        raise ValueError("Invalid file path detected")
    
    # Save file asynchronously
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    # Generate relative web URL for serving via admin panel
    # Path relative to uploads folder
    rel_path = os.path.relpath(file_path, UPLOADS_DIR)
    web_url = f"/uploads/{rel_path.replace(os.sep, '/')}"
    
    return file_path, web_url


async def delete_file(file_path: str) -> bool:
    """Delete file from local storage."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False


async def delete_folder(folder_path: str) -> bool:
    """Delete folder and its contents from local storage."""
    import shutil
    try:
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            return True
        return False
    except Exception:
        return False
