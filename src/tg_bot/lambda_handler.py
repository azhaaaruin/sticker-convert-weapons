"""AWS Lambda handler for Telegram webhook.

This module builds the telegram Application once (cold start) and exposes
`handler(event, context)` compatible with API Gateway/Lambda Function URL.

Env vars used:
- BOT_TOKEN (required)
- GEMINI_API_KEY (optional)
- TELEGRAM_WEBHOOK_SECRET (optional, if set we verify request header)
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any, Dict

from telegram import Update
from telegram.ext import (
    AIORateLimiter,
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from .config import load_config
from .handlers import (
    cmd_retry,
    cmd_start,
    cmd_status,
    on_document,
    on_lang,
    on_media,
    on_platform,
    on_text,
)


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Build Application once per container
_app: Application | None = None
_app_started: bool = False


def _build_app() -> Application:
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
    return app


async def _ensure_started(app: Application) -> None:
    global _app_started
    if not _app_started:
        await app.initialize()
        await app.start()
        _app_started = True


def _get_header(headers: Dict[str, str], key: str) -> str | None:
    if not headers:
        return None
    # headers may be in various cases; normalize
    for k, v in headers.items():
        if k.lower() == key.lower():
            return v
    return None


def _decode_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        body_bytes = base64.b64decode(body)
        body_str = body_bytes.decode("utf-8")
    else:
        body_str = body or "{}"
    return json.loads(body_str)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    global _app
    if _app is None:
        _app = _build_app()

    method = (
        (event.get("requestContext", {}).get("http", {}).get("method"))
        or event.get("httpMethod")
        or "GET"
    ).upper()
    headers = event.get("headers", {}) or {}

    # Optional secret token validation
    expected_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if expected_secret:
        got = _get_header(headers, "X-Telegram-Bot-Api-Secret-Token")
        if got != expected_secret:
            log.warning("Forbidden: secret token mismatch")
            return {"statusCode": 403, "body": "forbidden"}

    if method == "GET":
        return {"statusCode": 200, "body": "ok"}

    if method != "POST":
        return {"statusCode": 405, "body": "method not allowed"}

    try:
        data = _decode_body(event)
        assert _app is not None
        async def _run():
            await _ensure_started(_app)
            update = Update.de_json(data, _app.bot)
            await _app.process_update(update)

        asyncio.run(_run())
        return {"statusCode": 200, "body": json.dumps({"ok": True})}
    except Exception as e:  # noqa: BLE001
        log.exception("Error processing update: %s", e)
        return {"statusCode": 500, "body": json.dumps({"ok": False})}
