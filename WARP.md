# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

WinPacMan is a Python-based unified package manager for Windows that provides a single interface for managing packages across WinGet, Chocolatey, Pip, and NPM. The project is built with PyQt6 for the GUI (in development) and uses a modular, layered architecture.

**Current Status:** The core logic and CLI interface are functional. The PyQt6 GUI components are planned but not yet fully implemented.

## Development Commands

### Environment Setup
```powershell
# Create and activate virtual environment
python -m venv winpacman_env
.\winpacman_env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```powershell
# Interactive mode (default)
python main.py

# List packages from a specific manager
python main.py list winget
python main.py list choco

# Search for packages
python main.py search winget <query>

# Show system info and available package managers
python main.py info

# Show configuration
python main.py config

# Test threading functionality
python main.py test-threading
```

### Testing
No formal test suite is currently implemented. When adding tests:
- Use pytest as the testing framework
- Use pytest-qt for PyQt6 component testing
- Test files should follow the pattern `test_*.py` or `*_test.py`

### Code Quality
Development tools are listed in requirements.txt but not installed by default:
- **black**: Code formatting (when implemented, run: `black .`)
- **mypy**: Type checking (when implemented, run: `mypy .`)

## Architecture Overview

### Layered Architecture
The project follows a clean separation of concerns with these layers:

```
main.py           → Entry point (console interface currently)
├─ services/      → Business logic & orchestration
│  ├─ package_service.py      → Package operations, parsing output
│  └─ settings_service.py     → Settings management
├─ core/          → Domain models & configuration
│  ├─ models.py               → Data classes (Package, PackageManager, etc.)
│  ├─ config.py               → XDG-compliant config management
│  └─ exceptions.py           → Custom exception hierarchy
├─ utils/         → System utilities
│  └─ system_utils.py         → Command execution, version checking
└─ ui/            → User interface (mostly placeholder)
   ├─ components/ → Reusable UI widgets
   └─ views/      → Main application views
```

### Key Design Patterns

**Threading for Non-Blocking Operations:**
- All package manager operations (list, install, uninstall) use background threads
- `PackageOperationWorker` class wraps operations in threads
- Progress callbacks are used to report status without blocking the UI
- **Critical**: When implementing PyQt6 UI, use `QThread` instead of Python's `threading.Thread` for proper Qt integration (see notes/How to capture and parse winget output into a PyQt table.md)

**Configuration Management:**
- XDG Base Directory specification is used for config/data/cache locations
- Config files stored in: `~/.config/winpacman/` (or `%APPDATA%/Local/winpacman/`)
- Data stored in: `~/.local/share/winpacman/`
- Cache stored in: `~/.cache/winpacman/`
- ConfigManager provides dot-notation access: `config_manager.get_config_value('ui.theme')`

**Package Manager Abstraction:**
- Each package manager has dedicated parsing logic in `PackageManagerService`
- Output parsing is tailored per manager (WinGet uses regex, Pip uses JSON, etc.)
- All return standardized `Package` objects

### Important Implementation Details

**WinGet Output Parsing:**
- WinGet output format: `Name | Id | Version | Available | Source`
- Split on 2+ whitespace characters: `re.split(r'\s{2,}', line)`
- Must skip header lines (typically 2-3 lines)
- Use `--accept-source-agreements` flag to avoid interactive prompts
- Handle encoding issues by filtering control characters

**Chocolatey Parsing:**
- Format: `package_name version`
- Skip summary line containing "packages installed"

**Pip Parsing:**
- Use `pip list --format=json` for structured output
- No regex parsing needed

**NPM Parsing:**
- Use `npm list -g --json --depth=0` for structured output
- Parse `dependencies` object from JSON

## Data Models

**Key Enums:**
- `PackageManager`: WINGET, CHOCOLATEY, PIP, NPM
- `PackageStatus`: INSTALLED, AVAILABLE, OUTDATED, INSTALLING, UNINSTALLING, UPDATING, FAILED
- `OperationType`: INSTALL, UNINSTALL, UPDATE, SEARCH, LIST
- `OperationStage`: QUEUED, DOWNLOADING, INSTALLING, CONFIGURING, COMPLETE, FAILED, CANCELLED

**Core Classes:**
- `Package`: Represents a software package with name, version, manager, status, etc.
- `OperationProgress`: Tracks progress of package operations (percentage, ETA, etc.)
- `OperationResult`: Result of completed operations (success/failure, message, details)
- `SearchQuery`: Structured search query with filters

## Exception Handling

Custom exception hierarchy in `core/exceptions.py`:
- `PackageManagerError` - Base exception
  - `PackageNotFoundError` - Specific package not found
  - `OperationFailedError` - Operation failed (install/uninstall/etc.)
  - `PackageManagerNotAvailableError` - Manager binary not in PATH
  - `TimeoutError` - Operation exceeded timeout
  - `NetworkError` - Network-related failures
  - `PermissionError` - Insufficient privileges
  - `ValidationError` - Data validation failures
  - `CancellationError` - User cancelled operation
  - `DependencyError` - Dependency resolution failures
  - `CacheError` - Cache operation failures

All exceptions include structured error codes and optional details dictionary.

## UI Development Notes

**PyQt6 Requirements:**
- Threading MUST use `QThread` not `threading.Thread` for Qt signal/slot compatibility
- Worker threads emit `pyqtSignal` to communicate with UI thread
- Use worker pattern to prevent UI freezing during long operations
- Reference: `notes/How to capture and parse winget output into a PyQt table.md`

**Planned UI Framework:**
- Modern Windows 11-style interface
- Consider using `PyQt-Fluent-Widgets` for Fluent Design System components
- Use SVG icons for DPI scaling
- Frameless window with custom title bar for modern look

## Configuration

Default configuration includes:
- UI settings (theme, window geometry)
- Package manager settings (enabled status, binary paths, auto-update)
- Advanced settings (auto-refresh, cache duration, max concurrent operations, log level)

Access configuration:
```python
from core.config import config_manager
config = config_manager.load_config()
config_manager.set_config_value('ui.theme', 'dark')
```

## System Requirements

- Python 3.11+
- Windows 10/11
- PyQt6 (for GUI, currently optional)
- At least one package manager installed:
  - WinGet (recommended, built into Windows 11)
  - Chocolatey (optional)
  - Pip (included with Python)
  - NPM (optional, requires Node.js)

## Development Guidelines

**Adding New Package Managers:**
1. Add enum value to `PackageManager` in `core/models.py`
2. Implement parser method in `PackageManagerService` (e.g., `_get_<manager>_installed()`)
3. Add command mappings in `install_package()` and `uninstall_package()`
4. Update default configuration in `core/config.py`
5. Add validation in `SystemUtils.validate_package_manager()`

**Threading Best Practices:**
- Always use `PackageOperationWorker` for long-running operations
- Implement progress callbacks for user feedback
- Set appropriate timeouts (list: 60s, install: 300s, uninstall: 180s)
- Handle `subprocess.TimeoutExpired` exceptions

**Error Handling:**
- Use specific exception types from `core/exceptions.py`
- Always include context (package name, manager, operation type)
- Log errors appropriately (when logging is implemented)
- Provide user-friendly error messages

**Code Style:**
- Use type hints for all function parameters and return values
- Use dataclasses for data structures (`@dataclass` decorator)
- Follow PEP 8 conventions
- Document complex parsing logic with inline comments
