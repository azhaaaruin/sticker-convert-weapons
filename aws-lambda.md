Deploy to AWS Lambda (Telegram webhook)

Overview
- Use a Function URL or API Gateway to receive Telegram webhooks.
- Image: build with Dockerfile.lambda and push to ECR, then create a Lambda from image.
- Set webhook to your public URL with optional secret.

Steps (paling mudah via Console)
1) Siapkan ECR image tanpa install apa-apa di laptop:
   - Buka GitHub → Repo → Actions → jalankan workflow "Build and Push Lambda Image to ECR" (workflow_dispatch)
   - Isi image_tag (misal: v1) → Run
   - Pastikan sudah set Secrets di GitHub: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
   - Hasilnya: image ter-push ke ECR otomatis
   - Alternatif: build lokal, lihat panduan CLI di bawah

2) Buat Lambda dari container image
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
5) Set Telegram webhook (Console friendly):
   - POST https://api.telegram.org/bot<token>/setWebhook with json:
     {"url":"<YOUR_URL>","secret_token":"<SECRET>"}
   - Bisa juga via Postman/Insomnia atau curl di CloudShell
6) Test: send a message to the bot and watch CloudWatch logs.

Unset previous webhook (if using polling before):
- https://api.telegram.org/bot<token>/deleteWebhook

Notes
- ffmpeg included for conversion. No GUI/Wine needed on Lambda.
- Storage is ephemeral; we write temp files to /tmp (default).
- Concurrency: each update is handled per-invocation; consider rate limits and retries.

CLI (opsional, kalau mau manual dari laptop)
- Lihat scripts/deploy_lambda.ps1 untuk otomatisasi satu-perintah.
