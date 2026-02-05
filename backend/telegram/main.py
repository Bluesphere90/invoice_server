"""
Telegram Bot Entry Point

Run with: python -m backend.telegram.main
"""
import asyncio
import signal
import sys

from backend.telegram.bot_service import TelegramBotService
from backend.observability.logger import get_logger, configure_root_logger
from backend.config import settings

# Setup logging
configure_root_logger()
logger = get_logger(__name__)


def main():
    """Entry point for Telegram bot."""
    # Check configuration
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured!")
        sys.exit(1)
    
    if not settings.TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not configured!")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Telegram Bot Starting...")
    logger.info("=" * 60)
    
    bot = TelegramBotService()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received...")
        bot.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(bot.start_polling())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Bot crashed: {e}")
        sys.exit(1)
    
    logger.info("Telegram Bot stopped.")


if __name__ == "__main__":
    main()
