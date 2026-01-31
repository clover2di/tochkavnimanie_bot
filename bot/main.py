import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from database import init_db

# Import handlers
from bot.handlers import start, application, info, my_works

# Import middlewares
from bot.middlewares.throttling import ThrottlingMiddleware, FileUploadThrottlingMiddleware

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Register middlewares (anti-spam protection)
dp.message.middleware(ThrottlingMiddleware(
    message_limit=0.5,       # Min 0.5 sec between messages
    callback_limit=0.3,      # Min 0.3 sec between callbacks  
    spam_threshold=5,        # 5 warnings before block
    block_duration=60        # Block for 60 seconds
))
dp.callback_query.middleware(ThrottlingMiddleware(
    message_limit=0.5,
    callback_limit=0.3,
    spam_threshold=5,
    block_duration=60
))
dp.message.middleware(FileUploadThrottlingMiddleware(
    files_per_minute=10,     # Max 10 files per minute
    total_mb_per_hour=100    # Max 100 MB per hour
))

# Include routers
dp.include_router(start.router)
dp.include_router(application.router)
dp.include_router(info.router)
dp.include_router(my_works.router)


async def start_bot():
    """Start the bot."""
    logger.info("Initializing database...")
    await init_db()
    
    logger.info("Starting bot...")
    await dp.start_polling(bot)


async def stop_bot():
    """Stop the bot gracefully."""
    logger.info("Stopping bot...")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(start_bot())
