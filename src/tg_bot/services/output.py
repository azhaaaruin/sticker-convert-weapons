from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol


class OutputBackend(Protocol):
    async def send(self, chat_id: int, files: List[Path], captions: Dict[str, str]) -> List[str]:
        """Send files to a destination and return a list of failed file names."""
        ...


@dataclass
class TelegramOutputBackend:
    bot: Any  # telegram.Bot-like

    async def send(self, chat_id: int, files: List[Path], captions: Dict[str, str]) -> List[str]:
        fails: List[str] = []
        for p in files:
            try:
                with p.open("rb") as f:
                    await self.bot.send_document(chat_id=chat_id, document=f, caption=captions.get(p.stem, ""))
            except Exception:
                fails.append(p.name)
        return fails


def get_output_backend(name: str, **kwargs: object) -> OutputBackend:
    """Factory for output backends. Currently only 'telegram'."""
    if name == "telegram":
        return TelegramOutputBackend(bot=kwargs.get("bot"))
    raise ValueError(f"Unknown output backend: {name}")
