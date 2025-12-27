# Plan: Installed Packages Metadata Cache

**Status:** Planning
**Created:** 2025-12-27
**Priority:** High
**Estimated Effort:** 4-6 hours

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

### Phase 1: Database Schema Extension (1 hour)

**File:** `metadata/cache/service.py`

1. **Add columns to `packages` table:**
   ```sql
   ALTER TABLE packages ADD COLUMN is_installed BOOLEAN DEFAULT 0;
   ALTER TABLE packages ADD COLUMN installed_version TEXT;
   ALTER TABLE packages ADD COLUMN install_date TEXT;
   ```

2. **Create index for fast installed queries:**
   ```sql
   CREATE INDEX idx_packages_installed ON packages(is_installed, manager);
   ```

3. **Update `PackageMetadata` dataclass:**
   ```python
   @dataclass
   class PackageMetadata:
       # ... existing fields ...
       is_installed: bool = False
       installed_version: Optional[str] = None
       install_date: Optional[str] = None
   ```

4. **Add migration logic** to update existing databases

### Phase 2: Installed Packages Providers (2-3 hours)

**New File:** `metadata/providers/installed_provider.py`

1. **Create base class:**
   ```python
   class InstalledPackagesProvider(ABC):
       """Base class for syncing installed package state."""

       @abstractmethod
       def fetch_installed_packages(self) -> List[InstalledPackageInfo]:
           """Query package manager for installed packages."""
           pass

       def sync_installed_state(self, cache: MetadataCacheService):
           """Update cache with installed package state."""
           # 1. Get installed packages from package manager
           # 2. Mark packages as installed in cache
           # 3. Update installed_version
           pass
   ```

2. **Implement for each manager:**
   - `WinGetInstalledProvider` - uses `winget list` output
   - `ChocolateyInstalledProvider` - uses `choco list --local-only`
   - `PipInstalledProvider` - uses `pip list --format=json`
   - `NPMInstalledProvider` - uses `npm list -g --json`

3. **Reuse existing parsing logic** from `PackageManagerService`

### Phase 3: MetadataCacheService Extensions (1 hour)

**File:** `metadata/cache/service.py`

1. **Add method to sync installed state:**
   ```python
   def sync_installed_packages(self, manager: str, force: bool = False):
       """Sync installed package state for a specific manager."""
       provider = self._get_installed_provider(manager)
       provider.sync_installed_state(self)
   ```

2. **Add method to query installed packages:**
   ```python
   def get_installed_packages(self, managers: Optional[List[str]] = None) -> List[PackageMetadata]:
       """Get all installed packages, optionally filtered by manager."""
       query = "SELECT * FROM packages WHERE is_installed = 1"
       if managers:
           placeholders = ','.join('?' * len(managers))
           query += f" AND manager IN ({placeholders})"
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

### Phase 4: UI Integration (1 hour)

**File:** `ui/views/main_window.py`

1. **Update `refresh_packages()` for Installed mode:**
   ```python
   if self.current_source == 'installed':
       if managers is None:
           # All Packages - sync all managers
           self.sync_all_installed_packages()
       else:
           # Single manager tab
           manager_name = managers[0]
           self.metadata_cache.sync_installed_packages(manager_name, force=True)

       # Query cache for installed packages
       installed = self.metadata_cache.get_installed_packages(managers)
       self.package_table.set_packages([m.to_package() for m in installed])
   ```

2. **Add background sync worker:**
   ```python
   class InstalledPackagesSyncWorker(QThread):
       """Background worker to sync installed package state."""
       # Similar to PackageListWorker but calls cache.sync_installed_packages()
   ```

3. **Update install/uninstall handlers** to update cache:
   ```python
   def on_install_complete(self, result):
       if result.success:
           # Mark package as installed in cache
           self.metadata_cache.mark_as_installed(
               result.package_id,
               result.manager,
               result.version
           )
           # Refresh view
           self.refresh_packages()
   ```

### Phase 5: Auto-Refresh & Optimization (1 hour)

1. **Add background sync on startup:**
   - Sync installed state when app launches (if cache is stale)
   - Show progress in status bar

2. **Add "Refresh Installed" menu item:**
   - Under Config menu: "Refresh Installed Packages"
   - Forces re-sync of all managers

3. **Cache staleness detection:**
   - Track `last_sync` timestamp per manager
   - Auto-refresh if older than 1 hour

4. **Optimize for large package lists:**
   - Use batch SQL inserts
   - Show progress during sync

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
│   ├── service.py              # MetadataCacheService (MODIFY)
│   └── schema.py               # Database schema (MODIFY)
├── providers/
│   ├── base.py                 # BaseProvider (existing)
│   ├── winget_provider.py      # WinGetProvider (existing)
│   ├── chocolatey_provider.py  # ChocolateyProvider (existing)
│   └── installed_provider.py   # NEW: InstalledPackagesProvider classes
└── models.py                   # PackageMetadata (MODIFY)

ui/
├── workers/
│   └── package_worker.py       # Add InstalledPackagesSyncWorker
└── views/
    └── main_window.py          # Update refresh_packages() logic
```

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
| 2025-12-27 | Create separate `InstalledPackagesProvider` classes | Separation of concerns, reuses existing package manager parsing logic |

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
