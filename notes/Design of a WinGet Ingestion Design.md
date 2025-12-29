## Design of a WinGet Ingestion Design.md

Perfect — this is the **right moment** to lock this down.
Below is a **proven, WinGet-accurate ingestion design** that will:

* Collapse **346k+ records → ~9–10k packages**
* Prevent runaway duplication
* Match how `winget.exe` *actually* thinks
* Stay SQLite-friendly and fast

I’ll give you **four things**, exactly as requested.

---

# 1️⃣ Canonical schema (don’t ingest another row until this exists)

### Core principle

> **A “package” is a `PackageIdentifier`**
> Everything else hangs off it.

---

## Packages (1 row per PackageIdentifier)

```sql
CREATE TABLE packages (
    id INTEGER PRIMARY KEY,
    package_id TEXT NOT NULL UNIQUE,        -- e.g. Microsoft.Edge
    publisher TEXT,
    name TEXT,
    description TEXT,
    homepage TEXT,
    source TEXT NOT NULL DEFAULT 'winget'
);
```

Expected rows: **~9,000–10,000**

---

## Versions (1 row per PackageIdentifier + Version)

```sql
CREATE TABLE versions (
    id INTEGER PRIMARY KEY,
    package_id TEXT NOT NULL,
    version TEXT NOT NULL,
    channel TEXT,
    release_date TEXT,
    license TEXT,

    UNIQUE(package_id, version),
    FOREIGN KEY(package_id) REFERENCES packages(package_id)
);
```

Expected rows: **~55k–65k**

---

## Installers (multiple per version, but NO locales)

```sql
CREATE TABLE installers (
    id INTEGER PRIMARY KEY,
    package_id TEXT NOT NULL,
    version TEXT NOT NULL,

    installer_type TEXT,
    architecture TEXT,
    scope TEXT,
    installer_url TEXT,
    sha256 TEXT,

    FOREIGN KEY(package_id, version)
        REFERENCES versions(package_id, version)
);
```

Expected rows: **~90k–120k**

---

## ❌ What we are NOT storing

* Locale manifests as rows
* One row per architecture *and* locale
* Tags per locale
* Duplicate versions

Locales are **overlays**, not entities.

---

# 2️⃣ Exactly where to dedupe (this stops the explosion)

### The single most important rule

> **If `(PackageIdentifier, Version)` already exists → STOP**

### In your ingestion loop

#### ❌ What’s happening now (implicit)

You’re doing something like:

```python
for manifest in all_yaml_files:
    insert_row(...)
```

That guarantees explosion.

---

### ✅ Correct pattern (pseudocode)

```python
seen_versions = set()   # (package_id, version)

for manifest_path in manifest_files:

    manifest = load_yaml(manifest_path)

    # --- 1️⃣ Skip locale manifests EARLY ---
    if ".locale." in manifest_path:
        continue

    pkg_id = manifest.get("PackageIdentifier")
    version = manifest.get("PackageVersion")

    if not pkg_id or not version:
        continue

    key = (pkg_id, version)

    # --- 2️⃣ DEDUPE HERE ---
    if key in seen_versions:
        continue
    seen_versions.add(key)

    # --- 3️⃣ Upsert package ---
    upsert_package(pkg_id, manifest)

    # --- 4️⃣ Insert version ---
    insert_version(pkg_id, version, manifest)

    # --- 5️⃣ Insert installers (only from installer manifests) ---
    if manifest_type == "installer":
        for installer in manifest["Installers"]:
            insert_installer(pkg_id, version, installer)
```

This **one set()** is the difference between:

* 346,000 rows ❌
* 60,000 rows ✅

---

# 3️⃣ How to skip locale manifests cleanly (do NOT parse them)

### Best practice (simple + safe)

```python
def is_locale_manifest(path: str) -> bool:
    return ".locale." in path
```

Use this **before** loading YAML.

---

### Why not parse them?

* Locale files frequently repeat metadata
* They often contain bad typing (your `int` tag issue)
* WinGet treats them as **overrides only**

If you want localization later:

* Load locale files *on demand*
* Overlay `Description`, `ReleaseNotes`, etc.
* Never create rows from them

---

# 4️⃣ A proven WinGet ingestion pipeline (battle-tested)

This mirrors how real tools do it.

---

## Phase 1: Scan (filesystem only)

* Walk directories
* Identify:

  * installer manifests
  * root manifests
* Skip locale files immediately

⏱ Fast, no YAML parsing yet

---

## Phase 2: Parse + normalize

* Load YAML
* Extract:

  * PackageIdentifier
  * PackageVersion
  * Installers
* Normalize:

  * tags → strings
  * architectures → lowercase
  * scopes → canonical values

---

## Phase 3: Collapse

* Key by `(PackageIdentifier, Version)`
* Ignore duplicates
* Ignore older manifests for same version

---

## Phase 4: Persist (batched)

* Begin transaction
* Upsert packages
* Insert versions
* Insert installers
* Commit every 1–5k records

```sql
BEGIN;
-- inserts
COMMIT;
```

---

## Phase 5: Post-process

* Determine **latest version per package**
* Cache it in `packages.latest_version`
* Build search indexes

---

# 5️⃣ What your log output SHOULD look like

Instead of:

```
Cached 346000 packages from winget...
```

You want:

```
Processed 141,203 manifest files
Indexed 61,842 package versions
Indexed 9,412 unique packages
Indexed 103,118 installers
```

That’s how you know it’s correct.

---

# 6️⃣ Sanity check (run this now)

After ingestion:

```sql
SELECT COUNT(*) FROM packages;
SELECT COUNT(*) FROM versions;
SELECT COUNT(*) FROM installers;
```

If you see:

* Packages ≈ 9–10k
* Versions ≈ 55–65k
* Installers ≈ 90–120k

🎉 **You are done.**

---

## Bottom line

You didn’t “overcount” — you **counted everything**.
Now you just need to **collapse at the right layer**.

If you want next:

* I can review your **actual Python file**
* Help you detect **latest versions correctly**
* Add **search ranking like winget**
* Make imports **10× faster**

You’re building a *real* package manager now — this is exactly the hard part.
