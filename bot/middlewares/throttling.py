"""
Throttling middleware for protection against spam and DDoS.
Limits message frequency per user.
"""
import time
import logging
from typing import Any, Awaitable, Callable, Dict
from collections import defaultdict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware to limit message rate per user.
    
    Features:
    - Per-user rate limiting
    - Different limits for messages and callbacks
    - Automatic cleanup of old records
    - Warning messages to users who spam
    """
    
    def __init__(
        self, 
        message_limit: float = 0.5,      # Min seconds between messages
        callback_limit: float = 0.3,      # Min seconds between callbacks
        spam_threshold: int = 5,          # Warnings before temporary block
        block_duration: int = 60,         # Block duration in seconds
        cleanup_interval: int = 300       # Cleanup old records every N seconds
    ):
        self.message_limit = message_limit
        self.callback_limit = callback_limit
        self.spam_threshold = spam_threshold
        self.block_duration = block_duration
        self.cleanup_interval = cleanup_interval
        
        # Storage: {user_id: {'last_time': float, 'warnings': int, 'blocked_until': float}}
        self.users: Dict[int, Dict[str, Any]] = defaultdict(
            lambda: {'last_time': 0, 'warnings': 0, 'blocked_until': 0}
        )
        self.last_cleanup = time.time()
    
    def _cleanup_old_records(self):
        """Remove records of users who haven't been active for a while."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = now
        cutoff = now - self.cleanup_interval
        
        # Find users to remove
        to_remove = [
            user_id for user_id, data in self.users.items()
            if data['last_time'] < cutoff and data['blocked_until'] < now
        ]
        
        for user_id in to_remove:
            del self.users[user_id]
        
        if to_remove:
            logger.debug(f"Throttling cleanup: removed {len(to_remove)} old records")
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Determine user ID and rate limit based on event type
        if isinstance(event, Message):
            user = event.from_user
            limit = self.message_limit
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            limit = self.callback_limit
        else:
            # Unknown event type, pass through
            return await handler(event, data)
        
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        now = time.time()
        user_data = self.users[user_id]
        
        # Periodic cleanup
        self._cleanup_old_records()
        
        # Check if user is blocked
        if user_data['blocked_until'] > now:
            remaining = int(user_data['blocked_until'] - now)
            logger.warning(f"Blocked user {user_id} tried to send message. {remaining}s remaining.")
            
            # Silently ignore or send one warning
            if isinstance(event, Message):
                try:
                    await event.answer(
                        f"⚠️ Вы временно заблокированы за спам.\n"
                        f"Попробуйте через {remaining} секунд."
                    )
                except:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer(
                        f"⚠️ Подождите {remaining} сек.",
                        show_alert=True
                    )
                except:
                    pass
            return  # Block the request
        
        # Check rate limit
        time_passed = now - user_data['last_time']
        
        if time_passed < limit:
            # Too fast - increment warnings
            user_data['warnings'] += 1
            user_data['last_time'] = now
            
            logger.info(f"User {user_id} rate limited. Warning {user_data['warnings']}/{self.spam_threshold}")
            
            if user_data['warnings'] >= self.spam_threshold:
                # Block the user
                user_data['blocked_until'] = now + self.block_duration
                user_data['warnings'] = 0
                
                logger.warning(f"User {user_id} blocked for {self.block_duration}s due to spam")
                
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            f"🚫 Вы отправляете сообщения слишком часто!\n"
                            f"Временная блокировка на {self.block_duration} секунд."
                        )
                    except:
                        pass
                elif isinstance(event, CallbackQuery):
                    try:
                        await event.answer(
                            f"🚫 Слишком много запросов! Блокировка на {self.block_duration} сек.",
                            show_alert=True
                        )
                    except:
                        pass
            
            return  # Block the request
        
        # Request is allowed
        user_data['last_time'] = now
        # Gradually decrease warnings if user behaves
        if user_data['warnings'] > 0 and time_passed > limit * 3:
            user_data['warnings'] = max(0, user_data['warnings'] - 1)
        
        return await handler(event, data)


class FileUploadThrottlingMiddleware(BaseMiddleware):
    """
    Additional middleware specifically for file uploads.
    Prevents users from uploading too many files in short time.
    """
    
    def __init__(
        self,
        files_per_minute: int = 10,      # Max files per minute
        total_mb_per_hour: float = 100,   # Max MB per hour per user
    ):
        self.files_per_minute = files_per_minute
        self.total_mb_per_hour = total_mb_per_hour
        
        # Storage: {user_id: {'files': [(timestamp, size_mb), ...], 'last_warning': float}}
        self.users: Dict[int, Dict] = defaultdict(
            lambda: {'files': [], 'last_warning': 0}
        )
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)
        
        # Check if message contains files
        file_size = 0
        if event.photo:
            file_size = event.photo[-1].file_size or 0
        elif event.document:
            file_size = event.document.file_size or 0
        else:
            return await handler(event, data)
        
        user_id = event.from_user.id
        now = time.time()
        user_data = self.users[user_id]
        
        # Clean old records (older than 1 hour)
        user_data['files'] = [
            (ts, size) for ts, size in user_data['files']
            if now - ts < 3600
        ]
        
        # Count files in last minute
        files_last_minute = sum(
            1 for ts, _ in user_data['files']
            if now - ts < 60
        )
        
        # Calculate total MB in last hour
        total_mb = sum(size for _, size in user_data['files'])
        
        file_size_mb = file_size / (1024 * 1024)
        
        # Check limits
        if files_last_minute >= self.files_per_minute:
            if now - user_data['last_warning'] > 30:  # Warn max once per 30s
                user_data['last_warning'] = now
                await event.answer(
                    f"⚠️ Слишком много файлов! Максимум {self.files_per_minute} файлов в минуту.\n"
                    f"Подождите немного."
                )
            logger.warning(f"User {user_id} exceeded file upload rate limit")
            return
        
        if total_mb + file_size_mb > self.total_mb_per_hour:
            if now - user_data['last_warning'] > 30:
                user_data['last_warning'] = now
                await event.answer(
                    f"⚠️ Превышен лимит загрузки: {self.total_mb_per_hour} МБ в час.\n"
                    f"Вы загрузили: {total_mb:.1f} МБ"
                )
            logger.warning(f"User {user_id} exceeded file upload volume limit")
            return
        
        # Record this file
        user_data['files'].append((now, file_size_mb))
        
        return await handler(event, data)
