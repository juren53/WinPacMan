# WinPacMan User Guide

## Overview
WinPacMan is a unified Windows package manager that provides a single interface for managing packages across WinGet, Chocolatey, Pip, and NPM.

## Getting Started

### Installation
- Python 3.11+ required
- PyQt6 for modern UI
- Virtual environment recommended

### First Launch
1. Launch WinPacMan
2. Select package manager from dropdown
3. Choose between "Installed" and "Available" tabs
4. Search or browse packages

## Main Interface

### Package Manager Selection
- **All Packages**: Shows packages from all managers
- **WinGet**: Windows Package Manager packages
- **Chocolatey**: Chocolatey community packages
- **Pip**: Python packages
- **NPM**: Node.js packages

### Tabs
- **Installed**: View currently installed packages
- **Available**: Search and browse available packages

### Package Actions
Right-click any package for:
- **Install**: Install selected package
- **Uninstall**: Remove installed package
- **Show Details**: View package information

## Package Operations

### Installing Packages
1. Switch to "Available" tab
2. Search for desired package
3. Double-click or right-click → Install
4. Monitor progress in status bar
5. Review results in verbose output (if enabled)

### Uninstalling Packages
1. Switch to "Installed" tab
2. Find package to remove
3. Double-click or right-click → Uninstall
4. Confirm removal
5. Monitor progress

### Package Search
- **Basic Search**: Type in search box for instant filtering
- **Real-time Results**: Results update as you type
- **Multi-manager**: Searches across all selected package managers

## Configuration

### Settings Location
Configuration files are stored in XDG-compliant locations:
- **Windows**: `%APPDATA%\Local\winpacman\`
- **Config**: `config.json` - Application settings
- **Data**: Package metadata cache

### View Configuration
Access via **Config → View Configuration** to see:
- Current settings
- Cache statistics
- Package manager status

### Verbose Output
Enable via **View → Verbose Output** to see:
- Detailed package manager commands
- Real-time operation output
- Error messages and troubleshooting

## Package Managers

### WinGet
- **Source**: Microsoft's official package manager
- **Pros**: Modern, well-maintained, Microsoft curated
- **Commands**: `winget install`, `winget uninstall`

### Chocolatey
- **Source**: Community-driven package manager
- **Pros**: Large package library, mature ecosystem
- **Commands**: `choco install`, `choco uninstall`

### Pip
- **Source**: Python package installer
- **Pros**: Essential for Python development
- **Commands**: `pip install`, `pip uninstall`

### NPM
- **Source**: Node.js package manager
- **Pros**: JavaScript/Node.js ecosystem
- **Commands**: `npm install -g`, `npm uninstall -g`

## Tips and Tricks

### Performance
- Use search instead of browsing for large repositories
- Enable metadata cache updates regularly
- Restart WinPacMan if operations seem slow

### Troubleshooting
- Check package manager availability in Config → View Configuration
- Enable Verbose Output for detailed error information
- Ensure package managers are in system PATH
- Run as administrator if installations fail

### Best Practices
- Keep package managers updated
- Use WinGet for modern Windows applications
- Use Chocolatey for legacy software
- Use Pip/NPM for development tools