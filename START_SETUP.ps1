# Poora setup — step by step (sirf ek baar)

Write-Host @"

========================================
CoopsIndia Daily Automation — Setup
========================================

BLOCKED GOOGLE WINDOW?
  -> Wo gcloud wala tha — BAND karo.
  -> Neeche Step 1 follow karo (apna OAuth client).

STEP 1 — Google Drive (2 min, ek baar)
  python setup_google_oauth.py

STEP 2 — OneDrive SharePoint (2 min, ek baar)
  .\setup_onedrive_rclone.ps1

STEP 3 — GitHub cloud (laptop OFF par bhi chalega)
  .\push_github.ps1

STEP 4 — Test
  python daily_job.py

Roz 9 AM: GitHub Actions automatic (laptop band ho tab bhi)

"@

Set-Location $PSScriptRoot
pip install -q -r requirements.txt
Write-Host "Dependencies OK. Ab Step 1 chalao: python setup_google_oauth.py"
