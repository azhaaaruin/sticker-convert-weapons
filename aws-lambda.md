Deploy to AWS Lambda (Telegram webhook)

Overview
- Use a Function URL or API Gateway to receive Telegram webhooks.
- Image: build with Dockerfile.lambda and push to ECR, then create a Lambda from image.
- Set webhook to your public URL with optional secret.

Steps
1) Create ECR repo and build/push image:
   - Build: Dockerfile.lambda
   - Push to ECR: tag and push
2) Create Lambda from container image
   - Handler is provided by container CMD (tg_bot.lambda_handler.handler)
   - Memory: 1024MB+, Timeout: 60–120s recommended
   - Arch: x86_64 (recommended)
3) Configure env variables on Lambda:
   - BOT_TOKEN: required
   - GEMINI_API_KEY: optional
   - TELEGRAM_WEBHOOK_SECRET: optional (recommended)
   - MAX_FILE_SIZE_MB etc: optional
4) Expose URL:
   - Option A: Lambda Function URL (Auth: NONE) and restrict via webhook secret
   - Option B: API Gateway HTTP API → Lambda integration
5) Set Telegram webhook:
   - POST https://api.telegram.org/bot<token>/setWebhook with json:
     {"url":"<YOUR_URL>","secret_token":"<SECRET>"}
6) Test: send a message to the bot and watch CloudWatch logs.

Unset previous webhook (if using polling before):
- https://api.telegram.org/bot<token>/deleteWebhook

Notes
- ffmpeg included for conversion. No GUI/Wine needed on Lambda.
- Storage is ephemeral; we write temp files to /tmp (default).
- Concurrency: each update is handled per-invocation; consider rate limits and retries.
