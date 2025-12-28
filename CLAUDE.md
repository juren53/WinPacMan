# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WinPacMan is a Python-based unified package manager for Windows that provides a single interface for managing packages across WinGet, Chocolatey, Pip, and NPM. Built with PyQt6 (in development), it uses a modular, layered architecture with threading for non-blocking operations.

The project uses a stanard Python venv virtual environment that must be set for Python to run properly 

**Current Status:** Phase 1 complete. Core logic and CLI interface functional. PyQt6 6.10.1 successfully installed and ready for GUI development. Basic Tkinter GUI available as fallback.

## Development Commands

### Environment Setup
```powershell
# Use the Windows Python virtual environment (PyQt6 installed)
.\winpacman_env_windows\Scripts\Activate.ps1

# Or create new virtual environment with Windows Python
C:\Users\jimur\AppData\Local\Microsoft\WindowsApps\python.exe -m venv winpacman_env_windows

# Install dependencies
pip install -r requirements.txt
```

**Important**: Use `winpacman_env_windows` which has PyQt6 installed. The old `winpacman_env` uses MSYS2 Python without pip.

### Running the Application
```powershell
# Interactive mode (default)
python main.py

# List packages from a specific manager
python main.py list winget
python main.py list choco
python main.py list pip
python main.py list npm

# Search for packages
python main.py search winget <query>

# Show system info and available package managers
python main.py info

# Show configuration
python main.py config

# Test threading functionality
python main.py test-threading

# Launch GUI (Tkinter fallback)
python gui_tkinter.py
```

### Testing
No formal test suite currently implemented. When adding tests:
- Use pytest as the testing framework
- Use pytest-qt for PyQt6 component testing
- Test files should follow the pattern `test_*.py` or `*_test.py`

### Code Quality Tools
```powershell
# Code formatting (when implemented)
black .

# Type checking (when implemented)
mypy .
```

## Architecture

### Layered Architecture Pattern

```
Presentation Layer:  main.py, gui_tkinter.py
       ↓
Service Layer:       services/package_service.py, services/settings_service.py
       ↓
Core Layer:          core/models.py, core/config.py, core/exceptions.py
       ↓
Infrastructure:      utils/system_utils.py
```

**Key Directories:**
- `core/` - Domain models (Package, PackageManager enums), configuration management, exception hierarchy
- `services/` - Business logic (PackageManagerService for operations, SettingsService for configuration)
- `utils/` - System utilities (command execution, path management, admin privilege checking)
- `ui/` - UI components (mostly placeholder, awaiting PyQt6 implementation)
- `resources/` - UI assets and resources

### Critical Threading Pattern

**Current (CLI/Tkinter):**
```python
worker = PackageOperationWorker(
    self.package_service.get_installed_packages,
    manager,
    progress_callback
)
worker.start()
```

**CRITICAL: When implementing PyQt6 UI, you MUST use QThread instead of threading.Thread:**
```python
class PackageWorker(QThread):
    progress_signal = pyqtSignal(int, int, str)
    result_signal = pyqtSignal(list)

    def run(self):
        # Operations here
        self.result_signal.emit(packages)
```

Reason: Qt's signal/slot mechanism requires operations to run in QThread for proper thread safety and UI updates. Reference: `notes/How to capture and parse winget output into a PyQt table.md`

## Package Manager Integration

### Output Parsing Specifics

**WinGet:**
- Output format: `Name | Id | Version | Available | Source`
- Split on 2+ whitespace: `re.split(r'\s{2,}', line)`
- Skip header lines (typically 2-3 lines)
- Use `--accept-source-agreements` flag to avoid prompts
- Filter control characters from output

**Chocolatey:**
- Format: `package_name version`
- Skip summary line containing "packages installed"

**Pip:**
- Use `pip list --format=json` for structured output
- Parse directly as JSON (no regex needed)

**NPM:**
- Use `npm list -g --json --depth=0` for structured output
- Parse `dependencies` object from JSON response

### Timeouts
- List operations: 60 seconds
- Install operations: 300 seconds
- Uninstall operations: 180 seconds

## Data Models (core/models.py)

**Key Enums:**
- `PackageManager`: WINGET, CHOCOLATEY, PIP, NPM
- `PackageStatus`: INSTALLED, AVAILABLE, OUTDATED, INSTALLING, UNINSTALLING, UPDATING, FAILED
- `OperationType`: INSTALL, UNINSTALL, UPDATE, SEARCH, LIST
- `OperationStage`: QUEUED, DOWNLOADING, INSTALLING, CONFIGURING, COMPLETE, FAILED, CANCELLED

**Core Classes:**
- `Package` (dataclass): name, version, manager, status, description, source, etc.
- `OperationProgress`: Tracks operation progress (percentage, ETA, stage)
- `OperationResult`: Operation outcome (success, message, error details)
- `SearchQuery`: Structured search with filters

## Configuration Management

**XDG Base Directory Compliance:**
- Config: `~/.config/winpacman/` (Windows: `%APPDATA%/Local/winpacman/`)
- Data: `~/.local/share/winpacman/`
- Cache: `~/.cache/winpacman/`

**Access Pattern:**
```python
from core.config import config_manager
config = config_manager.load_config()
config_manager.set_config_value('ui.theme', 'dark')
# Dot-notation for nested values
theme = config_manager.get_config_value('ui.theme')
```

**Default Settings Include:**
- UI: theme, window geometry, language
- Package managers: enabled status, binary paths, auto-update
- Advanced: auto-refresh, cache duration, max concurrent operations, log level

## Exception Hierarchy (core/exceptions.py)

All exceptions inherit from `PackageManagerError` and include error codes and optional details dict:

- `PackageNotFoundError` - Package not found
- `OperationFailedError` - Install/uninstall/update failed
- `PackageManagerNotAvailableError` - Manager binary not in PATH
- `TimeoutError` - Operation timeout exceeded
- `NetworkError` - Network failures
- `PermissionError` - Insufficient privileges
- `ValidationError` - Data validation failures
- `CancellationError` - User cancelled operation
- `DependencyError` - Dependency resolution failures
- `CacheError` - Cache operation failures

Always include context: package name, manager, operation type.

## Adding New Package Managers

Follow these steps:
1. Add enum value to `PackageManager` in `core/models.py`
2. Implement parser method in `PackageManagerService` (e.g., `_get_<manager>_installed()`)
3. Add command mappings in `install_package()` and `uninstall_package()` methods
4. Update default configuration in `core/config.py`
5. Add validation in `SystemUtils.validate_package_manager()`

## System Utilities (utils/system_utils.py)

**SystemUtils static methods:**
- `is_command_available(command)` - Check if command exists in PATH
- `get_command_version(command, version_flag)` - Extract version info
- `run_command(command, timeout)` - Execute with timeout, return stdout/stderr/returncode
- `check_admin_privileges()` - Windows admin detection via ctypes
- `get_system_info()` - Platform, architecture, Python version
- `validate_package_manager(manager)` - Full availability check
- `elevate_privileges()` - Windows UAC elevation

**PathManager class:**
- Manages temporary files and log file paths
- Automatic directory creation

## Code Style

- Use type hints for all function parameters and return values
- Use `@dataclass` decorator for data structures
- Follow PEP 8 conventions
- Document complex parsing logic with inline comments
- Type hints already present throughout codebase

## System Requirements

- Python 3.11+
- Windows 10/11 (primary target, cross-platform design)
- PyQt6 (for GUI)
- At least one package manager:
  - WinGet (recommended, built into Windows 11)
  - Chocolatey (optional)
  - Pip (included with Python)
  - NPM (optional, requires Node.js)

## Important Files to Read First

1. **WARP.md** - Comprehensive development guidance (more detailed than this file)
2. **core/models.py** - All data structures and enums
3. **services/package_service.py** - Core business logic and package manager integrations
4. **main.py** - Entry point and CLI interface
5. **gui_tkinter.py** - Current GUI implementation (Tkinter-based fallback)

## Known Architectural Decisions

- Threading approach chosen for non-blocking operations (must migrate to QThread for PyQt6)
- XDG Base Directory spec used despite Windows target (cross-platform consideration)
- Each package manager has dedicated parsing logic (no generic parser due to format differences)
- Progress callbacks used instead of polling for status updates
- Configuration uses deep merge strategy for user settings vs defaults
