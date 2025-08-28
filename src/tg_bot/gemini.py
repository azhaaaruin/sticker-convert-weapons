"""
Minimal Gemini emoji detector.

We avoid heavy dependencies; use HTTP to Gemini REST if available, else
heuristic fallback mapping. The function returns a dict {stem: emoji}.
"""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

import httpx


async def _detect_one(client: httpx.AsyncClient, path: Path, api_key: str, timeout_s: int) -> str:
    # Convert image frame to base64; videos/tgs will fallback to default emoji
    ext = path.suffix.lower()
    if ext not in (".png", ".webp", ".jpg", ".jpeg"):
        return "😀"

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    # Gemini 1.5 Flash or similar multimodal endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Return ONE emoji that best represents the facial expression or subject."},
                    {"inline_data": {"mime_type": "image/png", "data": b64}},
                ]
            }
        ]
    }
    r = await client.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()
    out = r.json()
    # naive parse; return first token
    try:
        text = out["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "😀"
    # sanitize to one emoji (basic)
    return text.split()[0] if text else "😀"


async def detect_emoji_batch(paths: Iterable[Path], api_key: str, progress_cb: Optional[Callable[[int, int], None]] = None, timeout_s: int = 30, max_retries: int = 1) -> Dict[str, str]:
    items: List[Path] = list(paths)
    total = len(items)
    res: Dict[str, str] = {}
    if total == 0:
        return res
    async with httpx.AsyncClient() as client:
        done = 0
        for p in items:
            emo = "😀"
            try:
                emo = await _detect_one(client, p, api_key, timeout_s)
            except Exception:
                # simple retry
                for _ in range(max_retries):
                    try:
                        emo = await _detect_one(client, p, api_key, timeout_s)
                        break
                    except Exception:
                        continue
            res[p.stem] = emo
            done += 1
            if progress_cb:
                progress_cb(done, total)
    return res
