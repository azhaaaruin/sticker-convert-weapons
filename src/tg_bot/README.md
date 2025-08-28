# Telegram Bot module structure

src/tg_bot/
  - bot.py           # entrypoint; wires handlers and config
  - config.py        # env var loading, limits
  - handlers.py      # telegram update handlers
  - i18n.py          # language texts
  - keyboards.py     # inline keyboards
  - models.py        # Session and constants
  - services/
      - conversion.py  # conversion pipeline via sticker_convert.Job
      - ai.py          # Gemini emoji detection wrapper
  - gemini.py        # minimal Gemini REST integration

Run:
  BOT_TOKEN=... GEMINI_API_KEY=... python -m tg_bot.bot
