Write-Host @"

======================================================
CoopsIndia — FINAL SETUP (sirf ek baar, 5 minute)
======================================================

LAPTOP OFF par bhi roz 9 AM chalega?  -> HAAN (GitHub Cloud)
Laptop ON roz subah?                    -> NAHI chahiye

Sirf 2 step (ek baar):

  1) .\setup_rclone_all.ps1
     -> Google + OneDrive login (aapka account, kisi aur se permission NAHI)

  2) .\push_github.ps1
     -> GitHub secrets + cloud schedule

Agar git push fail ho to:
  gh auth refresh -h github.com -s workflow
  git push origin main

======================================================

"@

Set-Location $PSScriptRoot
