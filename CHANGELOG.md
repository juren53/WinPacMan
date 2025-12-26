# Changelog for WinPacMan

All notable changes to WinPacMan are documented here. This project follows [Semantic Versioning](https://semver.org/).

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
