# GitHub repo + secrets setup
# Run AFTER: setup_google_oauth.py + setup_onedrive_rclone.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$RepoName = "coopsindia-daily-automation"

Write-Host "=== GitHub Setup ==="

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add .
git status

$commit = git diff --cached --quiet 2>$null
if ($LASTEXITCODE -ne 0) {
    git commit -m "CoopsIndia daily automation - login download upload logout"
}

$exists = gh repo view "paldeepak623-bit/$RepoName" 2>$null
if (-not $exists) {
    gh repo create $RepoName --private --source=. --remote=origin --push
} else {
    git remote add origin "https://github.com/paldeepak623-bit/$RepoName.git" 2>$null
    git push -u origin main
}

Write-Host "Setting GitHub Secrets..."

# CoopsIndia login
$cfg = Get-Content "config.json" -Raw | ConvertFrom-Json
gh secret set COOPS_LOGIN_ID --body $cfg.login_id
gh secret set COOPS_PASSWORD --body $cfg.password

# Google OAuth
if (Test-Path "credentials\google_oauth_token.json") {
    $tok = Get-Content "credentials\google_oauth_token.json" -Raw | ConvertFrom-Json
    gh secret set GOOGLE_OAUTH_CLIENT_ID --body $tok.client_id
    gh secret set GOOGLE_OAUTH_CLIENT_SECRET --body $tok.client_secret
    gh secret set GOOGLE_OAUTH_REFRESH_TOKEN --body $tok.refresh_token
    Write-Host "Google OAuth secrets set."
} else {
    Write-Host "WARN: credentials\google_oauth_token.json missing — pehle python setup_google_oauth.py chalao"
}

# Rclone config (OneDrive)
if (Test-Path "rclone.conf") {
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$ScriptDir\rclone.conf"))
    gh secret set RCLONE_CONFIG_B64 --body $b64
    Write-Host "Rclone secret set."
} else {
    Write-Host "WARN: rclone.conf missing — pehle setup_onedrive_rclone.ps1 chalao"
}

Write-Host ""
Write-Host "Repo: https://github.com/paldeepak623-bit/$RepoName"
Write-Host "Daily 9 AM IST cloud par chalega (GitHub Actions)."
Write-Host "Manual test: gh workflow run daily-coopsindia.yml"
