Railway deployment guide

1) Create a new Railway project and choose “Deploy from GitHub” pointing to this repo, or “Empty Project” and then connect your repo.

2) Variables to set in Railway → Variables:
   - BOT_TOKEN: your Telegram bot token (required)
   - GEMINI_API_KEY: optional, for emoji detection
   - MAX_FILE_SIZE_MB: optional (default 25)

3) Build & Deploy configuration:
   - Railway auto-detects `railway.json` and will build using Dockerfile.bot
   - Start command is `sticker-bot` via the package entrypoint

4) Networking:
   - This bot uses polling, so no inbound HTTP port is required. Leave service as “Worker” if prompted.

5) Files storage:
   - The bot writes to `/app/src/sticker_convert/stickers_input` and `.../stickers_output` in the container. Railway ephemeral filesystem is OK; data resets on redeploy.
   - If you need persistence, attach a Railway Volume and set env vars DEFAULT_DIR accordingly (not required by default).

6) Logs:
   - View real-time logs in Railway to verify the bot is running and receiving updates.

7) Troubleshooting:
   - Ensure BOT_TOKEN is correct and the bot is started via @BotFather
   - If media conversion fails for some formats, ffmpeg is preinstalled in the image; share failing samples to debug.
