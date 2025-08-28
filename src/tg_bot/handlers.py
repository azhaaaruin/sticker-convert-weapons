from __future__ import annotations

from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
import asyncio

from .config import Config, load_config
from .i18n import LANGS, t
from .keyboards import lang_keyboard, platform_keyboard
from .models import PLATFORMS, current_running, job_queue, get_session
from .services.ai import detect_emojis
from .services.output import get_output_backend
from .services.conversion import convert_and_collect


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    # Auto-detect preferred language (default to English)
    lc = ""
    if update.effective_user and getattr(update.effective_user, "language_code", None):
        lc = str(update.effective_user.language_code).lower()
    sess.lang = "en" if lc.startswith("en") else ("id" if lc.startswith("id") else "en")
    await update.message.reply_text(t(sess.lang, "welcome"), reply_markup=lang_keyboard(LANGS))


async def on_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_chat:
        return
    await query.answer()
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    data = query.data or ""
    code = data.split(":", 1)[1] if ":" in data else sess.lang
    if code in LANGS:
        sess.lang = code
    await query.edit_message_text(t(sess.lang, "choose_platform"), reply_markup=platform_keyboard(PLATFORMS))


async def on_platform(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not update.effective_chat:
        return
    await query.answer()
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    data = query.data or ""
    platform = data.split(":", 1)[1] if ":" in data else "local"
    sess.platform = platform
    if platform == "local":
        sess.state = "awaiting_file"
        await query.edit_message_text(t(sess.lang, "send_file"))
    else:
        sess.state = "awaiting_url"
        await query.edit_message_text(t(sess.lang, "send_url"))


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.message.text:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    text = update.message.text.strip()
    if sess.state == "awaiting_url" and sess.platform:
        sess.last_url = text
        # For URL, we don't know file count until download; inform user we'll estimate later
        await update.message.reply_text(t(sess.lang, "link_received_estimating"))
        await enqueue_or_run(update, context, url=text)
    else:
        await update.message.reply_text(t(sess.lang, "choose_platform"), reply_markup=platform_keyboard(PLATFORMS))


async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat or not update.message.document:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    if sess.state != "awaiting_file":
        await update.message.reply_text(t(sess.lang, "choose_platform"), reply_markup=platform_keyboard(PLATFORMS))
        return
    await update.message.chat.send_action(ChatAction.UPLOAD_DOCUMENT)
    dst = Path(sess.input_dir, update.message.document.file_name or "upload.bin")
    file = await update.message.document.get_file()
    await file.download_to_drive(custom_path=dst.as_posix())
    # Pre-conversion estimation for uploads: count current input_dir files (excluding txt/m4a)
    inputs = [p for p in sorted(sess.input_dir.iterdir()) if p.is_file() and p.suffix.lower() not in (".txt", ".m4a")]
    cfg: Config = load_config()
    n = len(inputs)
    if n > 0:
        eta = n * (cfg.est_seconds_convert_per_file + cfg.est_seconds_ai_per_file)
        await update.message.reply_text(t(sess.lang, "detected_files", n=n, eta=eta))
    await enqueue_or_run(update, context)


async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    if sess.state != "awaiting_file":
        await update.message.reply_text(t(sess.lang, "choose_platform"), reply_markup=platform_keyboard(PLATFORMS))
        return
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        dst = Path(sess.input_dir, f"photo_{photo.file_unique_id}.jpg")
    else:
        video = update.message.video
        if not video:
            return
        file = await video.get_file()
        dst = Path(sess.input_dir, f"video_{video.file_unique_id}.mp4")
    await file.download_to_drive(custom_path=dst.as_posix())
    # Pre-conversion estimation similar to documents
    inputs = [p for p in sorted(sess.input_dir.iterdir()) if p.is_file() and p.suffix.lower() not in (".txt", ".m4a")]
    cfg: Config = load_config()
    n = len(inputs)
    if n > 0:
        eta = n * (cfg.est_seconds_convert_per_file + cfg.est_seconds_ai_per_file)
        await update.message.reply_text(t(sess.lang, "detected_files", n=n, eta=eta))
    await enqueue_or_run(update, context)


async def cmd_retry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    # If there are specific failed files retained, prioritize them
    if sess.failed_files:
        for name in list(sess.failed_files):
            src = Path(sess.output_dir, name)
            if src.exists():
                src.replace(Path(sess.input_dir, name))
        await enqueue_or_run(update, context, url=sess.last_url)
        return
    # Else if user provided a URL previously, re-run with last_url
    if sess.last_url:
        await enqueue_or_run(update, context, url=sess.last_url)
        return
    await update.message.reply_text(t(sess.lang, "no_failed"))


async def run_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE, url: Optional[str] = None) -> None:
    assert update.message and update.effective_chat
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)

    # 1) Convert (single job execution)
    # Inform user about estimated duration based on planned count if possible
    cfg: Config = load_config()
    # Pre-announce estimated time: if URL or upload, we can only estimate after we know file count.
    # First run conversion to populate output, conversion itself controls the pipeline.
    files = await convert_and_collect(update.message, sess, url)
    if not files:
        await update.message.reply_text(t(sess.lang, "error", msg="no result"))
        return

    # 2) AI detection
    # Dynamic ETA message
    total_files = len(files)
    est_seconds = total_files * (cfg.est_seconds_ai_per_file)
    eta_msg = (f"⏱️ ETA ~{est_seconds}s" if sess.lang == "en" else f"⏱️ Estimasi ~{est_seconds}dtk")
    status = await update.message.reply_text(t(sess.lang, "analyzing", done=0, total=total_files) + f"\n{eta_msg}")
    def _progress(d: int, tot: int) -> None:
        async def _runner() -> None:
            try:
                await status.edit_text(t(sess.lang, "analyzing", done=d, total=tot))
            except Exception:
                pass
        asyncio.get_event_loop().create_task(_runner())
    emoji_map = await detect_emojis(files, cfg.gemini_api_key, progress=_progress)

    # Write emoji.txt and send results
    lines = [f"{p.name}: {emoji_map.get(p.stem, '😀')}" for p in files]
    Path(sess.output_dir, "emoji.txt").write_text("\n".join(lines), encoding="utf-8")

    # Output via backend abstraction (telegram for now)
    captions = {p.stem: emoji_map.get(p.stem, "😀") for p in files}
    backend = get_output_backend("telegram", bot=context.bot)
    fails = await backend.send(chat_id=chat_id, files=files, captions=captions)

    sess.failed_files = fails
    # Inform retention policy and retry hint
    retention_note = "\n" + ("📦 Files are retained for 24h for secure retry and auditing." if sess.lang == "en" else "\n📦 File disimpan 24 jam untuk kebutuhan retry dan keamanan.")
    if fails:
        await update.message.reply_text(
            t(sess.lang, "partial_success", fails=", ".join(fails)) + "\n" + t(sess.lang, "retry_prompt") + retention_note
        )
    else:
        await update.message.reply_text(t(sess.lang, "done") + retention_note)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    cfg: Config = load_config()
    sys_status = "OK"
    ai_status = "ON" if cfg.gemini_api_key else "OFF"
    from .models import current_running, job_queue
    await update.message.reply_text(
        t(
            sess.lang,
            "status",
            sys=sys_status,
            ai=ai_status,
            load=current_running,
            cap=cfg.max_concurrent_jobs,
            qsize=len(job_queue),
        )
    )


async def enqueue_or_run(update: Update, context: ContextTypes.DEFAULT_TYPE, url: Optional[str] = None) -> None:
    assert update.message and update.effective_chat
    chat_id = int(update.effective_chat.id)
    sess = get_session(chat_id)
    cfg: Config = load_config()

    # Anti-spam cooldown
    import time
    now = time.time()
    if now - sess.last_used_ts < cfg.per_user_cooldown_s:
        remain = int(cfg.per_user_cooldown_s - (now - sess.last_used_ts))
        await update.message.reply_text(t(sess.lang, "cooldown", sec=remain))
        return

    # Limit pending per user
    if sum(1 for uid, _ in job_queue if uid == chat_id) >= cfg.per_user_max_pending:
        await update.message.reply_text(t(sess.lang, "queue_full"))
        return

    # Decide run or queue
    global current_running
    if current_running < cfg.max_concurrent_jobs:
        current_running += 1
        try:
            await run_pipeline(update, context, url)
        finally:
            current_running -= 1
            # Drain queue if any
            await drain_queue(context)
    else:
        # Enqueue if space
        if len(job_queue) >= cfg.queue_limit:
            await update.message.reply_text(t(sess.lang, "queue_full"))
            return
        job_queue.append((chat_id, url))
        pos = sum(1 for _ in job_queue)
        eta = pos * cfg.est_seconds_per_job
        await update.message.reply_text(t(sess.lang, "queued", pos=pos, total=pos, eta=eta))


async def drain_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    # Try to start next jobs up to capacity
    cfg: Config = load_config()
    global current_running
    while job_queue and current_running < cfg.max_concurrent_jobs:
        chat_id, url = job_queue.popleft()
        sess = get_session(chat_id)
        # Create a fake Update using Bot API to message user
        try:
            current_running += 1
            # Use application.bot to send a dummy message and wrap into Update-like
            bot = context.bot
            msg = await bot.send_message(chat_id=chat_id, text=t(sess.lang, "processing"))
            # Build a minimal Update-like object with this message for run_pipeline
            from telegram import Update as TgUpdate
            upd = TgUpdate(update_id=0, message=msg)
            await run_pipeline(upd, context, url)
        except Exception:
            pass
        finally:
            current_running -= 1
