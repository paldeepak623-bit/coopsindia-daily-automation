# GitHub cloud secrets + workflow push
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Repo = "paldeepak623-bit/coopsindia-daily-automation"

Write-Host "=== GitHub Cloud Setup ==="

$cfg = Get-Content "config.json" -Raw | ConvertFrom-Json
gh secret set COOPS_LOGIN_ID --body $cfg.login_id --repo $Repo
gh secret set COOPS_PASSWORD --body $cfg.password --repo $Repo

if (Test-Path "rclone.conf") {
    $bytes = [IO.File]::ReadAllBytes("$ScriptDir\rclone.conf")
    $b64 = [Convert]::ToBase64String($bytes)
    gh secret set RCLONE_CONFIG_B64 --body $b64 --repo $Repo
    Write-Host "RCLONE_CONFIG_B64 secret set (Google + OneDrive dono)."
} else {
    Write-Host "ERROR: rclone.conf nahi mila — pehle .\setup_rclone_all.ps1 chalao"
    exit 1
}

git add -A
git commit -m "Cloud daily automation with rclone upload" 2>$null
git push origin main 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Workflow push ke liye ek baar ye chalao:"
    Write-Host "  gh auth refresh -h github.com -s workflow"
    Write-Host "  git push origin main"
}

Write-Host ""
Write-Host "Repo: https://github.com/$Repo"
Write-Host "Roz 9:00 AM IST — GitHub cloud par automatic (laptop band ho tab bhi)"
Write-Host "Manual test: gh workflow run daily-coopsindia.yml --repo $Repo"
