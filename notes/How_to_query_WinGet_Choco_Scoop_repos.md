How_to_query_WinGet_Choco_Scoop_repos.md

Below are **direct, reproducible ways to query package counts yourself** from each package manager using their official CLIs. These give you **real counts from your system at query time**, not estimates.

---

## 🪟 WinGet (Windows Package Manager)

### Count all available packages in the default repositories

```powershell
winget search --source winget | Measure-Object -Line
```

**What this does**

* `winget search` lists all manifests
* `Measure-Object -Line` counts the result rows

### Optional: export and count exactly

```powershell
winget search --source winget | Out-File winget.txt
(Get-Content winget.txt).Count
```

> ℹ️ Note: The count includes headers and separators. Subtract ~2–3 lines if you want a “pure” package count.

---

## 🍫 Chocolatey

Chocolatey has a built-in count mechanism via `list`.

### Count all community packages

```powershell
choco list --limit-output | Measure-Object -Line
```

### Explicitly specify the community repository

```powershell
choco list -r | Measure-Object -Line
```

**What this does**

* `--limit-output` or `-r` ensures one line per package
* Output is already normalized → very accurate count

---

## 🪓 Scoop

Scoop packages live in **buckets**, so counts are bucket-based.

### List installed buckets

```powershell
scoop bucket list
```

### Count packages in a specific bucket

Example: `main`

```powershell
scoop search | Measure-Object -Line
```

### Count packages per bucket (precise)

```powershell
Get-ChildItem ~/scoop/buckets/main/bucket/*.json | Measure-Object
```

Repeat for other buckets:

```powershell
Get-ChildItem ~/scoop/buckets/extras/bucket/*.json | Measure-Object
Get-ChildItem ~/scoop/buckets/versions/bucket/*.json | Measure-Object
```

### Total Scoop package count (all buckets)

```powershell
Get-ChildItem ~/scoop/buckets/*/bucket/*.json | Measure-Object
```

**Why this works**

* Each `.json` file = exactly one package manifest
* This is the most accurate Scoop count possible

---

## 📊 Quick Comparison Script (Optional)

If you want a **single PowerShell snippet**:

```powershell
Write-Host "WinGet:" (winget search | Measure-Object -Line).Lines
Write-Host "Chocolatey:" (choco list -r | Measure-Object -Line).Lines
Write-Host "Scoop:" (Get-ChildItem ~/scoop/buckets/*/bucket/*.json | Measure-Object).Count
```

---

## ✅ Accuracy Notes

| Manager        | Accuracy  | Notes                       |
| -------------- | --------- | --------------------------- |
| **WinGet**     | Very good | Includes some metadata rows |
| **Chocolatey** | Excellent | One line per package        |
| **Scoop**      | Exact     | Files = packages            |

---

If you’d like, I can:

* Normalize counts (remove headers automatically)
* Break counts down by **publisher / category**
* Compare **overlap** between WinGet, Choco, and Scoop
* Help you decide which ecosystem best matches your “Debian-like GUI apt” goal

Just tell me 👍
