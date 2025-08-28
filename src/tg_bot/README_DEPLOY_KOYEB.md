Koyeb deployment guide

Overview
- This bot runs with long-polling; no inbound HTTP port is needed.
- We ship a Dockerfile suitable for Koyeb: Dockerfile.bot
- Configure environment variables and deploy from your GitHub repo.

Steps (UI)
1) In Koyeb, create a new App → Deploy from GitHub → select this repository.
2) Build settings:
   - Build method: Docker
   - Dockerfile path: Dockerfile.bot
3) Runtime command: leave default (Dockerfile CMD is sticker-bot).
4) Networking:
   - Do NOT expose any port (no routes needed). This runs as a worker-like service.
5) Environment variables:
   - BOT_TOKEN: your Telegram bot token (required)
   - GEMINI_API_KEY: optional, for emoji detection (leave empty to use 😀 fallback)
   - MAX_FILE_SIZE_MB: optional (default 25)
6) Resources & scaling:
   - Instances: 1 (you can scale up later)
   - Choose a region/machine size as you prefer
7) Deploy. Check logs to verify the bot starts and receives updates.

Notes
- Filesystem is ephemeral by default. Conversion temp/output directories are fine to be ephemeral.
- For persistence, attach a Volume in Koyeb and set custom dirs in code if needed later.
- No HTTP healthcheck is required; the process stays up and logs activity as updates arrive.

Troubleshooting
- If the service restarts repeatedly, confirm BOT_TOKEN is valid and the bot is started via @BotFather.
- If emoji detection fails, set GEMINI_API_KEY or run with fallback (default 😀).
- ffmpeg is installed in the image; if a specific format fails, capture logs and sample to debug.
