"""
PyQt6-based GUI for WinPacMan with Windows 11 Fluent Design.

This is the main entry point for the PyQt6 GUI. It uses QThread workers
for non-blocking package operations and modern Fluent Design components.
"""

import sys
from PyQt6.QtWidgets import QApplication

from ui.views.main_window import WinPacManMainWindow


def main():
    """Main entry point for PyQt6 GUI."""
    # Create QApplication
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("WinPacMan")
    app.setOrganizationName("WinPacMan")

    # Create and show main window
    window = WinPacManMainWindow()
    window.show()

    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
