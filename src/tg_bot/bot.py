#!/usr/bin/env python3
"""App entrypoint wiring handlers and configuration."""
import logging

from telegram.ext import AIORateLimiter, ApplicationBuilder, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from .config import load_config
from .handlers import cmd_start, cmd_retry, cmd_status, on_document, on_lang, on_media, on_platform, on_text


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()

    app = (
        ApplicationBuilder()
        .token(cfg.bot_token)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("retry", cmd_retry))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(on_lang, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_platform, pattern=r"^platform:"))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
