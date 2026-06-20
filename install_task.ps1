# Windows Task Scheduler — roz subah 9:00 AM (laptop ON hona chahiye)
# Run as Administrator: right-click -> Run with PowerShell

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BatPath = Join-Path $ScriptDir "run_daily.bat"
$TaskName = "CoopsIndia Daily Report 9AM"

if (-not (Test-Path $BatPath)) {
    Write-Error "run_daily.bat not found: $BatPath"
    exit 1
}

$Action = New-ScheduledTaskAction -Execute $BatPath -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00"
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host "Task installed: $TaskName"
Write-Host "Time: Daily 9:00 AM"
Write-Host "Script: $BatPath"
Write-Host ""
Write-Host "NOTE: Laptop band hone par ye task NAHI chalega."
Write-Host "Laptop OFF par bhi chahiye to GitHub Actions setup dekhein (SETUP_AUTOMATION.md)."
