# PyQt6 and PyQt-Fluent-Widgets Compatibility Issue

**Date:** 2025-12-26
**Issue:** Segmentation fault when using PyQt-Fluent-Widgets with PyQt6
**Status:** RESOLVED

## Problem Description

When attempting to use `FluentWindow` from `qfluentwidgets` (PyQt-Fluent-Widgets library) with PyQt6, the application would launch but immediately crash with a segmentation fault. The window would not display at all.

### Symptoms
- Clean launch (no Python errors)
- Immediate segmentation fault
- No window displayed
- No error traceback

### Root Cause

PyQt-Fluent-Widgets is built specifically for **PyQt5**, not PyQt6. According to the package metadata:

```bash
pip show PyQt-Fluent-Widgets
# Summary: A fluent design widgets library based on PyQt5
```

The library is fundamentally incompatible with PyQt6 due to differences in the Qt bindings between PyQt5 and PyQt6.

## Investigation Steps

1. Created debug script (`gui_pyqt6_debug.py`) to isolate the crash point
2. Tested basic PyQt6 functionality (QApplication) - PASSED
3. Tested FluentWindow instantiation - FAILED with segfault
4. Checked package metadata - discovered PyQt5 dependency

## Solution

Migrated from PyQt-Fluent-Widgets to **standard PyQt6 widgets** with custom stylesheets.

### Changes Made

#### ui/views/main_window.py

**Before:**
```python
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    PushButton, ComboBox, ProgressBar, InfoBar, setTheme, Theme
)

class WinPacManMainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.addSubInterface(widget, FluentIcon.LIBRARY, "Packages")
        self.setMicaEffectEnabled(True)
```

**After:**
```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QProgressBar, QStatusBar
)

class WinPacManMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setCentralWidget(widget)
        self.setStyleSheet(...)  # Custom styling
```

### Widget Replacements

| FluentWidget | Standard PyQt6 | Notes |
|--------------|----------------|-------|
| `FluentWindow` | `QMainWindow` | Base class change |
| `PushButton` | `QPushButton` | Standard button |
| `ComboBox` | `QComboBox` | Standard combo box |
| `ProgressBar` | `QProgressBar` | Standard progress bar |
| `InfoBar` | `QMessageBox` | Dialog-based notifications |
| `setTheme()` | `setStyleSheet()` | Custom CSS styling |
| `addSubInterface()` | `setCentralWidget()` | Layout management |
| `FluentIcon.*` | Removed | Text-only buttons for now |

### Styling Approach

Implemented custom Qt stylesheets to maintain a modern Windows 11-like appearance:

- **Light theme**: Blue accent buttons (#0078d4), clean styling
- **Dark theme**: Dark background (#1e1e1e), light text, blue accents

## Trade-offs

### Lost Features
- Fluent Design icons (FluentIcon.*)
- Mica effect (Windows 11 translucent background)
- Advanced navigation components
- Toast-style InfoBar notifications

### Gained Benefits
- **Full PyQt6 compatibility** - no segmentation faults
- **Better long-term stability** - using official Qt widgets
- **Simpler dependency chain** - fewer third-party libraries
- **Full control** - custom styling as needed

## Future Considerations

### Option 1: Wait for PyQt6-Fluent-Widgets
Monitor for a potential PyQt6 version of the Fluent Widgets library. As of December 2025, no official PyQt6 version exists.

### Option 2: Enhance Custom Styling
Gradually improve the custom stylesheet to more closely match Windows 11 Fluent Design:
- Add custom icon resources
- Implement rounded corners and shadows
- Create custom notification system (toast-style)
- Add subtle animations

### Option 3: Use Qt Designer
Create `.ui` files with Qt Designer for more sophisticated layouts and visual design.

## Lessons Learned

1. **Always verify library compatibility** before committing to a UI framework
2. **Check package metadata** (`pip show`) to understand dependencies
3. **PyQt5 and PyQt6 are NOT interchangeable** - bindings differ significantly
4. **Standard widgets are reliable** - they may be less flashy but they always work
5. **Custom stylesheets are powerful** - can achieve modern looks without third-party libraries

## References

- PyQt-Fluent-Widgets GitHub: https://github.com/zhiyiYo/PyQt-Fluent-Widgets
- PyQt6 Documentation: https://www.riverbankcomputing.com/static/Docs/PyQt6/
- Qt Stylesheets: https://doc.qt.io/qt-6/stylesheet-reference.html

## Testing Results

After migration to standard PyQt6 widgets:
- Window launches successfully
- No segmentation faults
- All functionality works as expected
- Responsive UI with QThread workers
- Progress updates working correctly

**Status:** Issue resolved, Phase 2 ready for manual testing
