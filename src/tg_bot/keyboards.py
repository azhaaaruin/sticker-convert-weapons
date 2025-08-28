from __future__ import annotations

from typing import Dict, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def lang_keyboard(langs: Dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(name, callback_data=f"lang:{code}")]
         for code, name in langs.items()]
    )


def platform_keyboard(platforms: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for code, name in platforms:
        row.append(InlineKeyboardButton(name, callback_data=f"platform:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)
