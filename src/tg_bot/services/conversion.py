from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Awaitable, Callable, Optional, Tuple, cast

from telegram.constants import ChatAction

from sticker_convert.job import Job
from sticker_convert.job_option import CompOption, CredOption, InputOption, OutputOption
from sticker_convert.utils.files.metadata_handler import MetadataHandler


def ensure_dirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_options(
    input_dir: Path,
    output_dir: Path,
    platform: Optional[str],
    url: Optional[str],
) -> Tuple[InputOption, CompOption, OutputOption, CredOption]:
    opt_input = InputOption()
    if url and platform and platform != "local":
        opt_input.option = platform
        opt_input.url = url
    else:
        opt_input.option = "local"
    opt_input.dir = input_dir

    comp = CompOption(preset="telegram", steps=6)
    comp.default_emoji = "😀"
    comp.processes = 1

    out = OutputOption(option="local", dir=output_dir, title="Sticker Pack", author="Bot")
    cred = CredOption()  # Telegram cred not needed for local export
    return opt_input, comp, out, cred


class JobCallback:
    def __init__(self, msg_edit: Callable[[str], Awaitable[object]]):
        self.msg_edit = msg_edit

    def put(self, item: object) -> None:
        if isinstance(item, tuple):
            first = cast("tuple[object, ...]", item)[0]
            text = str(first)
        else:
            text = str(item)
        # msg_edit is an async function, wrap into a coroutine
        async def _run() -> None:
            await self.msg_edit(text)
        asyncio.get_event_loop().create_task(_run())


from telegram import Message
from ..models import Session


async def convert_and_collect(message: Message, sess: Session, url: Optional[str]) -> list[Path]:
    ensure_dirs(sess.input_dir)
    ensure_dirs(sess.output_dir)

    status = await message.reply_text("⏳ Processing...")

    cb = JobCallback(status.edit_text)

    MetadataHandler.generate_emoji_file(sess.input_dir, default_emoji="😀")
    tpath = Path(sess.input_dir, "title.txt")
    if not tpath.exists():
        tpath.write_text("Sticker Pack", encoding="utf-8")

    opt_input, comp, out, cred = build_options(sess.input_dir, sess.output_dir, sess.platform, url)

    def cb_msg(*args: object, **kwargs: object) -> None:
        cb.put(" ".join(map(str, args)))

    def cb_msg_block(*args: object, **kwargs: object) -> None:
        cb.put(" ".join(map(str, args)))
        return None

    def cb_bar(*args: object, **kwargs: object) -> None:
        if "update_bar" in kwargs or (args and args[0] == "update_bar"):
            cb.put("⏳ progress")

    def cb_ask_bool(*args: object, **kwargs: object) -> bool:
        cb.put(("ask_bool", args, kwargs))
        return False

    def cb_ask_str(*args: object, **kwargs: object) -> str:
        cb.put(("ask_str", args, kwargs))
        return ""

    job = Job(opt_input, comp, out, cred, cb_msg, cb_msg_block, cb_bar, cb_ask_bool, cb_ask_str)

    await message.chat.send_action(ChatAction.TYPING)
    await asyncio.to_thread(job.start)

    files = [p for p in sorted(sess.output_dir.iterdir()) if p.is_file() and p.suffix.lower() in (".png", ".webp", ".webm", ".tgs")]
    return files
