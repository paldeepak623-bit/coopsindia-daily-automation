# Ek baar chalao — Google Drive + OneDrive login (2-3 minute)
# Uske baad GitHub cloud roz 9 AM khud chalega (laptop OFF OK)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Rclone = Join-Path $ScriptDir "tools\rclone-v1.74.3-windows-amd64\rclone.exe"
$Conf = Join-Path $ScriptDir "rclone.conf"

if (-not (Test-Path $Rclone)) {
    Write-Host "rclone download ho raha hai..."
    $tools = Join-Path $ScriptDir "tools"
    New-Item -ItemType Directory -Force -Path $tools | Out-Null
    $zip = Join-Path $tools "rclone.zip"
    Invoke-WebRequest -Uri "https://downloads.rclone.org/rclone-current-windows-amd64.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $tools -Force
    $Rclone = (Get-ChildItem $tools -Recurse -Filter rclone.exe | Select-Object -First 1).FullName
}

Write-Host ""
Write-Host "=========================================="
Write-Host "STEP 1/2 — Google Drive login"
Write-Host "Browser khulega — paldeepak623@gmail.com se Allow karo"
Write-Host "=========================================="
Write-Host ""

$gdriveScope = "drive,root_folder_id=1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5"
$gdriveToken = & $Rclone authorize $gdriveScope 2>&1 | Out-String
Write-Host $gdriveToken

& $Rclone config create gdrive drive config_token $gdriveToken root_folder_id 1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5 --config $Conf 2>&1

Write-Host ""
Write-Host "=========================================="
Write-Host "STEP 2/2 — OneDrive / SharePoint login"
Write-Host "Browser khulega — Microsoft account se login karo"
Write-Host "=========================================="
Write-Host ""

$odToken = & $Rclone authorize onedrive 2>&1 | Out-String
Write-Host $odToken

& $Rclone config create onedrive onedrive config_token $odToken drive_type business --config $Conf 2>&1

Write-Host ""
Write-Host "Test upload paths..."
& $Rclone lsd gdrive: --config $Conf
& $Rclone lsd onedrive: --config $Conf

Write-Host ""
Write-Host "DONE — rclone.conf ready."
Write-Host "Ab chalao: .\push_github.ps1"
