#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tg_bot.services.ai import detect_emojis  # noqa: E402


async def main() -> None:
    sample = ROOT / "tests" / "samples" / "static_png_1_800x600.png"
    if not sample.exists():
        print("Sample not found; skipping")
        return
    res = await detect_emojis([sample], api_key=None)
    print("AI fallback result:", res)


if __name__ == "__main__":
    asyncio.run(main())
