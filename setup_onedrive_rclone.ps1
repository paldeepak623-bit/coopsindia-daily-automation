# One-time OneDrive rclone setup (SharePoint folder)
# Run in PowerShell from this folder

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Rclone = Join-Path $ScriptDir "tools\rclone-v1.74.3-windows-amd64\rclone.exe"
$Conf = Join-Path $ScriptDir "rclone.conf"

if (-not (Test-Path $Rclone)) {
    Write-Host "Pehle rclone download ho chuka hona chahiye (tools folder)."
    exit 1
}

Write-Host "=========================================="
Write-Host "OneDrive / SharePoint — ek baar login"
Write-Host "=========================================="
Write-Host "Browser khulega — Microsoft account se login karo"
Write-Host "Folder link: cripson SharePoint (Bareilly - OneDrive tab)"
Write-Host ""

# Step 1: Get token via browser
Write-Host "Step 1: Authorize..."
$token = & $Rclone authorize "onedrive" --config $Conf 2>&1
Write-Host $token

Write-Host ""
Write-Host "Step 2: Remote banao..."
Write-Host "Site type: SharePoint / OneDrive for Business"
Write-Host "SharePoint URL: https://cripson-my.sharepoint.com"

& $Rclone config create onedrive onedrive `
    config_token $token `
    drive_type business `
    --config $Conf

Write-Host ""
Write-Host "Step 3: Test list..."
& $Rclone lsd onedrive: --config $Conf

Write-Host ""
Write-Host "Done. rclone.conf ready."
Write-Host "GitHub secret ke liye chalao: .\push_github.ps1"
