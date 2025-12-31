"""
PyQt6-based GUI for WinPacMan with Windows 11 Fluent Design.

This is the main entry point for the PyQt6 GUI. It uses QThread workers
for non-blocking package operations and modern Fluent Design components.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox

from ui.views.main_window import WinPacManMainWindow
from utils.system_utils import SingleInstanceChecker


def main():
    """Main entry point for PyQt6 GUI."""
    # Check if another instance is already running
    instance_checker = SingleInstanceChecker("WinPacMan")

    if instance_checker.is_already_running():
        # Create a minimal QApplication just to show the message box
        app = QApplication(sys.argv)
        QMessageBox.warning(
            None,
            "WinPacMan Already Running",
            "Another instance of WinPacMan is already running.\n\n"
            "Please use the existing window or close it before starting a new instance."
        )
        return 1  # Exit with error code

    # Create QApplication
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("WinPacMan")
    app.setOrganizationName("WinPacMan")

    # Create and show main window
    window = WinPacManMainWindow()
    window.show()

    # Start event loop
    try:
        return app.exec()
    finally:
        # Release the mutex when application exits
        instance_checker.release()


if __name__ == "__main__":
    sys.exit(main())
