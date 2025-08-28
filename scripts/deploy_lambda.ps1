param(
  [string]$Region,
  [string]$FunctionName = "sticker-convert-bot",
  [string]$RepoName = "sticker-convert-bot",
  [string]$RoleName = "lambda-sticker-bot-role",
  [string]$Tag = "v1"
)

Write-Host "=== Deploy sticker-convert bot to AWS Lambda (container image) ==="

function Require-Cmd($cmd) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Error "Missing command: $cmd"
    exit 1
  }
}

Require-Cmd aws
Require-Cmd docker

# Region
if (-not $Region) {
  $Region = $env:AWS_DEFAULT_REGION
}
if (-not $Region) {
  $Region = Read-Host "AWS Region (e.g., ap-southeast-1)"
}
if (-not $Region) { Write-Error "Region is required"; exit 1 }

# AWS account
$AccountId = (aws sts get-caller-identity --query Account --output text)
if (-not $AccountId -or $AccountId -eq "None") { Write-Error "AWS CLI not configured or no credentials."; exit 1 }

# Secrets
$BotToken = Read-Host -AsSecureString "Enter BOT_TOKEN (from @BotFather)"
$GeminiKey = Read-Host -AsSecureString "Enter GEMINI_API_KEY (optional, press Enter to skip)"
$WebhookSecret = Read-Host -AsSecureString "Enter TELEGRAM_WEBHOOK_SECRET (recommended)"

function SecureToText($sec) {
  if (-not $sec) { return "" }
  return [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
}

$BotTokenPlain = SecureToText $BotToken
$GeminiKeyPlain = SecureToText $GeminiKey
$WebhookSecretPlain = SecureToText $WebhookSecret
if (-not $BotTokenPlain) { Write-Error "BOT_TOKEN is required"; exit 1 }

$Registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"
$ImageUri = "$Registry/$RepoName:$Tag"

Write-Host "[1/8] Ensure ECR repository: $RepoName"
try {
  aws ecr describe-repositories --repository-names $RepoName --region $Region | Out-Null
} catch {
  aws ecr create-repository --repository-name $RepoName --region $Region | Out-Null
}

Write-Host "[2/8] Login Docker to ECR: $Registry"
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $Registry | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "Docker login failed"; exit 1 }

Write-Host "[3/8] Build image (Dockerfile.lambda)"
docker build --platform linux/amd64 -f Dockerfile.lambda -t $RepoName:$Tag .
if ($LASTEXITCODE -ne 0) { Write-Error "Docker build failed"; exit 1 }

Write-Host "[4/8] Tag & push image: $ImageUri"
docker tag $RepoName:$Tag $ImageUri
docker push $ImageUri
if ($LASTEXITCODE -ne 0) { Write-Error "Docker push failed"; exit 1 }

Write-Host "[5/8] Ensure IAM Role: $RoleName"
$RoleArn = ""
try {
  $RoleArn = (aws iam get-role --role-name $RoleName | ConvertFrom-Json).Role.Arn
} catch {
  $Trust = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  $RoleArn = (aws iam create-role --role-name $RoleName --assume-role-policy-document $Trust | ConvertFrom-Json).Role.Arn
  aws iam attach-role-policy --role-name $RoleName --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole | Out-Null
}
if (-not $RoleArn) { Write-Error "Failed to ensure IAM role"; exit 1 }

Write-Host "[6/8] Create or update Lambda function: $FunctionName"
$FunctionExists = $false
try {
  aws lambda get-function --function-name $FunctionName | Out-Null
  $FunctionExists = $true
} catch { $FunctionExists = $false }

if ($FunctionExists) {
  aws lambda update-function-code --function-name $FunctionName --image-uri $ImageUri | Out-Null
  aws lambda update-function-configuration --function-name $FunctionName --timeout 120 --memory-size 2048 --environment "Variables={BOT_TOKEN='$BotTokenPlain',GEMINI_API_KEY='$GeminiKeyPlain',TELEGRAM_WEBHOOK_SECRET='$WebhookSecretPlain'}" | Out-Null
} else {
  aws lambda create-function --function-name $FunctionName --package-type Image --code ImageUri=$ImageUri --role $RoleArn --architectures x86_64 --timeout 120 --memory-size 2048 | Out-Null
  aws lambda update-function-configuration --function-name $FunctionName --environment "Variables={BOT_TOKEN='$BotTokenPlain',GEMINI_API_KEY='$GeminiKeyPlain',TELEGRAM_WEBHOOK_SECRET='$WebhookSecretPlain'}" | Out-Null
}

Write-Host "[7/8] Ensure Function URL"
$FuncUrl = ""
try {
  $FuncUrl = (aws lambda get-function-url-config --function-name $FunctionName | ConvertFrom-Json).FunctionUrl
} catch {
  $FuncUrl = (aws lambda create-function-url-config --function-name $FunctionName --auth-type NONE | ConvertFrom-Json).FunctionUrl
}
if (-not $FuncUrl) { Write-Error "Failed to get Function URL"; exit 1 }

Write-Host "[8/8] Set Telegram webhook"
$Body = @{ url = $FuncUrl.TrimEnd('/'); secret_token = $WebhookSecretPlain } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://api.telegram.org/bot$BotTokenPlain/setWebhook" -ContentType "application/json" -Body $Body | Out-Null

Write-Host "\n✓ Done"
Write-Host "Function URL: $FuncUrl"
Write-Host "ECR Image: $ImageUri"
Write-Host "You can test by sending a message to your bot. Check CloudWatch Logs if needed."
