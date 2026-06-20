# CoopsIndia — Daily 9 AM Automation Setup

## Aap kya chahte ho

| Requirement | Solution |
|-------------|----------|
| Roz subah **9:00 AM** auto chale | Windows Task Scheduler **ya** GitHub Actions (cloud) |
| Excel **kal ki date** ke folder mein | `19-06-2026` jaisa folder (aaj 20-06-2026 ho to) |
| **Google Drive** par upload | Google Service Account (neeche steps) |
| **OneDrive/SharePoint** par upload | PC par folder **Sync** karke local path |
| **Bina touch kiye** chale | Task Scheduler (laptop ON) **ya** GitHub Actions (laptop OFF) |

---

## IMPORTANT — Laptop band hone par

**Agar laptop 9 baje band / sleep mein hai, to koi bhi local script NAHI chalegi.**

| Option | Laptop OFF par kaam? | Cost |
|--------|----------------------|------|
| **A) Windows Task Scheduler** | ❌ Nahi (laptop ON ya sleep+Wake chahiye) | Free |
| **B) GitHub Actions (cloud)** | ✅ Haan — har din cloud par chalega | Free (private repo) |

**100% bina laptop ke:** Option **B** use karein (Section 4).

---

## Step 1 — Pehle ek baar setup (aapke PC par)

```powershell
cd "C:\Users\Deepak Pal\OneDrive\Desktop\Coopsindia Login"
pip install -r requirements.txt
playwright install chromium
```

`config.json` check karein (password + paths).

**Test (ek baar manually):**
```powershell
python daily_job.py --visible
```
Excel `downloads\DD-MM-YYYY\` folder mein aani chahiye + logout hona chahiye.

---

## Step 2 — Roz 9 AM (laptop ON rehne par)

1. PowerShell **Administrator** se kholo
2. Chalao:
```powershell
cd "C:\Users\Deepak Pal\OneDrive\Desktop\Coopsindia Login"
Set-ExecutionPolicy -Scope Process Bypass
.\install_task.ps1
```

Task name: **CoopsIndia Daily Report 9AM**

Logs: `logs\daily_YYYYMMDD.log`

**Laptop sleep par:** BIOS / Windows mein "Wake timers" enable karein taaki 9 baje uth jaye (optional).

---

## Step 3 — Google Drive upload setup

Folder link: https://drive.google.com/drive/folders/1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5

### Zaroori cheezein (aapko deni hongi / banana hoga)

1. **Google Cloud Project** (free) — https://console.cloud.google.com
2. **Google Drive API** enable karein
3. **Service Account** banao → JSON key download karein
4. JSON file yahan rakhein:
   `credentials\google_service_account.json`
5. Service account ka email (JSON mein `client_email`) copy karein
6. Apne Google Drive folder ko us email ke saath **Editor** share karein

`config.json` mein:
```json
"google_drive": {
  "enabled": true,
  "folder_id": "1QSO9aBUym6ZdvwrkZGq7H-SCALhC34S5",
  "service_account_json": "credentials/google_service_account.json"
}
```

Har din structure:
```
Google Drive Folder/
  └── 19-06-2026/
        └── DCT_Status_Summary_....xlsx
```

---

## Step 3b — OneDrive / SharePoint upload

Link: https://cripson-my.sharepoint.com/... (aapka SharePoint folder)

**Sabse aasaan tareeka:**

1. Browser mein folder kholo → **Sync** dabao (OneDrive app install hogi)
2. PC par sync path dhundo, jaise:
   `C:\Users\Deepak Pal\OneDrive - cripson\CoopsIndia Reports`
   (exact naam aapke PC par alag ho sakta hai)
3. `config.json` mein:
```json
"onedrive": {
  "enabled": true,
  "local_sync_path": "C:\\Users\\Deepak Pal\\OneDrive - cripson\\SHAREPOINT_FOLDER_NAME"
}
```

Script file copy karegi → OneDrive khud cloud par upload karega.

---

## Step 4 — Laptop OFF par bhi chale (GitHub Actions — recommended)

### Aapko chahiye

1. **GitHub account** (free)
2. Is folder ko **private GitHub repo** mein push karein
3. Repo **Secrets** mein ye daalein:

| Secret name | Value |
|-------------|-------|
| `COOPS_LOGIN_ID` | `dccbbr.jarb@coopsindia.com` |
| `COOPS_PASSWORD` | aapka password |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | poori JSON file ka text (copy-paste) |

4. Workflow file already hai: `.github/workflows/daily-coopsindia.yml`
5. Time: **9:00 AM IST** har din cloud par automatically

**OneDrive cloud-only upload** GitHub se direct mushkil hai — uske liye:
- Google Drive use karein (setup upar), **ya**
- Azure VM (~₹500/month) par poora script chalao

---

## Folder date logic

| Aaj ki date | Banega folder | Report |
|-------------|---------------|--------|
| 20-06-2026 9 AM | `19-06-2026` | us din ka DCT data |

---

## Aap se ab kya chahiye (requirements list)

Please ye confirm / provide karein:

1. ✅ **CoopsIndia login** — already hai
2. ⬜ **Google Service Account JSON** — aapko Google Cloud se banana hoga (Section 3)
3. ⬜ **OneDrive sync folder ka exact path** — Sync ke baad mujhe path bata dena
4. ⬜ **Laptop OFF par bhi chahiye?** → Haan = GitHub repo + secrets setup
5. ⬜ **GitHub username** — agar cloud setup mein help chahiye

---

## Files

| File | Kaam |
|------|------|
| `daily_job.py` | Poora daily kaam |
| `run_daily.bat` | Scheduler ke liye |
| `install_task.ps1` | 9 AM task install |
| `config.json` | Password + upload settings |
| `upload_drives.py` | Drive upload |
| `logs/` | Daily logs |

---

## Troubleshooting

- **Session busy** — pichhli run ne logout nahi kiya; 3 min wait automatic hai
- **Google upload fail** — folder service account email se share kiya?
- **OneDrive upload fail** — `local_sync_path` sahi hai? Folder exist karta hai?
- **Task nahi chala** — laptop ON tha? Task Scheduler → History check karein
