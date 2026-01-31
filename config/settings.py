from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List
import os
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Telegram Bot
    bot_token: str = ""
    
    # Admin Panel
    admin_secret_key: str = "change-this-secret-key"
    admin_username: str = "admin"
    # Password hash (use: python -c "from passlib.hash import bcrypt; print(bcrypt.hash('your_password'))")
    admin_password_hash: str = ""
    # Legacy plaintext password (deprecated, use admin_password_hash instead)
    admin_password: str = "admin"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./database/bot.db"
    
    # File upload settings
    uploads_dir: str = "uploads"  # Папка для хранения загруженных файлов
    
    # File upload settings
    max_file_size_mb: int = 20
    allowed_image_extensions: List[str] = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
    allowed_document_extensions: List[str] = [".pdf"]
    allowed_archive_extensions: List[str] = [".zip", ".rar"]
    
    # App settings
    debug: bool = False
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def all_allowed_extensions(self) -> List[str]:
        return (
            self.allowed_image_extensions + 
            self.allowed_document_extensions + 
            self.allowed_archive_extensions
        )
    
    def validate_security(self) -> list[str]:
        """Validate security settings and return warnings."""
        warnings = []
        if self.admin_secret_key == "change-this-secret-key":
            warnings.append("⚠️  SECURITY: admin_secret_key is default! Change it in .env")
        if self.admin_password == "admin":
            warnings.append("⚠️  SECURITY: admin_password is default! Change it in .env")
        return warnings
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env file


settings = Settings()

# Print security warnings on startup
for warning in settings.validate_security():
    logger.warning(warning)
