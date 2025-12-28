# Plan: Markdown-Based Help System for WinPacMan

### Overview
Based on analysis of SysMon's sophisticated markdown implementation, this plan outlines how to implement GitHub-style markdown rendering for WinPacMan's Help system, replacing current basic dialogs with professional, styled HTML content.

### Current State Analysis

**Existing Help Implementation** (`ui/views/main_window.py`):
- `show_user_guide()` - Basic placeholder with QMessageBox
- `show_changelog()` - Displays raw markdown in QTextEdit with monospace font
- `show_about()` - Simple HTML in QMessageBox
- Uses QTextEdit for changelog (shows raw markdown syntax)
- Missing: QTextBrowser import, markdown libraries, documentation files

### Implementation Strategy

#### Phase 1: Dependencies and Infrastructure

**1. Update `requirements.txt`**:
```txt
# Add markdown rendering dependencies
markdown>=3.4.0
pygments>=2.15.0
```

**2. Add PyQt6 Imports** (`ui/views/main_window.py`, line 8):
```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QStatusBar, QApplication,
    QInputDialog, QDialog, QDialogButtonBox, QCheckBox, QTextEdit,
    QMenuBar, QMenu, QLineEdit, QTabWidget, QRadioButton, QButtonGroup,
    QTextBrowser  # ADD THIS
)
```

**3. Add Markdown Imports** (after existing imports, around line 27):
```python
import markdown
from markdown.extensions import fenced_code, tables, nl2br, sane_lists
from pygments.formatters import HtmlFormatter
import os
import re
```

#### Phase 2: Documentation Structure

**Create `docs/` directory** with markdown files:

**`docs/user-guide.md`**:
```markdown
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
```

**`docs/keyboard-shortcuts.md`**:
```markdown
# WinPacMan Keyboard Shortcuts

## Application Shortcuts

### File Menu
- **Ctrl+Q**: Exit WinPacMan

### View Menu
- **Ctrl+V**: Toggle Verbose Output
- **Tab**: Switch between Installed/Available tabs
- **Ctrl+Tab**: Cycle through package manager tabs

### Navigation
- **↑/↓ Arrow Keys**: Navigate package list
- **Enter**: Install/Uninstall selected package
- **Escape**: Close current dialog
- **F5**: Refresh package list

### Search
- **Ctrl+F**: Focus search box
- **Ctrl+L**: Clear search
- **Escape**: Clear search and deselect

## Package Operations

### Quick Actions
- **Double-click**: Install/Uninstall package
- **Right-click**: Show context menu
- **Ctrl+Enter**: Install package (from Available tab)
- **Ctrl+Delete**: Uninstall package (from Installed tab)

### Selection
- **Ctrl+A**: Select all packages
- **Ctrl+Click**: Multi-select packages
- **Shift+Click**: Range selection
- **Space**: Toggle package selection

## Interface Navigation

### Menu Access
- **Alt+F**: File menu
- **Alt+C**: Config menu
- **Alt+V**: View menu
- **Alt+H**: Help menu

### Dialog Controls
- **Enter**: Confirm dialog action
- **Escape**: Cancel/Close dialog
- **Tab**: Navigate dialog controls
- **Shift+Tab**: Reverse navigation

## Package Manager Tabs

### Quick Switching
- **Ctrl+1**: All Packages
- **Ctrl+2**: WinGet
- **Ctrl+3**: Chocolatey
- **Ctrl+4**: Pip
- **Ctrl+5**: NPM

### View Modes
- **Ctrl+I**: Installed packages
- **Ctrl+A**: Available packages

## Advanced Features

### Search Filters
- **Ctrl+R**: Search by package name
- **Ctrl+T**: Search by description
- **Ctrl+S**: Search by source/manager

### Bulk Operations
- **Ctrl+Shift+I**: Install selected packages
- **Ctrl+Shift+U**: Uninstall selected packages
- **Delete**: Remove selected items from list

## Tips

### Productivity
- Use keyboard shortcuts for faster navigation
- Enable Verbose Output for debugging
- Use search to quickly find packages
- Bookmark frequently used packages

### Troubleshooting
- Check verbose output for error details
- Verify package manager availability
- Ensure network connectivity for package operations
- Run as administrator if installations fail
```

#### Phase 3: Core Implementation

**1. Add Helper Methods** (`ui/views/main_window.py`, after `show_configuration()`):

```python
def get_dialog_theme_colors(self) -> dict:
    """Get theme-appropriate colors for dialogs."""
    # Check if dark theme (implementation needed based on Qt palette)
    palette = self.palette()
    bg_color = palette.color(palette.ColorRole.Window)
    bg_brightness = (bg_color.red() + bg_color.green() + bg_color.blue()) / 3
    is_dark_theme = bg_brightness < 128
    
    if is_dark_theme:
        return {
            'background': '#1e1e1e',
            'text': '#c8c8c8',
            'selection_bg': '#0078d7',
            'selection_text': 'white'
        }
    else:
        return {
            'background': '#f8f9fa', 
            'text': '#212529',
            'selection_bg': '#0078d7',
            'selection_text': 'white'
        }

def is_dark_theme(self) -> bool:
    """Check if application is using dark theme."""
    palette = self.palette()
    bg_color = palette.color(palette.ColorRole.Window)
    return bg_color.lightness() < 128

def render_markdown_to_html(self, markdown_text: str) -> str:
    """
    Convert markdown text to GitHub-style HTML with syntax highlighting.
    
    Args:
        markdown_text: Raw markdown content as string
        
    Returns:
        Fully styled HTML string with CSS
    """
    # Get theme colors for styling
    theme_colors = self.get_dialog_theme_colors()
    
    # Configure markdown extensions (GitHub-flavored)
    extensions = [
        'fenced_code',      # ```code blocks```
        'tables',           # GitHub markdown tables
        'nl2br',            # Convert newlines to <br>
        'sane_lists',       # Better list handling
        'codehilite',       # Syntax highlighting
        'toc',              # Table of contents support
    ]
    
    # Configure extension settings
    extension_configs = {
        'codehilite': {
            'css_class': 'highlight',
            'linenums': False,
            'guess_lang': True
        }
    }
    
    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=extensions,
        extension_configs=extension_configs
    )
    html_content = md.convert(markdown_text)
    
    # Get Pygments CSS for syntax highlighting
    formatter = HtmlFormatter(style='github-dark' if self.is_dark_theme() else 'github')
    pygments_css = formatter.get_style_defs('.highlight')
    
    # Build complete HTML document with GitHub-style CSS
    full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* Base styles */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica', 'Arial', sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: {theme_colors['text']};
            background-color: {theme_colors['background']};
            padding: 16px;
            margin: 0;
        }}
        
        /* Headers */
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
            border-bottom: 1px solid {'#30363d' if self.is_dark_theme() else '#d8dee4'};
            padding-bottom: 8px;
        }}
        
        h1 {{ font-size: 2em; }}
        h2 {{ font-size: 1.5em; }}
        h3 {{ font-size: 1.25em; }}
        
        /* Paragraphs and text */
        p {{ margin-top: 0; margin-bottom: 16px; }}
        
        strong {{ font-weight: 600; }}
        em {{ font-style: italic; }}
        
        /* Links */
        a {{
            color: #58a6ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        
        /* Lists */
        ul, ol {{
            margin-top: 0;
            margin-bottom: 16px;
            padding-left: 2em;
        }}
        
        li {{ margin-top: 0.25em; }}
        
        /* Code */
        code {{
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            background-color: {'rgba(110,118,129,0.4)' if self.is_dark_theme() else 'rgba(175,184,193,0.2)'};
            border-radius: 6px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }}
        
        /* Code blocks */
        pre {{
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            background-color: {'#161b22' if self.is_dark_theme() else '#f6f8fa'};
            border-radius: 6px;
            margin-bottom: 16px;
        }}
        
        pre code {{
            display: inline;
            padding: 0;
            margin: 0;
            overflow: visible;
            line-height: inherit;
            background-color: transparent;
            border: 0;
        }}
        
        /* Tables */
        table {{
            border-spacing: 0;
            border-collapse: collapse;
            margin-top: 0;
            margin-bottom: 16px;
            width: 100%;
        }}
        
        table th {{
            font-weight: 600;
            padding: 6px 13px;
            border: 1px solid {'#30363d' if self.is_dark_theme() else '#d0d7de'};
            background-color: {'#161b22' if self.is_dark_theme() else '#f6f8fa'};
        }}
        
        table td {{
            padding: 6px 13px;
            border: 1px solid {'#30363d' if self.is_dark_theme() else '#d0d7de'};
        }}
        
        table tr:nth-child(2n) {{
            background-color: {'#0d1117' if self.is_dark_theme() else '#f6f8fa'};
        }}
        
        /* Blockquotes */
        blockquote {{
            padding: 0 1em;
            color: {'#8b949e' if self.is_dark_theme() else '#57606a'};
            border-left: 0.25em solid {'#30363d' if self.is_dark_theme() else '#d0d7de'};
            margin: 0 0 16px 0;
        }}
        
        /* Horizontal rules */
        hr {{
            height: 0.25em;
            padding: 0;
            margin: 24px 0;
            background-color: {'#30363d' if self.is_dark_theme() else '#d0d7de'};
            border: 0;
        }}
        
        /* Pygments syntax highlighting */
        {pygments_css}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""
    
    return full_html
```

**2. Update Help Methods**:

```python
def show_user_guide(self):
    """Show user guide dialog with rendered markdown."""
    user_guide_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs', 'user-guide.md')
    
    try:
        with open(user_guide_path, 'r', encoding='utf-8', errors='replace') as f:
            markdown_content = f.read()
    except Exception as e:
        markdown_content = f"""# WinPacMan User Guide
        
Unable to load user guide file.

Error: {str(e)}

Please check docs/user-guide.md file in WinPacMan repository.

For now, please refer to README.md and CLAUDE.md files in project repository."""
    
    # Convert markdown to HTML
    html_content = self.render_markdown_to_html(markdown_content)
    
    # Create dialog
    dialog = QDialog(self)
    dialog.setWindowTitle("WinPacMan User Guide")
    dialog.setModal(True)
    dialog.resize(1000, 750)
    
    # Use QTextBrowser for HTML rendering
    text_browser = QTextBrowser()
    text_browser.setReadOnly(True)
    text_browser.setOpenExternalLinks(True)  # Allow clicking links
    text_browser.setHtml(html_content)
    text_browser.setStyleSheet("QTextBrowser { border: none; }")
    
    # Close button
    close_button = QPushButton("Close")
    close_button.clicked.connect(dialog.accept)
    
    # Layout
    layout = QVBoxLayout(dialog)
    layout.addWidget(text_browser)
    
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    layout.addLayout(button_layout)
    
    dialog.exec()

def show_changelog(self):
    """Display CHANGELOG.md with rendered markdown."""
    changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "CHANGELOG.md")
    
    if not os.path.exists(changelog_path):
        QMessageBox.warning(self, "Change Log", "CHANGELOG.md file not found.")
        return
    
    try:
        with open(changelog_path, 'r', encoding='utf-8', errors='replace') as f:
            markdown_content = f.read()
    except Exception as e:
        markdown_content = f"""# Change Log
        
Unable to load CHANGELOG.md file.

Error: {str(e)}"""
    
    # Convert markdown to HTML
    html_content = self.render_markdown_to_html(markdown_content)
    
    # Create dialog
    dialog = QDialog(self)
    dialog.setWindowTitle("WinPacMan Change Log")
    dialog.setModal(True)
    dialog.resize(900, 700)
    
    # Use QTextBrowser for HTML rendering
    text_browser = QTextBrowser()
    text_browser.setReadOnly(True)
    text_browser.setOpenExternalLinks(True)
    text_browser.setHtml(html_content)
    text_browser.setStyleSheet("QTextBrowser { border: none; }")
    
    # Close button
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    button_box.rejected.connect(dialog.reject)
    
    # Layout
    layout = QVBoxLayout(dialog)
    layout.addWidget(text_browser)
    layout.addWidget(button_box)
    
    dialog.exec()

def show_keyboard_shortcuts(self):
    """Show keyboard shortcuts dialog with rendered markdown."""
    # Add keyboard shortcuts action to menu first
    shortcuts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs', 'keyboard-shortcuts.md')
    
    try:
        with open(shortcuts_path, 'r', encoding='utf-8', errors='replace') as f:
            markdown_content = f.read()
    except Exception as e:
        # Fallback to embedded content
        markdown_content = f"""# WinPacMan Keyboard Shortcuts
        
Unable to load keyboard shortcuts file.

Error: {str(e)}

## Application Shortcuts
- **Ctrl+Q**: Exit WinPacMan
- **F5**: Refresh package list
- **Tab**: Switch between Installed/Available tabs

## Navigation
- **↑/↓ Arrow Keys**: Navigate package list
- **Enter**: Install/Uninstall selected package
- **Escape**: Close current dialog

## Search
- **Ctrl+F**: Focus search box
- **Ctrl+L**: Clear search"""
    
    # Convert markdown to HTML
    html_content = self.render_markdown_to_html(markdown_content)
    
    # Create dialog
    dialog = QDialog(self)
    dialog.setWindowTitle("WinPacMan Keyboard Shortcuts")
    dialog.setModal(True)
    dialog.resize(800, 650)
    
    # Use QTextBrowser for HTML rendering
    text_browser = QTextBrowser()
    text_browser.setReadOnly(True)
    text_browser.setOpenExternalLinks(True)
    text_browser.setHtml(html_content)
    text_browser.setStyleSheet("QTextBrowser { border: none; }")
    
    # Close button
    close_button = QPushButton("Close")
    close_button.clicked.connect(dialog.accept)
    
    # Layout
    layout = QVBoxLayout(dialog)
    layout.addWidget(text_browser)
    
    button_layout = QHBoxLayout()
    button_layout.addStretch()
    button_layout.addWidget(close_button)
    button_layout.addStretch()
    layout.addLayout(button_layout)
    
    dialog.exec()
```

**3. Update Menu Creation** (`create_menu_bar()` method, around line 310):

```python
# Help menu
help_menu = menubar.addMenu("&Help")

user_guide_action = QAction("&User Guide", self)
user_guide_action.triggered.connect(self.show_user_guide)
help_menu.addAction(user_guide_action)

changelog_action = QAction("&Change Log", self)
changelog_action.triggered.connect(self.show_changelog)
help_menu.addAction(changelog_action)

shortcuts_action = QAction("&Keyboard Shortcuts", self)
shortcuts_action.triggered.connect(self.show_keyboard_shortcuts)
help_menu.addAction(shortcuts_action)

help_menu.addSeparator()

about_action = QAction("&About", self)
about_action.triggered.connect(self.show_about)
help_menu.addAction(about_action)
```

### Files to Create/Modify

#### New Files:
1. **`docs/user-guide.md`** - Comprehensive user documentation
2. **`docs/keyboard-shortcuts.md`** - Keyboard shortcuts reference

#### Modified Files:
1. **`requirements.txt`** - Add markdown and pygments dependencies
2. **`ui/views/main_window.py`** - 
   - Add imports (QTextBrowser, markdown, pygments)
   - Add helper methods (~200 lines)
   - Update help methods (~50 lines modified)
   - Update menu creation (~5 lines)

### Expected Results

#### Before (Current):
- User Guide: Basic QMessageBox placeholder
- Change Log: Raw markdown in QTextEdit with monospace font
- Keyboard Shortcuts: Not available
- About: Simple HTML in QMessageBox

#### After (Implemented):
- User Guide: Professional markdown with GitHub styling, syntax highlighting, theme awareness
- Change Log: Rendered markdown with proper headers, lists, code blocks
- Keyboard Shortcuts: Comprehensive reference with organized sections
- All dialogs: Theme-aware colors, clickable links, proper typography

### Technical Details

#### Key Features:
1. **GitHub-Style Rendering**: Professional typography and spacing
2. **Syntax Highlighting**: Code blocks with language-specific highlighting
3. **Theme Awareness**: Auto-detects dark/light mode and adjusts colors
4. **External Links**: Clickable URLs in documentation
5. **Error Handling**: Graceful fallbacks for missing files
6. **Consistent Styling**: All help dialogs use same design system

#### Performance Impact:
- **Minimal**: Markdown processing occurs on-demand when dialogs open
- **No Startup Delay**: Libraries loaded only when needed
- **Memory Efficient**: QTextBrowser handles large documents well

#### Dependencies:
- **markdown**: Lightweight (~200KB), BSD license
- **pygments**: Syntax highlighting (~1.5MB), BSD license
- Both are standard, well-maintained Python libraries

### Implementation Timeline

**Day 1**: Setup dependencies and create markdown files
**Day 2**: Implement core rendering methods  
**Day 3**: Update help dialog methods
**Day 4**: Testing and refinement

### Testing Strategy

1. **Basic Rendering**: Verify markdown converts to HTML properly
2. **Theme Testing**: Test dark/light mode adaptation
3. **File Loading**: Test with missing/corrupted markdown files
4. **Link Functionality**: Verify external links are clickable
5. **Performance**: Test with large markdown files
6. **Accessibility**: Ensure proper keyboard navigation in dialogs

### Future Enhancements

Not in scope for initial implementation:
- Search within help dialogs
- Print/export help content
- Embedded images in markdown
- Custom CSS themes
- Table of contents navigation
- Collapsible sections

This plan provides a comprehensive, professional help system that significantly improves user experience while maintaining existing WinPacMan architecture and coding standards.