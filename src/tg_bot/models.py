from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple, cast
from collections import deque

from sticker_convert.definitions import DEFAULT_DIR


PLATFORMS = [
    ("kakao", "Kakao"),
    ("line", "LINE"),
    ("signal", "Signal"),
    ("viber", "Viber"),
    ("telegram", "Telegram"),
    ("discord", "Discord"),
    ("ogq", "OGQ"),
    ("band", "BAND"),
    ("local", "Upload file"),
]


@dataclass
class Session:
    lang: str = "id"
    platform: Optional[str] = None
    state: str = "idle"  # awaiting_url | awaiting_file | idle
    input_dir: Path = field(default_factory=lambda: Path(DEFAULT_DIR, "stickers_input"))
    output_dir: Path = field(default_factory=lambda: Path(DEFAULT_DIR, "stickers_output"))
    failed_files: List[str] = field(default_factory=lambda: cast(List[str], []))
    last_used_ts: float = 0.0
    last_url: Optional[str] = None


SESSIONS: Dict[int, Session] = {}

# Global job queue with per-user anti-spam
job_queue: Deque[Tuple[int, Optional[str]]] = deque()
current_running: int = 0


def get_session(chat_id: int) -> Session:
    sess = SESSIONS.get(chat_id)
    if not sess:
        sess = Session()
        SESSIONS[chat_id] = sess
    return sess
