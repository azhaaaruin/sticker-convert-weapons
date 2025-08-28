from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Iterable, Optional

from ..config import load_config


async def detect_emojis(paths: Iterable[Path], api_key: Optional[str], progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, str]:
    # Lazy import Gemini only when API key is present to avoid requiring httpx in fallback-only mode
    if not api_key:
        return {p.stem: "😀" for p in paths}
    from ..gemini import detect_emoji_batch  # Local import to defer httpx dependency
    cfg = load_config()
    return await detect_emoji_batch(
        paths,
        api_key,
        progress_cb=progress,
        timeout_s=cfg.gemini_timeout_s,
        max_retries=cfg.gemini_max_retries,
    )
