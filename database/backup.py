"""
Database backup utilities.
Provides automatic and manual backup functionality.
"""
import os
import shutil
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Default backup settings
DEFAULT_BACKUP_DIR = "backups"
DEFAULT_MAX_BACKUPS = 10  # Keep last 10 backups
DEFAULT_BACKUP_INTERVAL_HOURS = 24  # Backup every 24 hours


class BackupManager:
    """Manages database backups."""
    
    def __init__(
        self,
        db_path: str = "database/bot.db",
        backup_dir: str = DEFAULT_BACKUP_DIR,
        max_backups: int = DEFAULT_MAX_BACKUPS
    ):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        
        # Ensure backup directory exists
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, suffix: str = "") -> Optional[str]:
        """
        Create a backup of the database.
        
        Args:
            suffix: Optional suffix for the backup filename
            
        Returns:
            Path to the backup file, or None if failed
        """
        if not os.path.exists(self.db_path):
            logger.warning(f"Database file not found: {self.db_path}")
            return None
        
        try:
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix_str = f"_{suffix}" if suffix else ""
            backup_filename = f"bot_db_backup_{timestamp}{suffix_str}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"Backup created: {backup_path}")
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """Remove old backups keeping only max_backups most recent."""
        try:
            backups = []
            for f in os.listdir(self.backup_dir):
                if f.startswith("bot_db_backup_") and f.endswith(".db"):
                    path = os.path.join(self.backup_dir, f)
                    backups.append((path, os.path.getmtime(path)))
            
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old backups
            for path, _ in backups[self.max_backups:]:
                os.remove(path)
                logger.info(f"Removed old backup: {path}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def list_backups(self) -> list:
        """
        List all available backups.
        
        Returns:
            List of dicts with backup info (path, size, date)
        """
        backups = []
        try:
            for f in os.listdir(self.backup_dir):
                if f.startswith("bot_db_backup_") and f.endswith(".db"):
                    path = os.path.join(self.backup_dir, f)
                    stat = os.stat(path)
                    backups.append({
                        'filename': f,
                        'path': path,
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'created': datetime.fromtimestamp(stat.st_mtime)
                    })
            
            # Sort by date (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # Create backup of current state before restore
            self.create_backup(suffix="before_restore")
            
            # Restore backup
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a specific backup file."""
        try:
            if os.path.exists(backup_path) and backup_path.startswith(self.backup_dir):
                os.remove(backup_path)
                logger.info(f"Backup deleted: {backup_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False


# Global backup manager instance
backup_manager = BackupManager()


async def scheduled_backup_task(interval_hours: int = DEFAULT_BACKUP_INTERVAL_HOURS):
    """
    Background task for scheduled backups.
    Run this in your main application loop.
    """
    while True:
        try:
            # Wait for the interval
            await asyncio.sleep(interval_hours * 3600)
            
            # Create backup
            backup_manager.create_backup(suffix="auto")
            
        except asyncio.CancelledError:
            logger.info("Scheduled backup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in scheduled backup: {e}")


def create_manual_backup(suffix: str = "manual") -> Optional[str]:
    """Helper function for manual backups."""
    return backup_manager.create_backup(suffix=suffix)
