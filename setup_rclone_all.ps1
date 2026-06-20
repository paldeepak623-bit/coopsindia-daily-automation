# Google Drive + OneDrive one-time login (rclone)
# Run: powershell -ExecutionPolicy Bypass -File setup_rclone_all.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Rclone = Join-Path $ScriptDir "tools\rclone-v1.74.3-windows-amd64\rclone.exe"
$Conf = Join-Path $ScriptDir "rclone.conf"

if (-not (Test-Path $Rclone)) {
    Write-Host "Downloading rclone..."
    $tools = Join-Path $ScriptDir "tools"
    New-Item -ItemType Directory -Force -Path $tools | Out-Null
    $zip = Join-Path $tools "rclone.zip"
    Invoke-WebRequest -Uri "https://downloads.rclone.org/rclone-current-windows-amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tools -Force
    $Rclone = (Get-ChildItem $tools -Recurse -Filter rclone.exe | Select-Object -First 1).FullName
}

Write-Host ""
Write-Host "STEP 1/2 - Google Drive login (browser opens)"
Write-Host ""

$gdriveToken = & $Rclone authorize drive 2>&1 | Select-Object -Last 1
& $Rclone config create gdrive drive config_token $gdriveToken root_folder_id 1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5 --config $Conf

Write-Host ""
Write-Host "STEP 2/2 - OneDrive login (browser opens)"
Write-Host ""

$odToken = & $Rclone authorize onedrive 2>&1 | Select-Object -Last 1
& $Rclone config create onedrive onedrive config_token $odToken drive_type business --config $Conf

Write-Host ""
Write-Host "Testing..."
& $Rclone lsd gdrive: --config $Conf
& $Rclone lsd onedrive: --config $Conf

Write-Host ""
Write-Host "DONE - rclone.conf ready"
Write-Host "Next: powershell -File push_github.ps1"
