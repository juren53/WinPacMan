# Changelog for WinPacMan

All notable changes to WinPacMan are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [0.5.1] - 2025-12-27

### Major Performance Improvement - Registry-Based Installed Packages Discovery

**Achievement:** Implemented Windows Registry scanning for installed package detection with **10-20x performance improvement** over shell command approach.

**Performance Results:**
- **Registry scan speed:** 1-2 seconds (vs 11-20 seconds for shell commands)
- **Total packages found:** 143 packages (138 from registry + 5 from Scoop)
- **Detection accuracy:** Fingerprint-based manager identification
- **Speedup:** 10-20x faster installed package discovery

### Added

#### Registry-Based Package Discovery
- **`metadata/providers/installed_registry_provider.py`** - Fast installed packages provider
  - `InstalledRegistryProvider` class for Windows Registry scanning
  - Scans three registry hives: HKLM, HKLM WOW6432Node, HKCU
  - Extracts: DisplayName, DisplayVersion, InstallLocation, InstallSource, InstallDate, Publisher
  - Fingerprint detection via `detect_manager()` method
  - Performance: ~1-2 seconds for complete system scan

#### Scoop-Specific Provider
- **`ScoopInstalledProvider`** class in `installed_registry_provider.py`
  - Scoop doesn't use Windows Registry (portable design)
  - Scans `%USERPROFILE%\scoop\apps` directory structure
  - Reads `manifest.json` for version and metadata
  - Detects packages via `current` symlink

#### Fingerprint Detection Strategy
Detection rules (in priority order):
1. **WinGet:** InstallSource contains "winget" or "appinstaller"
2. **Chocolatey:** InstallLocation/InstallSource contains "chocolatey" or "choco"
3. **Scoop:** InstallLocation contains "scoop"
4. **MS Store:** InstallLocation contains "WindowsApps"
5. **Unknown:** No fingerprint detected (per user requirement)

#### Database Schema Extensions
- **`metadata/metadata_cache.py`** - Extended for installed package tracking
  - Added columns: `installed_version`, `install_date`, `install_source`, `install_location`
  - `_migrate_schema()` method for backward compatibility
  - Automatic schema upgrade for existing databases
  - Index on `install_source` for performance

#### Data Model Extensions
- **`core/models.py`** - Extended PackageManager enum
  - Added `SCOOP = "scoop"`
  - Added `MSSTORE = "msstore"`
  - Added `UNKNOWN = "unknown"` (for manually installed packages)
  - Extended `UniversalPackageMetadata` with installed package fields

#### Cache Service Methods
- **`metadata/metadata_cache.py`** - New installed packages methods
  - `sync_installed_packages_from_registry()` - Sync from registry scan
  - `get_installed_packages()` - Query cached installed packages
  - `_update_installed_state()` - Update cache with install state
  - Filtering by manager and install source

#### UI Integration
- **`ui/views/main_window.py`** - Replaced shell command approach
  - Refresh now calls `metadata_cache.sync_installed_packages_from_registry()`
  - Displays results from cache query (instant)
  - Shows progress during registry scan

- **`ui/components/package_table.py`** - Display formatting
  - `_format_manager_name()` for proper capitalization
  - Manager column displays: "WinGet", "Chocolatey", "Scoop", "MS Store", "Unknown"
  - Color scheme for new managers (SCOOP, MSSTORE, UNKNOWN)

### Fixed

#### Critical Database Enum Binding Bug
- **Issue:** SQLite `ProgrammingError` when inserting packages
  - Error: "type 'PackageManager' is not supported"
  - PackageManager enum was passed directly to SQLite without conversion
- **Solution:** Convert enum to string value before database operations
  - Changed `pkg.manager` to `pkg.manager.value` (3 instances)
  - Locations: SELECT query, UPDATE query, INSERT query in `_update_installed_state()`
- **Impact:** Registry scan now completes successfully without database errors

### Changed

#### Installed Package Refresh Strategy
- **Before:** Shell commands invoked for each package manager (slow)
- **After:** Single registry scan + Scoop directory scan (fast)
- **UI Behavior:** "Installed" mode now uses registry-based sync

### Validated

#### Registry Scan Test Results
- ✅ **138 packages** discovered from Windows Registry
- ✅ **5 packages** discovered from Scoop directory scan
- ✅ **143 total packages** synced to database
- ✅ **135 packages** displayed after manager filtering
- ✅ **Manager detection working** - winget, chocolatey, scoop, msstore, unknown
- ✅ **Database migration working** - Existing databases auto-upgraded
- ✅ **No errors** - Clean execution with zero exceptions

#### Performance Comparison

| Method | Time | Packages | Status |
|--------|------|----------|--------|
| **Registry Scan (NEW)** | 1-2 seconds | 143 | ✅ 10-20x faster |
| Shell Commands (OLD) | 11-20 seconds | varies | ❌ Deprecated |

### Architecture Benefits

- **Consistency:** Installed packages use same cache architecture as available packages
- **Performance:** Sub-2 second scans vs 10-20 second shell commands
- **Cross-Manager:** Single query aggregates all installed packages
- **Offline:** View installed packages without package manager availability
- **Unified Data:** Same `UniversalPackageMetadata` model for all packages

### Technical Details

**Files Created:**
- `metadata/providers/installed_registry_provider.py` (287 lines)

**Files Modified:**
- `core/models.py` - Extended PackageManager enum, added installed package fields
- `metadata/metadata_cache.py` - Schema migration, sync methods, enum fix
- `ui/views/main_window.py` - Registry-based refresh integration
- `ui/components/package_table.py` - Display formatting for new managers
- `metadata/providers/__init__.py` - Export new providers

**Registry Keys Scanned:**
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`
- `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall`
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall`

### Next Steps

- Add WinGet `installed.db` validation for higher accuracy
- Add Chocolatey `.chocolatey` folder validation
- Implement update detection (compare installed_version vs version)
- Add installation history tracking

---

## [0.5.0-alpha] - 2025-12-27

### Major UX Improvement - Source Clarity (Installed vs Available Packages)

**Issue:** Users were confused about whether they were viewing installed packages (local system) or available packages (remote repositories). No visual indication of package source led to unclear expectations.

**Solution:** Implemented source toggle with clear visual indicators throughout the UI.

### Added

#### Source Toggle Control (`ui/views/main_window.py`)
- **Radio button toggle** at top of window: "Installed" vs "Available"
  - Defaults to "Available" (remote repository search)
  - Tooltips explain each mode clearly
  - Disabled during operations to prevent mode switching mid-operation

#### Clear Status Messages
- **Status bar** now shows: "Viewing: Available packages - WinGet" or "Viewing: Installed packages - WinGet"
- **Search placeholder** updates dynamically: "Search available packages..." or "Search installed packages..."
- **Progress messages** clarify source: "Loading installed packages from WinGet..."

#### Tab-Based Repository Selection
- **Replaced dropdown + checkboxes** with clean tab interface
  - Tabs: "All Packages", "WinGet", "Chocolatey"
  - Shows package counts in tab labels (e.g., "WinGet (8,398)")
  - Scales cleanly for future package managers (Scoop, Pip, NPM, Cargo, etc.)
  - Clear visual hierarchy

#### Smart Behavior Per Source
- **Available Mode (default):**
  - Search → Queries metadata cache (instant results)
  - Refresh → Shows info dialog (cache doesn't need manual refresh)

- **Installed Mode:**
  - Search → Filters already-loaded installed packages locally (instant)
  - Refresh → Calls package manager to list installed packages

#### View Menu Reorganization
- **Moved "Verbose Output"** from control panel checkbox to View menu
  - Checkable menu item with tooltip
  - Cleaner control panel layout
  - Professional menu organization

### Fixed

#### Tab Selector Bug
- **Issue:** Tab labels included package counts (e.g., "WinGet (8,398)"), breaking dictionary lookups
- **Solution:** Changed to index-based lookup instead of text-based lookup
- **Impact:** All tabs now correctly filter packages by selected repository

### Changed

#### UI Architecture (`ui/views/main_window.py`)
- Added `current_source` state variable ('installed' or 'available')
- Created `create_source_toggle()` method for source radio buttons
- Added `on_source_changed()` handler to update UI state
- Updated `on_tab_changed()` to include source context in status
- Modified `search_packages()` to route to appropriate search method based on source
- Added `_search_installed_packages()` for local filtering of installed packages
- Updated `refresh_packages()` to handle source-specific behavior
- Enhanced `disable_controls()` and `enable_controls()` to manage source toggle

---

### Planned - Installed Packages Metadata Cache Architecture

**Status:** Planning (see `PLAN_Installed_Packages_Cache.md`)

**Vision:** Treat installed packages with the same metadata cache approach as available packages, maintaining the core principle: **"A common data structure for all packages."**

#### Proposed Architecture

**Current Issue:**
- Available packages: Cached in SQLite, fast search, cross-manager aggregation ✅
- Installed packages: Queried via shell commands, slow, single-manager only ❌
- "All Packages" + "Installed" only shows WinGet (no unified aggregation) ❌

**Proposed Solution:**
- Add `is_installed` flag to existing `packages` table in metadata cache
- Store installed state alongside available package metadata
- Query SQLite instead of invoking package managers repeatedly
- Enable instant cross-manager aggregation with single query

#### Key Benefits

1. **Consistency** - Same `Package` model, same cache, same search logic for both sources
2. **Performance** - SQLite queries (< 1 second) vs shell commands (5-10 seconds)
3. **Cross-Manager Aggregation** - "All Packages" + "Installed" shows packages from all managers with one query: `SELECT * FROM packages WHERE is_installed = 1`
4. **Rich Metadata** - Can detect updates by comparing `installed_version` vs `version` (available)
5. **Offline Capability** - View installed packages without network or package manager availability

#### Implementation Phases (4-6 hours estimated)

1. **Database Schema Extension** - Add `is_installed`, `installed_version`, `install_date` columns
2. **Installed Packages Providers** - Create `InstalledPackagesProvider` classes for each manager
3. **Cache Service Extensions** - Add `sync_installed_packages()` and `get_installed_packages()` methods
4. **UI Integration** - Update refresh logic to use cache queries instead of shell commands
5. **Auto-Refresh & Optimization** - Background sync on startup, staleness detection

#### Future Enhancements

- **Update Detection** - Compare `installed_version` vs `version` to show "Update Available" badge
- **Installation History** - Track when packages were installed/uninstalled
- **Dependency Tracking** - Store and visualize package dependencies
- **Portable Mode** - Export/import installed package lists for new machine setup

**Full Plan:** See `PLAN_Installed_Packages_Cache.md` for complete architecture, code examples, migration strategy, and risk analysis.

---

## [0.4.1b] - 2025-12-27 11:30

### Fixed - Cross-Repository Search UI

**Issue:** UI search was hardcoded to only search WinGet repository, preventing cross-repository search functionality despite working cache layer.

**Solution:** Added repository selector checkboxes to enable flexible search across package managers.

### Added

#### UI Controls
- **Repository filter checkboxes** in search toolbar
  - WinGet checkbox (default: checked)
  - Chocolatey checkbox (default: checked)
  - Tooltips explaining each repository
  - "Repositories:" label for clarity

### Changed

#### Search Functionality (`ui/views/main_window.py`)
- **`search_packages()` method** - Now respects repository selection
  - Reads checkbox states to determine search scope
  - Validates at least one repository is selected
  - Uses `managers=None` for cross-repo search (both checked)
  - Uses `managers=['winget']` or `managers=['chocolatey']` for single-repo
  - Status messages now show which repositories were searched

#### User Experience
- Search across both repositories by default (both checkboxes checked)
- Easily filter to single repository by unchecking other
- Status bar shows repository scope: "Found 10 results for 'python' in all repositories"
- Warning if user unchecks both repositories

### Validated

#### Cross-Repository Search Tests
- ✅ **Cross-repo search working** - Returns results from both WinGet and Chocolatey
- ✅ **Single-repo filtering** - WinGet-only and Chocolatey-only searches work correctly  
- ✅ **FTS5 ranking** - Properly ranks results across repositories
- ✅ **Source attribution** - Results correctly tagged with source manager

**Test Results** (search for "python"):
- Cross-repo: 10 results (4 WinGet + 6 Chocolatey)
- WinGet only: 10 results (all WinGet)
- Chocolatey only: 10 results (all Chocolatey)

### Test Suite
- **`test_cross_repo_search.py`** - Comprehensive cross-repository validation
  - Tests cross-repo, WinGet-only, and Chocolatey-only searches
  - Validates result sources and counts
  - Confirms FTS5 ranking across repositories

---

## [0.4.1] - 2025-12-27 11:00

### Major Feature - Chocolatey Integration & Cross-Repository Search

**Achievement:** Successfully integrated Chocolatey Community Repository with **10,000 packages**, validating cross-repository search architecture with **18,398 total packages**.

#### Performance Results

| Metric | Result | Status |
|--------|--------|--------|
| **Chocolatey Packages** | 10,000 | ✅ CCR API limit |
| **Sync Time** | 4.49 minutes | ✅ Excellent |
| **Sync Rate** | 37 pkg/sec | ✅ API limited |
| **Search Speed** | 1.80ms avg | ✅ Sub-2ms |
| **Total Packages** | 18,398 | ✅ WinGet + Choco |
| **Total Cache Size** | 24.50 MB | ✅ 75% under target |

### Added

#### Chocolatey Integration
- **`metadata/providers/chocolatey_provider.py`** - Chocolatey metadata provider
  - Integrates with Chocolatey Community Repository OData API
  - Uses NuGet v2 protocol for package metadata
  - Fetches complete repository (10,000 package limit)
  
- **`metadata/sync/chocolatey_odata_fetcher.py`** - NuGet v2 OData API client
  - Atom XML feed parser for Chocolatey packages
  - Automatic pagination handling (40 packages per page)
  - Rate limiting and error recovery
  - Full metadata extraction (name, version, description, tags, homepage, license)

#### Test Suite
- **`test_choco_sync.py`** - Chocolatey sync validation script
  - Tests full repository sync from Chocolatey API
  - Validates cross-repository search functionality
  - Performance benchmarks for single-repo and cross-repo queries

### Changed
- **`metadata/sync/__init__.py`** - Exported `ChocolateyODataFetcher`
- **`metadata/providers/__init__.py`** - Exported `ChocolateyProvider`

### Validated - Cross-Repository Architecture

#### Single Database Performance
- ✅ **18,398 packages** in unified SQLite cache (WinGet + Chocolatey)
- ✅ **1.80ms average search** across both repositories
- ✅ **24.50 MB cache size** (1.33 KB per package)
- ✅ **Unified FTS5 ranking** - Best results regardless of source
- ✅ **Manager filtering** - Fast single-repo queries when needed

#### Search Validation
- ✅ **Single-repo search** - Chocolatey-only queries working
- ✅ **Cross-repo search** - Unified results from both repositories
- ✅ **Source attribution** - Results properly tagged with manager
- ✅ **Relevance ranking** - FTS5 ranks across repositories seamlessly

#### Architecture Decision Confirmed
**Single database approach validated** over separate databases:
- Unified FTS5 search ranks results across all package managers
- Simple cross-repo search (just remove manager filter)
- Efficient storage (excellent compression ratio)
- Fast manager-specific filtering with index

### API Details

**Chocolatey Community Repository:**
- **Endpoint:** `https://community.chocolatey.org/api/v2/Packages`
- **Protocol:** NuGet v2 OData (Atom XML)
- **Pagination:** 40 packages per page (hardcoded by API)
- **Limit:** 10,000 packages maximum (CCR API restriction)
- **Rate Limiting:** 0.1s delay between requests

### Next Steps (Phase 3)
- Implement UI sync progress dialog with provider selection
- Add incremental delta sync for faster updates
- Implement automatic background sync scheduling
- Add Scoop provider (~1,800 packages)
- Implement Pip lazy loading strategy (500K+ packages)
- Implement NPM lazy loading strategy (2M+ packages)

---

## [0.4.0] - 2025-12-27 04:15

### Major Feature - Complete Sync-to-SQL Architecture

**Achievement:** Implemented and validated complete metadata caching system with **8,398 real WinGet packages**.

#### Performance Results

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Search Speed | < 10ms | **1.52ms** | ✅ 85% faster |
| Cache Size | < 100 MB | **6.21 MB** | ✅ 94% under |
| Sync Time | < 5 min | **1.26 min** | ✅ 75% faster |
| Sync Rate | > 100/sec | **111/sec** | ✅ 11% faster |
| Scale Test (10K) | < 10ms | **3.59ms** | ✅ 64% faster |

### Added

#### Core Infrastructure
- **`metadata/` module** - Complete metadata caching system
  - `metadata_cache.py` - SQLite + FTS5 cache service with bulk update support
  - `providers/base.py` - Abstract MetadataProvider interface
  - `providers/winget_provider.py` - WinGet provider with full repository sync capability

#### Sync Services
- **`metadata/sync/` module** - Background synchronization services
  - `background_sync_service.py` - Orchestrates sync operations, tracks status per provider
  - `local_manifest_parser.py` - Parses local winget-pkgs repository clone ⭐ **Production method**
  - `github_manifest_fetcher.py` - GitHub API manifest fetcher (alternative approach)
  - `wingetrun_fetcher.py` - winget.run REST API fetcher (alternative approach)

#### Data Models
- **`core/models.py`** - New `UniversalPackageMetadata` dataclass
  - Normalized structure for all package managers
  - FTS5-optimized search_tokens field
  - Bidirectional conversion with existing `Package` model

#### UI Integration
- **`ui/views/main_window.py`** - Search UI components
  - QLineEdit search bar with real-time search
  - Search button with enable/disable logic
  - Background cache initialization on first use

#### Test Suite
- `test_search.py` - Initial search validation
- `test_10k_scale.py` - 10,000 synthetic package scale test ✅ ALL TARGETS EXCEEDED
- `test_full_sync.py` - Full repository sync framework
- `test_real_winget_sync.py` - **Production sync with 8,398 real packages** ⭐

#### Documentation
- `notes/sync_to_sql_architecture.md` - Complete architecture design
- `notes/apt_data_structures.md` - APT architecture reference
- `notes/WinGet_Rest_API_vs_SQLite_db-approach.md` - Approach comparison
- `notes/Relative_size_of_apt_vs_winget_dbs.md` - Scale reference

### Changed
- Enhanced `MetadataCacheService.refresh_cache()` to accept package iterators
- Added `WinGetProvider.fetch_all_packages()` for full repository sync
- Database schema: Added `sync_metadata` table for tracking sync status

### Fixed
- WinGet database path: Corrected from `index.db` to `installed.db`
- WinGet database schema: Updated queries for normalized tables
- FTS5 query handling: Added sanitization for special characters (., -, etc.)
- Tag parsing: Handle integer tags in YAML by converting to strings

### Validated
- ✅ **8,398 real WinGet packages** synced from microsoft/winget-pkgs
- ✅ **Zero parse errors** across all manifests
- ✅ **Sub-2ms search** across 8,398 packages
- ✅ **All test queries working** - VSCode, Chrome, Python, Notepad++, Git, etc.
- ✅ **Architecture scales linearly** - Proven with 10K synthetic test

### Architecture Benefits
- **Instant Search:** 1.52ms average across all query types
- **Offline Capable:** All data cached locally in SQLite
- **Cross-Repository Ready:** Pattern works for Chocolatey, Pip, NPM
- **Scalable:** Tested to 10K, designed for 60K+ (APT scale)
- **Efficient:** Only 740 bytes per package (SQLite + FTS5 compression)

### Dependencies Added
- `PyYAML` - YAML manifest parsing
- `requests` - HTTP requests for API fetchers (already installed)
- `packaging` - Semantic version parsing (already installed)

### Next Steps (Phase 2)
- Add Chocolatey provider (~9,500 packages)
- Implement UI sync progress dialog
- Add incremental delta sync
- Schedule automatic background sync
- Implement Pip lazy loading (500K+ packages)
- Implement NPM lazy loading (2M+ packages)

---

## [0.3.1] - 2025-12-27 02:15

### Major Improvements - Installation Path Detection

**Problem:** Installation paths showed 50% correct, 25% no path, 25% wrong paths (e.g., Vim/Quod Libet showing CPUID HWMonitor's path).

**Solution:** Complete overhaul of registry-based path detection system.

**Results:**
- **Before:** 52/138 packages (38%) with valid installation paths
- **After:** 84/138 packages (61%) with valid installation paths
- **Improvement:** +32 packages detected (+62% increase!)

### Added

- **UninstallString Path Extraction** (`ui/views/main_window.py`):
  - New Method 3: Extract from `UninstallString` registry field
  - New Method 4: Extract from `InstallString` registry field
  - Regex pattern extracts directory from executable paths:
    - Example: `"C:\Program Files\Vim\vim91\uninstall.exe"` → `C:\Program Files\Vim`
  - Handles quoted and unquoted paths
  - Validates extracted paths exist on disk
  - **Impact:** Fixed Vim, Notepad++, Armoury Crate Service, and many others

- **Smart Parent/Path Selection** (`ui/views/main_window.py`):
  - Intelligent decision logic: use extracted path vs. parent directory
  - Detects version subdirectories via pattern matching:
    - Version numbers: `vim91`, `v1.2.3`, `3.14`
    - Architecture subdirs: `x64`, `x86`, `win64`
    - Common subdirs: `bin`, `app`, `uninstall`, `install`
  - **Examples:**
    - Vim: `C:\...\Vim\vim91\...` → returns `C:\...\Vim` (parent)
    - Notepad++: `C:\...\Notepad++\...` → returns `C:\...\Notepad++` (path)
  - **Impact:** Prevents showing `C:\Program Files` (too high) or versioned subdirs

- **Multi-Hive Registry Search for ARP Packages** (`ui/views/main_window.py`):
  - ARP packages now search ALL registry hives (HKLM + HKCU)
  - Prioritizes indicated hive but falls back to others
  - Handles cases where WinGet's ARP hive indication is inaccurate
  - **Impact:** Finds user-level installations missed by machine-only search

- **Enhanced ARP Package Matching** (`ui/views/main_window.py`):
  - ARP format detection: `ARP\Machine\X64\PackageName`
  - Extracts actual package ID from ARP path
  - Matches against both registry subkey name AND DisplayName
  - Confidence-based scoring:
    - 150: Exact ARP subkey match
    - 145: Exact DisplayName match
    - 115: Normalized DisplayName match
  - **Impact:** Fixed exact-match packages like "Vim 9.1" that weren't being found

- **Debug Output Enhancements** (`ui/views/main_window.py`):
  - Shows total registry entries scanned
  - Sample of entries with/without install paths (✓/✗ indicators)
  - Match reason tracking (e.g., "subkey_exact_arp_normalized")
  - Confidence scores for all candidates
  - **Impact:** Made troubleshooting installation path issues transparent

### Fixed

- **Installation Path Accuracy** (`ui/views/main_window.py`):
  - Fixed: Vim 9.1 now shows `C:\Program Files\Vim` ✓
  - Fixed: Notepad++ now shows `C:\Program Files\Notepad++` ✓ (was showing `C:\Program Files`)
  - Fixed: Armoury Crate Service now shows path ✓ (was showing no path)
  - Fixed: Quod Libet no longer shows CPUID HWMonitor's path
  - Fixed: Mozilla Firefox shows correct path from 2 candidates
  - Fixed: Version-only package IDs (e.g., "4.7.1") now skipped entirely

- **ARP Package Handling** (`ui/views/main_window.py`):
  - Fixed: `winget show` no longer called for ARP packages (prevents error 2316632084)
  - Fixed: ARP packages search correct registry hives
  - Fixed: Case-sensitive vs case-insensitive matching for ARP subkeys

### Technical Details

**Path Extraction Methods (in priority order):**
1. `InstallLocation` field (direct registry value)
2. `InstallPath` field (alternate registry field)
3. `UninstallString` field (NEW - parse uninstaller path)
4. `InstallString` field (NEW - parse installer path)

**Regex Pattern for Path Extraction:**
```regex
^"?([A-Z]:[^"]+?)\\[^\\]+\.exe
```
- Matches: `"C:\Program Files\App\uninstall.exe"` or `C:\path\to\file.exe`
- Captures: Directory containing the executable

**Version Subdirectory Detection:**
```regex
(^|[^a-z])(v?\d+\.?\d*|bin|app|x64|x86|win\d+)$
```
- Matches: `vim91`, `v1.2`, `bin`, `x64`, etc.
- Action: Use parent directory instead of path itself

**Confidence Scoring System:**
- 150: Exact ARP subkey match (case-sensitive)
- 145: Exact DisplayName match for ARP
- 120-135: Normalized matches for ARP
- 100-110: Full package ID matches
- 80-95: Product/Publisher name matches
- 70: Minimum threshold for accepting match
- +5-10: Boost if install path contains package name

**Files Modified:**
- `ui/views/main_window.py` - All path detection improvements (15 commits)

**Commits in this release:**
1. Improve install path matching with multi-term search and registry subkey checking
2. Improve ARP package matching to check DisplayName field
3. Fix winget show for ARP packages and broaden registry search
4. Add debug output to show sample registry entries when no match found
5. Add WinGet show fallback for installation path detection
6. Enhanced debug output to show registry entries without install paths
7. Extract installation paths from UninstallString and InstallString
8. Add debug output for UninstallString extraction failures
9. Clean up debug code - UninstallString extraction working
10. Fix path extraction to use smart parent/path selection

## [0.3.0] - 2025-12-26 21:20

### Added - Professional UI and Menu System

- **Menu Bar** (`ui/views/main_window.py`):
  - Industry-standard menu structure: File, Edit, View, Config, Help
  - Keyboard shortcuts with Alt key navigation (underlined letters)
  - File menu with Exit action (Ctrl+Q shortcut)
  - Edit and View menus (placeholders for future features)

- **Help Menu** (`ui/views/main_window.py`):
  - **User Guide** - Placeholder dialog directing to README.md and CLAUDE.md
  - **Change Log** - Displays full CHANGELOG.md in scrollable dialog (800x600)
    - Monospace font for readability
    - Read-only QTextEdit widget
  - **About Dialog** - Professional about box with:
    - Auto-extracted version number from CHANGELOG.md (regex parsing)
    - Release date from CHANGELOG.md
    - Project description and supported package managers
    - Link to Claude Code
    - Copyright notice

- **Config Menu** (`ui/views/main_window.py`):
  - **View Configuration** - Read-only display of config.json
    - Shows full file path at top (selectable for copying)
    - Pretty-printed JSON in monospace font
    - 700x500 dialog with scrolling

- **Version Label** (`ui/views/main_window.py`):
  - Subdued gray label in upper right corner of UI
  - Shows: `v0.3.0 (2025-12-26 21:20)`
  - Auto-extracts from CHANGELOG.md on startup
  - Smaller font (9pt), gray color (#808080)
  - Unobtrusive but always visible

- **Animated Spinner** (`ui/views/main_window.py`):
  - Replaced static hourglass emoji with animated circling dots
  - 8 Braille pattern characters: ⣾ ⣽ ⣻ ⢿ ⡿ ⣟ ⣯ ⣷
  - Updates every 100ms (10 FPS) via QTimer
  - Modern loading indicator like AI chat applications
  - Starts on operation_started, stops on operation_finished
  - Shows next to status messages: `⣾ Getting package list...`

- **Verbose Mode** (`ui/views/main_window.py`):
  - Checkbox in control panel: "Verbose"
  - Tooltip: "Show detailed package manager output during operations"
  - When enabled, shows dialog after install/uninstall with:
    - Full stdout from package manager (monospace font)
    - Full stderr with errors (red text, monospace)
    - Exit code and operation details
  - Perfect for power users debugging installation issues
  - Disabled by default for clean UX

- **Persistent Status Bar** (`ui/views/main_window.py`):
  - Package count stays visible after loading
  - Format: "132 packages loaded - Ready"
  - Proper grammar: "1 package" vs "132 packages"
  - Temporary messages (clipboard copy) restore to package count after 3 seconds
  - No more disappearing package count

### Fixed

- **NPM Windows Compatibility** (`services/package_service.py`):
  - CRITICAL: NPM commands now work on Windows
  - Issue: `npm.cmd` not found by subprocess without shell
  - Solution: Added `shell=True` for all NPM operations:
    - `_get_npm_installed()` - List global packages
    - `install_package()` - Install when manager is NPM
    - `uninstall_package()` - Uninstall when manager is NPM
  - Tested with NPM 11.6.2 - fully functional

### Technical Details

**Menu System:**
- `QMenuBar` with `QAction` items
- Signal/slot connections to handler methods
- File path resolution using `os.path.dirname(__file__)`
- Regex version extraction: `r'##\s+\[([^\]]+)\]\s+-\s+(\d{4}-\d{2}-\d{2})'`

**Animated Spinner:**
- QTimer-based animation loop
- Spinner state: `spinner_index`, `spinner_frames`, `spinner_timer`
- `_update_spinner()` method called every 100ms
- Lifecycle managed by operation signals

**Verbose Dialog:**
- Custom QDialog with QTextEdit widgets
- Monospace font: 'Consolas', 'Courier New'
- Stderr styled with red text (#d32f2f)
- Displays `OperationResult.details` dict (stdout/stderr/exit_code)

**NPM Fix:**
- Conditional `shell=True` parameter: `use_shell = (manager == PackageManager.NPM)`
- Only affects NPM commands, other managers unchanged
- Windows-specific workaround for .cmd batch files

### User Benefits

- **Professional Appearance**: Industry-standard menu bar like commercial applications
- **Easy Access to Info**: Quick access to changelog, version, and configuration
- **Visual Feedback**: Smooth animated spinner shows operations are active
- **Power User Support**: Verbose mode for debugging installation issues
- **NPM Support**: NPM package management now works on Windows
- **Persistent Information**: Package count always visible in status bar
- **Quick Version Check**: Version label always visible in upper right corner

### Testing v0.3.0

**Menu Bar:**
1. Click each menu to verify structure
2. Help → About - Check version shows v0.3.0 and date
3. Help → Change Log - Scroll through full CHANGELOG.md
4. Config → View Configuration - Verify config.json displays with full path
5. File → Exit or Ctrl+Q to close

**Spinner Animation:**
1. Click Refresh with any package manager
2. Watch progress label - should see rotating dots
3. Verify smooth animation at 10 FPS

**Verbose Mode:**
1. Check "Verbose" checkbox
2. Install or uninstall a package
3. Verify detailed output dialog appears after operation
4. Check stdout and stderr sections display correctly

**NPM Support:**
1. Select "NPM" from dropdown
2. Click Refresh
3. Verify global NPM packages load successfully

**Persistent Status:**
1. Load packages from any manager
2. Verify status bar shows: "X packages loaded - Ready"
3. Copy installation path
4. After 3 seconds, verify status returns to package count

### Notes

- **Major Release**: Significant UI improvements justify jump to 0.3.0
- **Menu Placeholders**: Edit and View menus ready for future features
- **Version Automation**: Version/date auto-extracted from this CHANGELOG
- **Cross-Platform**: Menu system works on Windows, macOS, Linux
- **NPM Limitation**: `shell=True` is Windows-specific workaround
- **Next Phase**: Phase 4 will implement full search functionality

**Key Files Modified:**
- `ui/views/main_window.py`: Menu bar, dialogs, spinner, verbose mode, version label, persistent status
- `services/package_service.py`: NPM Windows fix with shell=True

**Tag:**
- `v0.3.0`: Major release with professional UI enhancements

---

## [0.0.2] - 2025-12-26

### Added - Installation Path Discovery and UX Enhancements

- **Installation Path Display** (`ui/views/main_window.py`):
  - `_get_winget_install_location()` method queries Windows Registry for actual installation directories
  - Searches three registry hives: HKLM, HKLM WOW6432Node, HKCU
  - Looks up `InstallLocation` and `InstallPath` registry values
  - Matches package ID to registry DisplayName (case-insensitive)
  - Verifies paths exist before returning
  - Displays in package details dialog for WinGet packages only

- **Enhanced Package Details Dialog** (`ui/views/main_window.py`):
  - Custom `QDialog` replaces simple `QMessageBox` for richer UI
  - Shows package information: Name, Version, Manager, Description
  - Installation Location section (when available):
    - Highlighted box with selectable text
    - One-click "Copy Path to Clipboard" button
    - Visual feedback in status bar: "Copied to clipboard: [path]"
    - Auto-clears status message after 3 seconds
  - Useful for adding installation directories to PATH environment variable

- **Manual Package Installation** (`ui/views/main_window.py`):
  - `QInputDialog` for entering WinGet package IDs directly
  - Install button always enabled when WinGet selected (no selection required)
  - Supports installing packages not yet visible in the list
  - Example package IDs: `Microsoft.PowerToys`, `Git.Git`, `7zip.7zip`
  - Creates temporary Package object with user-entered ID
  - Falls back to standard selection-based installation if package selected

### Fixed

- **Critical Sorting Bug** (`ui/components/package_table.py`):
  - **CRITICAL**: Fixed bug where selecting package after sorting could uninstall wrong package
  - Previously used row index on sorted table: `self.packages[row]`
  - Now stores Package object in table cell's UserRole data: `name_item.setData(Qt.ItemDataRole.UserRole, package)`
  - `get_selected_package()` retrieves Package from cell data instead of array index
  - Selection is now 100% safe regardless of sort order
  - Prevents accidental uninstallation of wrong applications

### Changed

- **UI Theme Integration** (`ui/components/package_table.py`):
  - Removed color-coded table backgrounds (light green/orange/blue/pink)
  - Now uses system theme colors for table display
  - Much easier on eyes for extended viewing sessions
  - Better integration with Windows light/dark mode
  - Commented out `_apply_row_color()` calls in `set_packages()`

- **Button State Logic** (`ui/views/main_window.py`):
  - Install button always enabled (supports manual WinGet ID entry)
  - Uninstall button only enabled when package selected
  - Previously both buttons required package selection

### User Benefits

- **Time Saver**: Installation paths readily available for adding to PATH
- **Safety**: Correct package always selected/uninstalled even after sorting
- **Comfort**: System theme colors reduce eye strain
- **Flexibility**: Install any WinGet package by ID without searching first

### Technical Details

**Windows Registry Lookup:**
- `winreg.OpenKey()` accesses uninstall registry keys
- Enumerates all subkeys (installed applications)
- Matches package name (e.g., "Firefox" from "Mozilla.Firefox")
- Extracts InstallLocation or InstallPath values
- Only returns paths that actually exist on filesystem

**Qt Data Storage:**
- `Qt.ItemDataRole.UserRole` stores Python objects in table cells
- Survives table sorting operations intact
- Retrieved via `item.data(Qt.ItemDataRole.UserRole)`

### Testing v0.0.2

**Installation Path Feature:**
1. Select "WinGet" → Click Refresh
2. Double-click on Mozilla Firefox, Notepad++, or VLC
3. Verify "Installation Location" section appears with correct path
4. Click "Copy Path to Clipboard"
5. Check status bar shows confirmation message
6. Paste in Notepad to verify clipboard contents

**Manual Installation:**
1. Select "WinGet" (ensure no package selected)
2. Click Install button
3. Enter package ID: `Microsoft.PowerToys`
4. Confirm installation
5. Verify package installs successfully

**Sorting Safety:**
1. Load WinGet packages
2. Click "Version" column header to sort
3. Select any package
4. Verify package details dialog shows correct package name
5. Test uninstall to ensure correct package targeted

### Notes

- **Minor Version Bump**: Significant user-facing features justify 0.0.1 → 0.0.2
- **Registry Access**: Read-only registry queries, no write operations
- **Path Availability**: Not all apps register InstallLocation in registry
  - Apps that don't register will show basic details without path
  - This is a Windows limitation, not a bug
- **Platform Specific**: Registry lookup Windows-only (WinGet is Windows-only)
- **Next Phase**: Phase 4 will implement full search functionality

**Key Files Modified:**
- `ui/views/main_window.py`: Registry lookup, enhanced dialog, manual entry, clipboard copy
- `ui/components/package_table.py`: UserRole data storage, theme integration

**Tag:**
- `v0.0.2`: Minor release with installation path discovery and UX enhancements

---

## [0.0.1d] - 2025-12-26

### Added - Phase 3: Install/Uninstall Functionality

- **Install/Uninstall Implementation** (`ui/views/main_window.py`):
  - `install_package()` method: Full worker-based implementation with confirmation dialog
  - `uninstall_package()` method: Full worker-based implementation with warning dialog
  - Package selection enables/disables Install/Uninstall buttons
  - Confirmation dialogs before operations (Yes/No with default to No)
  - Warning dialog for uninstall with "cannot be undone" message
  - Non-blocking operations via PackageInstallWorker and PackageUninstallWorker
  - Auto-refresh package list after successful operations
  - Success/failure dialogs with detailed messages

- **Worker State Management**:
  - `current_install_worker` and `current_uninstall_worker` tracking
  - `selected_package` state variable for button enable/disable logic
  - Proper worker cleanup with `.wait()` and `.deleteLater()`
  - Multiple worker types cleaned up in `on_operation_finished()`

- **Signal Handlers** (`ui/views/main_window.py`):
  - `on_package_selected()`: Enables Install/Uninstall buttons when package selected
  - `on_install_complete()`: Handles installation completion, shows dialog, auto-refreshes
  - `on_uninstall_complete()`: Handles uninstallation completion, shows dialog, auto-refreshes
  - Both handlers log operations to history file

- **Operation History Logging**:
  - `_log_operation()` helper method writes to `operation_history.json`
  - Logs stored in XDG data directory: `%APPDATA%\Local\winpacman\operation_history.json`
  - JSON format with operation type, package, success status, message, timestamp
  - Circular buffer keeps last 100 operations
  - Handles I/O errors gracefully (prints to console, doesn't crash)

- **Button State Logic**:
  - Install/Uninstall buttons disabled by default
  - Enabled when package selected (via `package_selected` signal)
  - Disabled when package manager dropdown changes
  - Disabled during any operation (install/uninstall/refresh)
  - Conditionally re-enabled after operation based on selection state

### Fixed

- **Error Message Handling** (`services/package_service.py`):
  - Improved error messages for install/uninstall failures
  - Checks both `stderr` and `stdout` for error output
  - Falls back to showing exit code if both streams are empty
  - Previously showed empty error messages when stderr was blank
  - Now provides detailed permission errors and failure reasons

### Changed

- **enable_controls() Method**: Conditionally enables Install/Uninstall buttons
  - Only enables if package is selected
  - Previously didn't manage Install/Uninstall button states

- **on_manager_changed() Method**: Clears selection and disables buttons
  - Resets `selected_package` to None
  - Disables Install/Uninstall buttons when switching managers
  - Previously only cleared table and status label

### Testing Phase 3

**Test Cases Verified:**
1. ✅ **Pip Install/Uninstall**: Cowsay installed and uninstalled successfully (no admin required)
2. ✅ **Chocolatey Install**: fzf installed successfully with auto-refresh
3. ✅ **Chocolatey Uninstall (no admin)**: Permission error displayed correctly, package not removed
4. ✅ **Chocolatey Uninstall (as admin)**: fzf uninstalled successfully with auto-refresh
5. ✅ **Button States**: Enabled/disabled correctly based on selection and operation status
6. ✅ **Confirmation Dialogs**: Displayed before install/uninstall operations
7. ✅ **Error Handling**: Detailed permission errors shown with full context
8. ✅ **Operation History**: Logged to JSON file successfully

```powershell
# Test Install/Uninstall (Pip - no admin required)
.\winpacman_env_windows\Scripts\Activate.ps1
python gui_pyqt6.py
# 1. Select "Pip" → Click Refresh
# 2. Install a test package via command line: pip install cowsay
# 3. Refresh Pip list, select cowsay
# 4. Click Uninstall → Confirm → Verify success dialog and auto-refresh

# Test Install/Uninstall (Chocolatey - requires admin)
# Run PowerShell as Administrator
cd C:\Users\jimur\Projects\WinPacMan
.\winpacman_env_windows\Scripts\Activate.ps1
python gui_pyqt6.py
# 1. Select "Chocolatey" → Click Refresh
# 2. Select a package → Click Install → Confirm
# 3. Verify success dialog and auto-refresh
# 4. Click Uninstall → Confirm warning → Verify success

# Check operation history
# View: %APPDATA%\Local\winpacman\operation_history.json
```

### Notes

- **Beta Release**: Phase 3 complete with install/uninstall functionality
- **Permission Handling**: Chocolatey requires admin rights for install/uninstall
  - Clear error messages guide users to run as administrator
  - Pip and WinGet typically work without admin for user-level packages
- **Auto-Refresh**: Package list automatically refreshes after successful operations
  - Failed operations do not trigger auto-refresh (preserves current view)
- **Operation History**: All install/uninstall attempts logged to JSON file
  - Success and failure both recorded with full details
  - Useful for debugging and auditing
- **Next Phase**: Phase 4 will implement search functionality

**Key Files Modified:**
- `ui/views/main_window.py`: Install/uninstall implementation, signal handlers, state management
- `services/package_service.py`: Improved error message handling

**Tag:**
- `v0.0.1d`: Beta release with Phase 3 complete

---

## [0.0.1c] - 2025-12-26

### Added - Phase 2: PyQt6 UI with Package Listing

- **Main Application Window** (`ui/views/main_window.py`):
  - `WinPacManMainWindow` class extending QMainWindow
  - Modern control panel with package manager dropdown selector
  - Action buttons: Refresh, Search, Install, Uninstall
  - Status bar with integrated progress indicator
  - Real-time operation status updates via QTimer
  - Comprehensive error handling with user-friendly dialogs
  - Theme support (light/dark) with stylesheet application

- **Package Table Widget** (`ui/components/package_table.py`):
  - `PackageTableWidget` custom QTableWidget for package display
  - Color-coded rows by package manager:
    - WinGet: Light green (#E8F5E8)
    - Chocolatey: Light orange (#FFF4E6)
    - Pip: Light blue (#E6F3FF)
    - NPM: Light pink (#FCE6F3)
  - Sortable columns: Package Name, Version, Manager, Description
  - Explicit text color (black) for visibility on light backgrounds
  - Single selection mode with row selection behavior
  - Double-click signal for package details
  - Automatic column sizing with interactive resize support

- **Enhanced Package Workers** (`ui/workers/package_worker.py`):
  - Progress tracking with current/total counts and status messages
  - Detailed debug logging for troubleshooting
  - Signal emissions: `started`, `progress`, `packages_loaded`, `error_occurred`, `finished`
  - Thread-safe communication via pyqtSignal/pyqtSlot decorators

- **Improved Error Handling** (`services/package_service.py`):
  - JSON module properly imported at file level
  - Separate exception handling for `FileNotFoundError` vs other errors
  - User-friendly error messages with installation suggestions:
    - **WinGet**: "Built into Windows 11. For Windows 10, install from Microsoft Store"
    - **Chocolatey**: "Install from https://chocolatey.org/install"
    - **Pip**: "Should be included with Python. Try 'python -m ensurepip'"
    - **NPM**: "Install Node.js from https://nodejs.org to use NPM"
  - Consistent error handling across all four package managers

### Fixed

- **Table Display Issue**: Added explicit `setForeground(QColor("#000000"))` to table cells
  - Previously, text was invisible due to white/light text on light backgrounds
  - Now displays black text on color-coded backgrounds for all package managers

- **NPM JSON Import Error**: Moved `import json` from function body to module imports
  - Fixed "cannot access local variable 'json' where it is not associated with a value" error
  - Exception handler can now properly reference `json.JSONDecodeError`

- **Package Manager Not Available**: Separated `FileNotFoundError` handling from general errors
  - Now shows `PackageManagerNotAvailableError` with helpful installation instructions
  - Previously showed generic "operation failed" messages

### Changed

- **Package Table Architecture**:
  - Sorting disabled during population for performance
  - Explicitly re-enabled after population complete
  - Row count set before populating (avoids incremental resize)

### Testing Phase 2

```powershell
# Activate environment
.\winpacman_env_windows\Scripts\Activate.ps1

# Launch PyQt6 GUI
python gui_pyqt6.py

# Test each package manager:
# 1. Select "WinGet" → Click Refresh → Verify 90 packages displayed with light green rows
# 2. Select "Chocolatey" → Click Refresh → Verify packages with light orange rows
# 3. Select "Pip" → Click Refresh → Verify packages with light blue rows
# 4. Select "NPM" → Click Refresh → Verify error message with installation link (if not installed)
```

### Notes

- **Beta Release**: Phase 2 complete with functional package listing UI
- **Description Column**: Reserved but blank (descriptions not available from list commands)
  - Future enhancement: Can be populated via lazy loading or caching
- **Responsiveness**: All operations run in QThread workers - UI never freezes
- **Next Phase**: Phase 3 will implement Install/Uninstall functionality

**Key Commits:**
- `f1d784e`: Fix PyQt6 segmentation fault - migrate from FluentWindow to QMainWindow
- `5aa783f`: Phase 2 Complete - FluentWindow UI with Package Listing

**Tag:**
- `v0.0.1c`: Beta release with Phase 2 complete

---

## [0.0.1b] - 2025-12-26

### Added - Phase 1: PyQt6 Foundation

- **PyQt6 Worker Framework** (`ui/workers/`):
  - `PackageSignals` class with pyqtSignal definitions for thread-safe communication
  - `PackageListWorker` (QThread): Non-blocking package listing with progress signals
  - `PackageInstallWorker` (QThread): Non-blocking package installation
  - `PackageUninstallWorker` (QThread): Non-blocking package uninstallation
  - Event-driven architecture replacing polling-based threading
  - Signals: `progress`, `packages_loaded`, `operation_complete`, `error_occurred`, `started`, `finished`

- **PyQt6 Test GUI** (`gui_pyqt6.py`):
  - Minimal test window demonstrating QThread worker functionality
  - Signal/slot communication pattern with no UI freezing
  - Progress bar and status updates via pyqtSignal
  - Test button for WinGet package listing
  - Proper worker lifecycle management with cleanup

- **Dependencies Added** (`requirements.txt`):
  - **PyQt-Fluent-Widgets 1.10.5**: Windows 11 Fluent Design components
  - **PyQt6-Frameless-Window 0.7.4**: Modern frameless window styling
  - **pywin32 311**: Windows integration (Mica effects, notifications)

### Changed

- **Threading Architecture**:
  - Before: `threading.Thread` with `root.after(100ms)` polling
  - After: `QThread` with `pyqtSignal`/`pyqtSlot` event-driven updates
  - Eliminates polling overhead for smoother UI performance

### Notes

- **Beta Release**: Phase 1 foundation complete, GUI is minimal test implementation
- **Tkinter Fallback**: `gui_tkinter.py` remains available and functional
- **Service Layer**: No changes to `PackageManagerService` or `SettingsService` - full backward compatibility
- **Next Phase**: Phase 2 will implement FluentWindow-based main UI with package table

### Development Commands

```powershell
# Install Phase 1 dependencies
.\winpacman_env_windows\Scripts\Activate.ps1
pip install PyQt-Fluent-Widgets PyQt6-Frameless-Window pywin32

# Test Phase 1 GUI
python gui_pyqt6.py
```

### Testing Phase 1

1. Launch `python gui_pyqt6.py`
2. Click "Test WinGet List (QThread Worker)"
3. Verify:
   - Window remains responsive during operation
   - Progress bar updates automatically
   - Status messages change in real-time
   - Package count displayed on completion
   - No UI freezing or "white out"

**Key Commits:**
- `3457e97`: Phase 1 Complete - PyQt6 Foundation with QThread Workers

**Tag:**
- `v0.0.1b`: Beta release with Phase 1 complete

---

## [0.0.1] - 2025-12-26

### Added
- **Core Architecture**:
  - Layered architecture with clean separation of concerns (Presentation, Service, Core, Infrastructure layers)
  - Comprehensive data models in `core/models.py`:
    - `PackageManager` enum: WINGET, CHOCOLATEY, PIP, NPM
    - `PackageStatus` enum: INSTALLED, AVAILABLE, OUTDATED, INSTALLING, UNINSTALLING, UPDATING, FAILED
    - `Package` dataclass with 12+ fields for package representation
    - `OperationProgress`, `OperationResult`, `SearchQuery`, and `PackageListResult` models
  - Custom exception hierarchy in `core/exceptions.py` with 11 specific exception types

- **Configuration Management**:
  - XDG Base Directory specification compliance via `ConfigManager` class
  - Configuration stored in `~/.config/winpacman/` (Windows: `%APPDATA%/Local/winpacman/`)
  - Dot-notation access for nested configuration values
  - Deep merge strategy for user settings vs defaults
  - Persistent JSON storage with automatic directory creation

- **Package Manager Integration**:
  - WinGet support with regex-based output parsing (`re.split(r'\s{2,}', line)`)
  - Chocolatey support with simple space-split parsing
  - Pip support with JSON output format (`--format=json`)
  - NPM support with JSON parsing (`npm list -g --json --depth=0`)
  - Package manager availability detection and validation
  - Version extraction for all supported package managers

- **Threading Support**:
  - `PackageOperationWorker` class for non-blocking operations
  - Background thread execution with result/error capture
  - Progress callback system for real-time status updates
  - Configurable timeouts (list: 60s, install: 300s, uninstall: 180s)

- **Console Application** (`main.py`):
  - Interactive mode with welcome screen and system info
  - Command-line modes: `list`, `search`, `info`, `config`, `test-threading`
  - Package manager status display with version information
  - Admin privilege detection
  - Threading demonstration functionality

- **Tkinter GUI** (`gui_tkinter.py`):
  - Modern tabbed interface (Discover, Installed, Updates, Settings)
  - Package manager selector dropdown
  - Package listing with color-coding by manager
  - Refresh functionality with progress tracking
  - Search capabilities
  - Status bar with real-time updates

- **System Utilities** (`utils/system_utils.py`):
  - `SystemUtils` class with static methods:
    - `is_command_available()`: Check if command exists in PATH
    - `get_command_version()`: Extract version information
    - `run_command()`: Execute commands with timeout handling
    - `check_admin_privileges()`: Windows admin detection via ctypes
    - `get_system_info()`: Platform, architecture, Python version
    - `validate_package_manager()`: Full availability verification
    - `elevate_privileges()`: Windows UAC elevation
  - `PathManager` class for temporary file and log management

- **Documentation**:
  - `README.md`: Project overview and installation instructions
  - `WARP.md`: Comprehensive development guidance for AI agents
  - `CLAUDE.md`: Claude Code instance guidance with architecture overview
  - `PyQt5_Installation_Plan.md`: PyQt6 installation documentation
  - Type hints throughout entire codebase

- **PyQt6 Environment**:
  - PyQt6 6.10.1 with Qt 6.10.0 successfully installed
  - Windows Python virtual environment at `winpacman_env_windows/`
  - All dependencies installed: xdg-base-dirs, requests, packaging, psutil
  - Verified and tested installation ready for GUI development

### Changed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

### Notes
- **Phase 1 Complete**: Core architecture and foundation established with 2000+ lines of well-organized Python code
- **Python Version**: Requires Python 3.11+
- **Platform**: Primary target is Windows 10/11, but designed with cross-platform compatibility in mind
- **PyQt6 Threading**: When implementing PyQt6 UI, must use `QThread` instead of `threading.Thread` for proper Qt signal/slot integration
- **Package Manager Requirements**: At least one package manager must be installed:
  - WinGet (recommended, built into Windows 11)
  - Chocolatey (optional)
  - Pip (included with Python)
  - NPM (optional, requires Node.js)

### Development History
Development commands used during Phase 1 implementation:

```powershell
# Environment setup
python -m venv winpacman_env
.\winpacman_env\Scripts\Activate.ps1
pip install -r requirements.txt

# PyQt6 installation (Windows Python)
C:\Users\jimur\AppData\Local\Microsoft\WindowsApps\python.exe -m venv winpacman_env_windows
.\winpacman_env_windows\Scripts\python.exe -m pip install -r requirements.txt

# Running the application
python main.py                          # Interactive mode
python main.py list winget              # List WinGet packages
python main.py info                     # System information
python main.py test-threading           # Threading demo
python gui_tkinter.py                   # Launch GUI

# Testing package managers
winget list                             # Test WinGet
choco list --local-only                 # Test Chocolatey
pip list --format=json                  # Test Pip
npm list -g --json --depth=0            # Test NPM

# Verification
.\winpacman_env_windows\Scripts\python.exe -c "from PyQt6 import QtWidgets; print('PyQt6 ready!')"
```

**Key Commits:**
- `4af5e51`: Phase 1 Foundation Complete - WinPacMan architecture established
- `e711588`: Phase 1 completed - Phase 1 Report
- `bb9886d`: Add WARP.md for AI agent development guidance
- `7ce2c7f`: Add CLAUDE.md and document successful PyQt6 6.10.1 installation

**Tag:**
- `v0.0.1`: Initial release with Phase 1 complete

---

## Development Phases

### Phase 1: Foundation (Complete)
- Core architecture and data models
- Package manager integration (4 managers)
- Configuration system
- Threading support
- Console interface
- Basic Tkinter GUI
- PyQt6 environment setup

### Phase 2: GUI Development (Planned)
- PyQt6 UI components
- Modern Windows 11-style interface
- QThread implementation for background operations
- Progress dialogs and notifications
- Settings GUI
- Advanced package management features

### Phase 3: Enhanced Features (Planned)
- Package installation/uninstallation
- Package updates and upgrades
- Advanced search with filters
- Batch operations
- Dependency management
- Update notifications
- System tray integration

---

## Version Format

WinPacMan follows Semantic Versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

Version 0.x.x indicates pre-release/development versions where the API may change.
