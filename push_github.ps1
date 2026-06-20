# Auto push secrets + workflow to GitHub cloud
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir
$Repo = "paldeepak623-bit/coopsindia-daily-automation"

$cfg = Get-Content "config.json" -Raw | ConvertFrom-Json
gh secret set COOPS_LOGIN_ID --body $cfg.login_id --repo $Repo
gh secret set COOPS_PASSWORD --body $cfg.password --repo $Repo

if (Test-Path "rclone.conf") {
    $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$ScriptDir\rclone.conf"))
    gh secret set RCLONE_CONFIG_B64 --body $b64 --repo $Repo
    Write-Host "Secrets OK"
} else {
    Write-Host "rclone.conf missing"
    exit 1
}

git add -A
git commit -m "Cloud automation update" 2>$null
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "git push failed - trying gh api..."
    $content = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content ".github/workflows/daily-coopsindia.yml" -Raw)))
    gh api -X PUT "repos/$Repo/contents/.github/workflows/daily-coopsindia.yml" -f message="Add daily workflow" -f content=$content 2>&1
}

Write-Host "Done: https://github.com/$Repo/actions"
