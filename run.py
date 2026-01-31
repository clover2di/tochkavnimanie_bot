"""
Competition Bot - Entry point
Run this file to start both the bot and admin panel.
"""
import asyncio
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging():
    """Configure logging to file and console."""
    # Create logs directory
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, "bot.log")
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler with rotation (5MB, keep 5 files)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('aiogram').setLevel(logging.INFO)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    
    return logging.getLogger('bot')


async def main():
    """Main entry point."""
    # Setup logging first
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Starting Competition Bot")
    logger.info("=" * 50)
    
    import uvicorn
    from bot.main import start_bot, stop_bot, bot, dp
    from admin.app import app
    from database import init_db
    
    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized.")
    
    # Create uvicorn config
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Run bot and admin panel concurrently
    logger.info("Starting services...")
    logger.info("  - Telegram Bot")
    logger.info("  - Admin Panel: http://localhost:8000")
    
    try:
        await asyncio.gather(
            dp.start_polling(bot),
            server.serve()
        )
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down...")
        await stop_bot()


def run_bot_only():
    """Run only the telegram bot."""
    logger = setup_logging()
    logger.info("Starting bot only mode")
    from bot.main import start_bot
    asyncio.run(start_bot())


def run_admin_only():
    """Run only the admin panel."""
    logger = setup_logging()
    logger.info("Starting admin panel only mode")
    import uvicorn
    from database import init_db
    
    async def init_and_run():
        await init_db()
    
    asyncio.run(init_and_run())
    uvicorn.run("admin.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "bot":
            run_bot_only()
        elif sys.argv[1] == "admin":
            run_admin_only()
        else:
            print("Usage: python run.py [bot|admin]")
            print("  bot   - run only Telegram bot")
            print("  admin - run only Admin panel")
            print("  (no args) - run both")
    else:
        asyncio.run(main())
