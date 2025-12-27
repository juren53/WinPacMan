# Plan: Installed Packages Metadata Cache

**Status:** Planning
**Created:** 2025-12-27
**Updated:** 2025-12-27 (Registry-based approach)
**Priority:** High
**Estimated Effort:** 3-4 hours (reduced from 4-6 hours due to registry approach)

---

## Problem Statement

Currently, WinPacMan handles **available** packages and **installed** packages differently:

- **Available Packages:** Cached in SQLite database (`metadata_cache.db`) with fast search, indexed by package manager
- **Installed Packages:** Queried directly from package managers each time (slow, requires shell execution)

When users select "Installed" + "All Packages" tab, the system only shows WinGet packages because there's no unified way to aggregate installed packages from multiple sources.

**User Expectation:** "All Packages" should show packages from **all** installed package managers, regardless of source type (installed vs available).

---

## Core Architectural Principle

> **"A common data structure for all packages is a common theme we should stick to."**

We should treat installed package metadata the same way we treat available package metadata:
- Use the **metadata cache** (`MetadataCacheService`) as the single source of truth
- Store installed package state alongside available package metadata
- Query from cache instead of invoking package managers repeatedly

---

## Current Architecture

### Available Packages Flow:
```
User searches → MetadataCacheService → SQLite query → Results displayed
                      ↑
                      |
           WinGetProvider syncs metadata
           ChocolateyProvider syncs metadata
```

### Installed Packages Flow (Current - Inefficient):
```
User clicks Refresh → PackageListWorker → Shell command (winget list) → Parse output → Display
                                       ↓
                                   Slow, no caching, no cross-manager aggregation
```

---

## Proposed Solution: Unified Metadata Cache Architecture

### New Architecture:
```
┌─────────────────────────────────────────────────────────────────┐
│                   MetadataCacheService                          │
│                                                                 │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │ Available Pkgs   │         │ Installed Pkgs   │             │
│  │ (remote repos)   │         │ (local system)   │             │
│  └──────────────────┘         └──────────────────┘             │
│           ↓                            ↓                        │
│  ┌────────────────────────────────────────────────────┐        │
│  │           SQLite Database (metadata_cache.db)      │        │
│  │                                                     │        │
│  │  packages table:                                   │        │
│  │    - package_id                                    │        │
│  │    - name                                          │        │
│  │    - version                                       │        │
│  │    - manager (winget/chocolatey/pip/npm)           │        │
│  │    - is_installed (NEW: boolean flag)              │        │
│  │    - installed_version (NEW: nullable)             │        │
│  │    - last_sync (timestamp)                         │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Key Changes:
1. **Add `is_installed` column** to `packages` table (boolean)
2. **Add `installed_version` column** to track version of installed package
3. **Add `InstalledPackagesProvider`** classes for each package manager
4. **Sync installed state** periodically or on-demand

---

## Registry-Based Discovery: Performance Breakthrough

**Key Insight:** Windows Registry scanning is **10-20x faster** than invoking package managers via shell commands.

### Performance Comparison

| Method | Time | Completeness | Accuracy |
|--------|------|--------------|----------|
| **Registry Scan (Tier 1)** | 1-2 seconds | 80-90% | "Best guess" |
| **Manager Validation (Tier 2)** | +0.5 seconds | 100% | Definitive |
| **Total (Hybrid)** | **1.5-2.5 seconds** | **100%** | **100%** |
| ~~Shell Commands (Old Plan)~~ | ~~11-20 seconds~~ | ~~100%~~ | ~~100%~~ |

### Why Registry Approach is Superior

1. **Single API Call** - One registry scan captures all installers (WinGet, Chocolatey, manual .exe/.msi)
2. **No Shell Overhead** - No process spawning, no output parsing, no timeouts
3. **Rich Metadata** - Registry provides DisplayName, Version, InstallLocation, Publisher, InstallDate
4. **Existing Code** - `_get_winget_install_location()` already implements registry scanning (lines 795-1177)
5. **Completeness** - Catches apps installed manually (not tracked by any package manager)

### Fingerprint Detection Strategy

The registry doesn't explicitly tag which package manager installed an app, but managers leave "fingerprints":

- **WinGet:** `InstallSource` contains `"winget"` or `"appinstaller"` in path
- **Chocolatey:** `InstallLocation` contains `"chocolatey"` or `"choco"` in path
- **Scoop:** Doesn't use registry (scan `%USERPROFILE%\scoop\apps` instead)
- **MS Store:** `InstallLocation` contains `"WindowsApps"` in path
- **Manual:** No fingerprint → fallback category

**Validation Layer:** Cross-reference with WinGet `installed.db` and Chocolatey `.chocolatey` metadata for 100% accuracy.

---

## Benefits of This Approach

### 1. **Consistency**
- Same `Package` data model for installed and available
- Same search/filter logic for both sources
- Same metadata cache infrastructure

### 2. **Performance**
- No shell execution for searches/filters
- SQLite queries are instant
- Cached results, refresh on-demand

### 3. **Cross-Manager Aggregation**
- "All Packages" tab naturally shows all installed packages
- Single query: `SELECT * FROM packages WHERE is_installed = 1`
- Easy to filter: `... AND manager IN ('winget', 'chocolatey')`

### 4. **Rich Metadata**
- Installed packages get same metadata as available (description, tags, etc.)
- Can show "Update Available" by comparing `installed_version` vs `version`
- Can track installation history

### 5. **Offline Capability**
- View installed packages without network
- Fast filtering and search

---

## Implementation Plan

**Updated Strategy:** Use Windows Registry scanning as the primary detection method (10-20x faster than invoking package managers), with manager-specific validation as an accuracy layer.

### Discovery Strategy: 3-Tier Hybrid Approach

#### **Tier 1: Registry Scan (Fast Path - 1-2 seconds)**
- Scan Windows Registry `Uninstall` keys
- Use fingerprint detection (InstallSource paths, directory patterns)
- Captures 80-90% of installed apps instantly
- Includes apps installed manually via `.exe`/`.msi`

#### **Tier 2: Manager-Specific Discovery (Accuracy Layer)**
- **WinGet:** Query `installed.db` SQLite database
- **Chocolatey:** Check `C:\ProgramData\chocolatey\.chocolatey` metadata
- **Scoop:** Scan `%USERPROFILE%\scoop\apps` directories
- **MS Store:** Check `AppModel\Repository\Packages` registry key
- Cross-reference with Tier 1 for definitive manager attribution

#### **Tier 3: Metadata Enrichment (Optional)**
- Cross-reference with metadata cache for descriptions, tags
- For "Manual/Unknown" apps, use registry DisplayName

---

### Phase 1: Database Schema Extension (1 hour)

**File:** `metadata/cache/service.py`

1. **Add columns to `packages` table:**
   ```sql
   ALTER TABLE packages ADD COLUMN is_installed BOOLEAN DEFAULT 0;
   ALTER TABLE packages ADD COLUMN installed_version TEXT;
   ALTER TABLE packages ADD COLUMN install_date TEXT;
   ALTER TABLE packages ADD COLUMN install_source TEXT;  -- NEW: "winget", "chocolatey", "manual", etc.
   ALTER TABLE packages ADD COLUMN install_location TEXT; -- NEW: Physical path on disk
   ```

2. **Create index for fast installed queries:**
   ```sql
   CREATE INDEX idx_packages_installed ON packages(is_installed, manager);
   CREATE INDEX idx_packages_source ON packages(install_source);
   ```

3. **Update `PackageMetadata` dataclass:**
   ```python
   @dataclass
   class PackageMetadata:
       # ... existing fields ...
       is_installed: bool = False
       installed_version: Optional[str] = None
       install_date: Optional[str] = None
       install_source: Optional[str] = None  -- "winget", "chocolatey", "manual", "scoop", etc.
       install_location: Optional[str] = None
   ```

4. **Add migration logic** to update existing databases

### Phase 2: Registry-Based Installed Provider (2-3 hours)

**New File:** `metadata/providers/installed_registry_provider.py`

**Key Insight:** Reuse existing registry scanning logic from `ui/views/main_window.py` (`_get_winget_install_location()` method, lines 795-1177).

1. **Create `InstalledRegistryProvider` class:**
   ```python
   class InstalledRegistryProvider:
       """Fast installed packages discovery via Windows Registry."""

       REGISTRY_PATHS = [
           (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
           (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
           (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
       ]

       def scan_registry(self) -> List[PackageMetadata]:
           """Scan all registry uninstall keys for installed apps."""
           packages = []
           for hive, path in self.REGISTRY_PATHS:
               packages.extend(self._scan_registry_key(hive, path))
           return packages

       def _scan_registry_key(self, hive, path) -> List[PackageMetadata]:
           """Scan a single registry key for installed apps."""
           # Iterate through subkeys
           # Extract: DisplayName, DisplayVersion, InstallLocation, InstallSource, Publisher, InstallDate
           # Call detect_manager() to determine source
           pass

       def detect_manager(self, install_source: str, install_location: str,
                         display_name: str) -> str:
           """
           Fingerprint detection based on paths.

           Detection Rules:
           - If InstallSource contains "winget" or "appinstaller" → "winget"
           - If InstallLocation/InstallSource contains "chocolatey" or "choco" → "chocolatey"
           - If InstallLocation contains "scoop" → "scoop"
           - If InstallLocation contains "windowsapps" → "msstore"
           - Otherwise → "manual"
           """
           install_source = (install_source or "").lower()
           install_location = (install_location or "").lower()
           display_name = (display_name or "").lower()

           # WinGet detection
           if "winget" in install_source or "appinstaller" in install_source:
               return "winget"

           # Chocolatey detection
           if "chocolatey" in install_location or "chocolatey" in install_source:
               return "chocolatey"
           if "choco" in install_source:
               return "chocolatey"

           # Scoop detection (usually in user profile)
           if "scoop" in install_location or "scoop" in install_source:
               return "scoop"

           # MS Store detection
           if "windowsapps" in install_location:
               return "msstore"

           return "manual"
   ```

2. **Create `ScoopInstalledProvider` class:**
   ```python
   class ScoopInstalledProvider:
       """Scoop-specific provider (doesn't use registry)."""

       def get_scoop_apps(self) -> List[PackageMetadata]:
           """
           Scan %USERPROFILE%\scoop\apps for installed Scoop packages.

           Scoop structure:
           - C:\Users\<user>\scoop\apps\<app_name>\current\ (symlink to version)
           - manifest.json contains version and metadata
           """
           scoop_path = os.path.expandvars(r"%USERPROFILE%\scoop\apps")
           if not os.path.exists(scoop_path):
               return []

           packages = []
           for app_name in os.listdir(scoop_path):
               app_dir = os.path.join(scoop_path, app_name)
               current_dir = os.path.join(app_dir, "current")

               if os.path.exists(current_dir):
                   manifest_path = os.path.join(current_dir, "manifest.json")
                   version = "Unknown"

                   if os.path.exists(manifest_path):
                       with open(manifest_path, 'r') as f:
                           data = json.load(f)
                           version = data.get("version", "Unknown")

                   packages.append(PackageMetadata(
                       package_id=app_name,
                       name=app_name,
                       version=version,
                       manager="scoop",
                       is_installed=True,
                       installed_version=version,
                       install_location=current_dir,
                       install_source="scoop"
                   ))

           return packages
   ```

3. **Refactor existing code:**
   - Extract registry scanning logic from `_get_winget_install_location()` in `ui/views/main_window.py`
   - Move to reusable provider class
   - Remove duplication

### Phase 3: Manager-Specific Validation Providers (1 hour)

**Purpose:** Cross-reference registry fingerprints with definitive manager databases for 100% accuracy.

**New File:** `metadata/providers/installed_validation_provider.py`

1. **Create `WinGetValidationProvider` class:**
   ```python
   class WinGetValidationProvider:
       """Validates WinGet installations via installed.db SQLite database."""

       def __init__(self):
           # WinGet database location
           self.db_path = os.path.expandvars(
               r"%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe"
               r"\LocalState\installed.db"
           )

       def get_installed_package_ids(self) -> Set[str]:
           """Query WinGet's installed.db for definitive installed package list."""
           if not os.path.exists(self.db_path):
               return set()

           # Query WinGet SQLite database
           # Return set of package IDs confirmed by WinGet
           pass

       def validate(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
           """
           Validate manager attribution for packages.

           If registry fingerprint says "winget" but package ID not in installed.db,
           change to "manual".
           """
           winget_ids = self.get_installed_package_ids()
           for pkg in packages:
               if pkg.install_source == "winget" and pkg.package_id not in winget_ids:
                   pkg.install_source = "manual"  # Fingerprint was wrong
           return packages
   ```

2. **Create `ChocolateyValidationProvider` class:**
   ```python
   class ChocolateyValidationProvider:
       """Validates Chocolatey installations via .chocolatey metadata folder."""

       def __init__(self):
           self.metadata_path = r"C:\ProgramData\chocolatey\.chocolatey"

       def get_installed_package_ids(self) -> Set[str]:
           """Scan .chocolatey folder for installed package names."""
           if not os.path.exists(self.metadata_path):
               return set()

           # Each installed Chocolatey package has a folder here
           # Folder name = package ID
           return set(os.listdir(self.metadata_path))

       def validate(self, packages: List[PackageMetadata]) -> List[PackageMetadata]:
           """Validate Chocolatey attribution."""
           choco_ids = self.get_installed_package_ids()
           for pkg in packages:
               if pkg.install_source == "chocolatey" and pkg.package_id not in choco_ids:
                   pkg.install_source = "manual"
           return packages
   ```

### Phase 4: MetadataCacheService Extensions (1 hour)

**File:** `metadata/cache/service.py`

1. **Add method to sync installed state via registry:**
   ```python
   def sync_installed_packages_from_registry(self, validate: bool = True):
       """
       Sync installed package state from Windows Registry.

       Args:
           validate: If True, cross-reference with manager-specific databases
       """
       # Tier 1: Registry scan
       registry_provider = InstalledRegistryProvider()
       packages = registry_provider.scan_registry()

       # Add Scoop packages (not in registry)
       scoop_provider = ScoopInstalledProvider()
       packages.extend(scoop_provider.get_scoop_apps())

       # Tier 2: Validation (optional)
       if validate:
           winget_validator = WinGetValidationProvider()
           packages = winget_validator.validate(packages)

           choco_validator = ChocolateyValidationProvider()
           packages = choco_validator.validate(packages)

       # Store in cache
       self._update_installed_state(packages)
   ```

2. **Add method to query installed packages:**
   ```python
   def get_installed_packages(self, managers: Optional[List[str]] = None,
                              source: Optional[str] = None) -> List[PackageMetadata]:
       """
       Get all installed packages, optionally filtered by manager or source.

       Args:
           managers: Filter by package manager (winget, chocolatey, etc.)
           source: Filter by install source (winget, chocolatey, manual, scoop, msstore)
       """
       query = "SELECT * FROM packages WHERE is_installed = 1"

       if managers:
           placeholders = ','.join('?' * len(managers))
           query += f" AND manager IN ({placeholders})"

       if source:
           query += f" AND install_source = ?"

       # ... execute and return results
   ```

3. **Add method to check if package is installed:**
   ```python
   def is_package_installed(self, package_id: str, manager: str) -> bool:
       """Check if a specific package is installed."""
       query = """
           SELECT is_installed FROM packages
           WHERE package_id = ? AND manager = ?
       """
       # ... execute and return result
   ```

4. **Add method to update installed state:**
   ```python
   def _update_installed_state(self, packages: List[PackageMetadata]):
       """
       Update cache with installed package state.

       Strategy:
       - Clear all is_installed flags
       - Insert/update packages from registry scan
       - Mark as installed
       """
       # Clear existing installed flags
       self.db.execute("UPDATE packages SET is_installed = 0")

       # Insert or update packages
       for pkg in packages:
           # Try to find existing package in cache by ID
           existing = self._find_package(pkg.package_id, pkg.install_source)

           if existing:
               # Update existing package
               self.db.execute("""
                   UPDATE packages SET
                       is_installed = 1,
                       installed_version = ?,
                       install_date = ?,
                       install_location = ?
                   WHERE package_id = ? AND manager = ?
               """, (pkg.installed_version, pkg.install_date,
                     pkg.install_location, pkg.package_id, pkg.install_source))
           else:
               # Insert new package (not in available repos)
               self.db.execute("""
                   INSERT INTO packages (package_id, name, version, manager,
                                        is_installed, installed_version,
                                        install_date, install_source, install_location)
                   VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
               """, (pkg.package_id, pkg.name, pkg.version,
                     pkg.install_source, pkg.installed_version,
                     pkg.install_date, pkg.install_source, pkg.install_location))
   ```

### Phase 5: UI Integration (1 hour)

**File:** `ui/views/main_window.py`

1. **Update `refresh_packages()` for Installed mode:**
   ```python
   if self.current_source == 'installed':
       # Sync installed packages from registry (fast!)
       self.metadata_cache.sync_installed_packages_from_registry(validate=True)

       # Query cache for installed packages
       managers_filter = self.get_active_managers()
       installed = self.metadata_cache.get_installed_packages(managers=managers_filter)

       # Convert to Package objects and display
       packages = [m.to_package() for m in installed]
       self.package_table.set_packages(packages)

       # Update status
       self.status_label.setText(
           f"Loaded {len(packages)} installed packages from registry"
       )
   ```

2. **Add background sync worker (optional for async):**
   ```python
   class InstalledPackagesSyncWorker(QThread):
       """Background worker to sync installed package state from registry."""

       signals = WorkerSignals()

       def __init__(self, cache: MetadataCacheService):
           super().__init__()
           self.cache = cache

       def run(self):
           try:
               self.signals.started.emit()
               self.cache.sync_installed_packages_from_registry(validate=True)
               self.signals.finished.emit()
           except Exception as e:
               self.signals.error_occurred.emit(str(e))
   ```

3. **Update install/uninstall handlers** to refresh cache:
   ```python
   def on_install_complete(self, result):
       if result.success:
           # Re-sync registry to pick up new installation
           # (Fast operation - only takes 1-2 seconds)
           self.metadata_cache.sync_installed_packages_from_registry(validate=True)

           # Refresh view if in Installed mode
           if self.current_source == 'installed':
               self.refresh_packages()

   def on_uninstall_complete(self, result):
       if result.success:
           # Re-sync registry to remove uninstalled package
           self.metadata_cache.sync_installed_packages_from_registry(validate=True)

           # Refresh view if in Installed mode
           if self.current_source == 'installed':
               self.refresh_packages()
   ```

4. **Add "Source" column to package table:**
   ```python
   # In PackageTableWidget initialization
   self.setColumnCount(7)  # Add one more column
   self.setHorizontalHeaderLabels([
       "Name", "Version", "Manager", "Source", "Description", "Status", "ID"
   ])

   # In set_packages() method
   source_item = QTableWidgetItem(package.install_source or "available")
   self.setItem(row, 3, source_item)
   ```

5. **Add filter by source (optional enhancement):**
   ```python
   # In UI, add dropdown to filter by source
   source_filter = QComboBox()
   source_filter.addItems(["All", "WinGet", "Chocolatey", "Manual", "Scoop", "MS Store"])
   source_filter.currentTextChanged.connect(self.on_source_filter_changed)

   def on_source_filter_changed(self, source: str):
       """Filter installed packages by install source."""
       if source == "All":
           source_filter = None
       else:
           source_filter = source.lower()

       installed = self.metadata_cache.get_installed_packages(
           managers=self.get_active_managers(),
           source=source_filter
       )
       self.package_table.set_packages([m.to_package() for m in installed])
   ```

### Phase 6: Auto-Refresh & Optimization (30 min)

1. **Add background sync on startup:**
   ```python
   def __init__(self):
       # ... existing init code ...

       # Sync installed packages on startup (background)
       QTimer.singleShot(1000, self._sync_installed_on_startup)

   def _sync_installed_on_startup(self):
       """Sync installed packages in background on startup."""
       # Check if cache is stale (> 1 hour old)
       last_sync = self.metadata_cache.get_last_sync_time('installed')

       if not last_sync or (time.time() - last_sync) > 3600:
           # Run sync in background
           worker = InstalledPackagesSyncWorker(self.metadata_cache)
           worker.signals.finished.connect(
               lambda: self.status_label.setText("Installed packages cache updated")
           )
           worker.start()
   ```

2. **Add "Refresh Installed Cache" menu item:**
   ```python
   # In create_menu_bar()
   config_menu.addSeparator()
   refresh_installed_action = QAction("Refresh Installed Packages Cache", self)
   refresh_installed_action.triggered.connect(self.refresh_installed_cache)
   config_menu.addAction(refresh_installed_action)

   def refresh_installed_cache(self):
       """Manually refresh installed packages cache from registry."""
       reply = QMessageBox.question(
           self, "Refresh Cache",
           "Re-scan Windows Registry for installed packages?",
           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
       )

       if reply == QMessageBox.StandardButton.Yes:
           self.metadata_cache.sync_installed_packages_from_registry(validate=True)
           QMessageBox.information(self, "Success", "Installed packages cache refreshed!")
   ```

3. **Cache staleness detection:**
   - Add `last_sync_installed` timestamp to metadata cache
   - Auto-refresh if older than 1 hour (configurable)

4. **Performance optimization:**
   - Registry scan already uses batch SQL operations
   - No additional optimization needed (1-2 second sync time)

---

## Testing Strategy

### Unit Tests:
1. Test schema migration on existing databases
2. Test installed package provider parsing
3. Test cache query methods (get_installed_packages, etc.)

### Integration Tests:
1. Test sync with real package managers (WinGet, Chocolatey)
2. Test install/uninstall updating cache state
3. Test "All Packages" aggregation

### Manual Testing:
1. Install a package → verify cache updates
2. Uninstall a package → verify cache updates
3. Switch between Installed/Available → verify correct data shown
4. Test with 0 packages, 100 packages, 1000+ packages

---

## Migration Path

### For Existing Users:
1. **First launch after update:**
   - Detect new schema version
   - Run migration to add `is_installed`, `installed_version` columns
   - Show dialog: "Refreshing installed packages cache..."
   - Sync all managers in background

2. **No data loss:**
   - Existing `packages` table preserved
   - New columns added with default values
   - Gradual sync on first use

---

## Future Enhancements

### 1. Update Detection
- Compare `installed_version` vs `version` (available)
- Show "Update Available" badge in table
- Add "Update All" button

### 2. Installation History
- New table: `installation_history`
- Track when packages were installed/uninstalled
- Show timeline view

### 3. Dependency Tracking
- Store package dependencies in cache
- Show dependency tree before install/uninstall

### 4. Portable Mode
- Export/import installed package list
- "Install on new machine" feature

---

## File Structure

```
metadata/
├── cache/
│   ├── service.py                      # MetadataCacheService (MODIFY)
│   │                                   # Add: sync_installed_packages_from_registry()
│   │                                   #      get_installed_packages()
│   │                                   #      _update_installed_state()
│   └── schema.py                       # Database schema (MODIFY)
│                                       # Add: is_installed, installed_version,
│                                       #      install_date, install_source, install_location
├── providers/
│   ├── base.py                         # BaseProvider (existing)
│   ├── winget_provider.py              # WinGetProvider (existing)
│   ├── chocolatey_provider.py          # ChocolateyProvider (existing)
│   ├── installed_registry_provider.py  # NEW: InstalledRegistryProvider
│   │                                   # NEW: ScoopInstalledProvider
│   └── installed_validation_provider.py # NEW: WinGetValidationProvider
│                                        # NEW: ChocolateyValidationProvider
└── models.py                           # PackageMetadata (MODIFY)

ui/
├── workers/
│   └── package_worker.py               # Add: InstalledPackagesSyncWorker
├── views/
│   └── main_window.py                  # MODIFY: refresh_packages() logic
│                                       # REFACTOR: Extract registry code from
│                                       #           _get_winget_install_location()
└── components/
    └── package_table.py                # MODIFY: Add "Source" column

notes/
└── Windows_Registry_and_Package_Managers.md  # Reference for fingerprint detection
```

**Key Refactoring:**
- Extract registry scanning logic from `ui/views/main_window.py` (`_get_winget_install_location()`)
- Move to reusable `InstalledRegistryProvider` class
- Remove code duplication

---

## Risks & Mitigation

### Risk 1: Performance with Large Package Lists
- **Mitigation:** Use batch inserts, indexed queries, pagination
- **Threshold:** Test with 10,000+ packages

### Risk 2: Package Manager Output Format Changes
- **Mitigation:** Reuse existing robust parsing from `PackageManagerService`
- **Fallback:** If sync fails, fall back to direct query

### Risk 3: Stale Cache
- **Mitigation:** Show cache age in UI, easy refresh button
- **Auto-refresh:** Background sync on startup if cache > 1 hour old

### Risk 4: Disk Space
- **Mitigation:** Cache is small (few MB even for thousands of packages)
- **Cleanup:** Add cache size limit, auto-prune old entries

---

## Success Metrics

1. **Functionality:**
   - ✅ "All Packages" + "Installed" shows packages from all managers
   - ✅ Search/filter works on installed packages
   - ✅ Install/uninstall updates cache in real-time

2. **Performance:**
   - ✅ Installed package list loads in < 1 second (vs 5-10 seconds with shell commands)
   - ✅ Search filters installed packages instantly

3. **User Experience:**
   - ✅ Users understand they're viewing cached data (show sync time)
   - ✅ Manual refresh works reliably
   - ✅ No confusion between installed/available

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-27 | Use metadata cache for installed packages | Consistency with available packages, better performance, enables cross-manager aggregation |
| 2025-12-27 | Add `is_installed` flag to existing `packages` table | Avoids data duplication, enables rich queries (e.g., "show installed packages with updates available") |
| 2025-12-27 | **Registry-based discovery as primary method** | **10-20x faster than shell commands (1-2 seconds vs 11-20 seconds), captures manual installs, reuses existing code** |
| 2025-12-27 | 3-tier hybrid approach (Registry + Validation + Cache) | Balances speed (registry scan) with accuracy (manager DB validation) |
| 2025-12-27 | Add `install_source` field separate from `manager` | Enables distinguishing "installed via WinGet" vs "available in WinGet" vs "manual install" |

---

## Open Questions

1. **Should we cache installed package metadata even if not in available repos?**
   - Example: User manually installs a local `.msi` that's not in WinGet repo
   - **Answer:** Yes - create minimal metadata entry with is_installed=true

2. **How often should we auto-refresh installed state?**
   - **Proposal:** On startup (if > 1 hour old), after install/uninstall operations, manual refresh

3. **Should we persist "Available" package list or only "Installed"?**
   - **Current:** Both are persisted (available packages already cached)
   - **Benefit:** Offline capability for both modes

---

## References

- Current metadata cache: `metadata/cache/service.py`
- Package models: `core/models.py`, `metadata/models.py`
- UI implementation: `ui/views/main_window.py`
- Existing providers: `metadata/sync/winget_provider.py`, `metadata/sync/chocolatey_odata_fetcher.py`

---

**Next Steps:**
1. Review this plan with stakeholders
2. Create feature branch: `feature/installed-packages-cache`
3. Implement Phase 1 (Database Schema Extension)
4. Test migration on existing database
5. Proceed with subsequent phases
