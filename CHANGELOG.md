# Changelog for WinPacMan

All notable changes to WinPacMan are documented here. This project follows [Semantic Versioning](https://semver.org/).

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
