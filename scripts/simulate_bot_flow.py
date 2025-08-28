#!/usr/bin/env python3
"""
Lightweight end-to-end simulation of the Telegram bot handlers without real network.
It mocks heavy services (conversion, AI) and Telegram API objects to validate flows:
- /start -> language -> platform (local + url)
- document/media upload flow with pre-ETA
- URL flow with pre-ETA notice
- queueing across two users
- cooldown
- retry with failed files

Run: python scripts/simulate_bot_flow.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional


# Ensure project root and src on sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Provide required env vars
os.environ.setdefault("BOT_TOKEN", "TEST_TOKEN")
os.environ.setdefault("GEMINI_API_KEY", "")


def install_service_mocks() -> None:
    """Mock heavy services before importing handlers so relative imports resolve to fakes."""
    async def fake_convert_and_collect(message: Any, sess: Any, url: Optional[str]) -> List[Path]:
        # Simulate some work and produce output files
        await asyncio.sleep(0.05)
        out = Path(sess.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files: List[Path] = []
        count = 3 if url else max(1, len([p for p in Path(sess.input_dir).glob('*') if p.is_file()]))
        for i in range(count):
            p = out / f"out_{i+1}.webp"
            p.write_bytes(b"RIFFWEBP\x00")
            files.append(p)
        return files

    async def fake_detect_emojis(files: List[Path], api_key: Optional[str], progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, str]:
        total = len(files)
        for i in range(total):
            await asyncio.sleep(0.02)
            if progress:
                progress(i + 1, total)
        return {p.stem: "😀" for p in files}

    sys.modules['tg_bot.services.conversion'] = SimpleNamespace(convert_and_collect=fake_convert_and_collect)
    sys.modules['tg_bot.services.ai'] = SimpleNamespace(detect_emojis=fake_detect_emojis)

    # Minimal telegram stubs to satisfy imports in handlers
    class _TgUpdate:
        def __init__(self, update_id: int, message: Any):
            self.update_id = update_id
            self.message = message
            self.effective_chat = SimpleNamespace(id=getattr(message, 'chat', SimpleNamespace(id=0)).id)
            self.effective_user = SimpleNamespace(language_code="en")

    class _ContextTypes:
        DEFAULT_TYPE = object

    class _ChatAction:
        UPLOAD_DOCUMENT = "UPLOAD_DOCUMENT"
        UPLOAD_PHOTO = "UPLOAD_PHOTO"

    class _InlineKeyboardButton:
        def __init__(self, text: str, callback_data: str) -> None:
            self.text = text
            self.callback_data = callback_data

    class _InlineKeyboardMarkup:
        def __init__(self, inline_keyboard: Any) -> None:
            self.inline_keyboard = inline_keyboard

    sys.modules['telegram'] = SimpleNamespace(Update=_TgUpdate, InlineKeyboardButton=_InlineKeyboardButton, InlineKeyboardMarkup=_InlineKeyboardMarkup)
    sys.modules['telegram.ext'] = SimpleNamespace(ContextTypes=_ContextTypes)
    sys.modules['telegram.constants'] = SimpleNamespace(ChatAction=_ChatAction)


# Minimal Telegram-like fakes
@dataclass
class FakeChat:
    id: int
    async def send_action(self, *_: Any, **__: Any) -> None:
        return None


class FakeFile:
    def __init__(self, source: Optional[Path] = None) -> None:
        self.source = source

    async def download_to_drive(self, custom_path: str) -> None:
        dst = Path(custom_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if self.source and self.source.exists():
            dst.write_bytes(self.source.read_bytes())
        else:
            dst.write_bytes(b"data")


class FakeDocument:
    def __init__(self, file_name: str, source: Optional[Path] = None) -> None:
        self.file_name = file_name
        self._file = FakeFile(source)

    async def get_file(self) -> FakeFile:
        return self._file


class FakePhoto:
    def __init__(self, file_unique_id: str, source: Optional[Path] = None) -> None:
        self.file_unique_id = file_unique_id
        self._file = FakeFile(source)

    async def get_file(self) -> FakeFile:
        return self._file


class FakeVideo:
    def __init__(self, file_unique_id: str, source: Optional[Path] = None) -> None:
        self.file_unique_id = file_unique_id
        self._file = FakeFile(source)

    async def get_file(self) -> FakeFile:
        return self._file


class FakeMessage:
    def __init__(self, chat_id: int, text: Optional[str] = None, document: Optional[FakeDocument] = None, photo: Optional[List[FakePhoto]] = None, video: Optional[FakeVideo] = None) -> None:
        self.text = text
        self.document = document
        self.photo = photo
        self.video = video
        self.chat = FakeChat(chat_id)
        self._log: List[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> 'FakeMessage':
        self._log.append(f"reply_text: {text}")
        return FakeMessage(self.chat.id, text=text)

    async def edit_text(self, text: str, **kwargs: Any) -> None:
        self._log.append(f"edit_text: {text}")


class FakeCallbackQuery:
    def __init__(self, chat_id: int, data: str) -> None:
        self.data = data
        self.message = FakeMessage(chat_id, text="callback")

    async def answer(self) -> None:
        return None

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.message._log.append(f"edit_message_text: {text}")


class FakeBot:
    def __init__(self) -> None:
        self.sent_docs: List[str] = []
        self.sent_msgs: List[str] = []

    async def send_document(self, chat_id: int, document: Any, caption: Optional[str] = None) -> None:
        self.sent_docs.append(f"to {chat_id} caption={caption}")

    async def send_message(self, chat_id: int, text: str) -> FakeMessage:
        self.sent_msgs.append(f"to {chat_id}: {text}")
        return FakeMessage(chat_id, text=text)


class FakeContext:
    def __init__(self) -> None:
        self.bot = FakeBot()


class FakeUpdate:
    def __init__(self, chat_id: int, message: Optional[FakeMessage] = None, callback_data: Optional[str] = None, user_lang: Optional[str] = None) -> None:
        self.effective_chat = SimpleNamespace(id=chat_id)
        self.effective_user = SimpleNamespace(language_code=user_lang or "en")
        self.message = message
        self.callback_query = FakeCallbackQuery(chat_id, callback_data) if callback_data else None


async def simulate_flows() -> None:
    install_service_mocks()
    # Import after mocks
    from tg_bot.handlers import cmd_start, on_lang, on_platform, on_document, on_text, cmd_retry, enqueue_or_run
    from tg_bot.models import get_session
    from tg_bot.i18n import t

    ctx = FakeContext()
    samples_dir = ROOT / 'tests' / 'samples'
    sample_png = samples_dir / 'static_png_1_800x600.png'

    print("-- Flow A: Upload (local) --")
    upd = FakeUpdate(1, message=FakeMessage(1, text="/start"), user_lang="id")
    await cmd_start(upd, ctx)  # welcome
    upd = FakeUpdate(1, callback_data="lang:id")
    await on_lang(upd, ctx)    # choose platform
    upd = FakeUpdate(1, callback_data="platform:local")
    await on_platform(upd, ctx)  # send_file
    doc = FakeDocument("sample.png", source=sample_png if sample_png.exists() else None)
    upd = FakeUpdate(1, message=FakeMessage(1, document=doc))
    await on_document(upd, ctx)  # should reply detected_files, then process and send results

    # Cooldown test
    sess = get_session(1)
    import time
    sess.last_used_ts = time.time()
    await enqueue_or_run(FakeUpdate(1, message=FakeMessage(1, text="again")), ctx)

    print("-- Flow B: URL flow (kakao) and queueing --")
    upd2 = FakeUpdate(2, message=FakeMessage(2, text="/start"), user_lang="en")
    await cmd_start(upd2, ctx)
    await on_lang(FakeUpdate(2, callback_data="lang:en"), ctx)
    await on_platform(FakeUpdate(2, callback_data="platform:kakao"), ctx)
    # Start user 2 processing (will be queued if user 1 is running)
    await on_text(FakeUpdate(2, message=FakeMessage(2, text="https://example.com/pack")), ctx)

    # Retry flow: mark one file as failed and ensure retry moves it back
    sess.failed_files = ["out_1.webp"]
    Path(sess.output_dir, "out_1.webp").write_bytes(b"x")
    await cmd_retry(FakeUpdate(1, message=FakeMessage(1, text="/retry")), ctx)

    # Print summary
    print("Bot sent messages:")
    for m in ctx.bot.sent_msgs:
        print(" ", m)
    print("Bot sent documents:")
    for d in ctx.bot.sent_docs:
        print(" ", d)
    print("All good if no exceptions were raised.")


def main() -> None:
    asyncio.run(simulate_flows())


if __name__ == "__main__":
    main()
