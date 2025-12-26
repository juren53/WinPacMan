"""
PyQt6-based GUI for WinPacMan with Windows 11 Fluent Design.

This is the main entry point for the PyQt6 GUI. It uses QThread workers
for non-blocking package operations and modern Fluent Design components.
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QProgressBar
from PyQt6.QtCore import Qt, pyqtSlot

from core.models import PackageManager, Package
from services.package_service import PackageManagerService
from services.settings_service import SettingsService
from ui.workers.package_worker import PackageListWorker


class WinPacManWindow(QMainWindow):
    """
    Minimal test window for Phase 1.

    This window tests the QThread worker framework with signal/slot
    communication. Will be replaced with full Fluent Design window in Phase 2.
    """

    def __init__(self):
        super().__init__()

        # Services
        self.package_service = PackageManagerService()
        self.settings_service = SettingsService()

        # State
        self.current_worker = None
        self.current_packages = []

        # Setup window
        self.setup_ui()

    def setup_ui(self):
        """Setup minimal UI for testing."""
        self.setWindowTitle("WinPacMan - PyQt6 Test (Phase 1)")
        self.resize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("WinPacMan - PyQt6 Worker Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Package count label
        self.package_count_label = QLabel("No packages loaded")
        self.package_count_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self.package_count_label)

        # Test button
        self.test_button = QPushButton("Test WinGet List (QThread Worker)")
        self.test_button.clicked.connect(self.test_worker)
        self.test_button.setStyleSheet("padding: 10px; font-size: 14px;")
        layout.addWidget(self.test_button)

        # Add stretch to push everything to top
        layout.addStretch()

    def test_worker(self):
        """Test worker with actual WinGet package listing."""
        if self.current_worker and self.current_worker.isRunning():
            self.status_label.setText("Operation already in progress...")
            return

        # Create worker
        self.current_worker = PackageListWorker(
            self.package_service,
            PackageManager.WINGET
        )

        # Connect signals to slots (EVENT-DRIVEN, NO POLLING!)
        self.current_worker.signals.started.connect(self.on_operation_started)
        self.current_worker.signals.progress.connect(self.on_progress_update)
        self.current_worker.signals.packages_loaded.connect(self.on_packages_loaded)
        self.current_worker.signals.error_occurred.connect(self.on_error)
        self.current_worker.signals.finished.connect(self.on_operation_finished)

        # Start worker
        self.current_worker.start()

    @pyqtSlot()
    def on_operation_started(self):
        """Handle operation start."""
        self.test_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Operation started...")
        self.status_label.setStyleSheet("padding: 10px; color: blue;")

    @pyqtSlot(int, int, str)
    def on_progress_update(self, current: int, total: int, message: str):
        """
        Handle progress update (thread-safe via signal).

        Args:
            current: Current progress value
            total: Total progress value
            message: Progress message
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

        self.status_label.setText(f"Progress: {message}")
        self.status_label.setStyleSheet("padding: 10px; color: blue;")

    @pyqtSlot(list)
    def on_packages_loaded(self, packages: list):
        """
        Handle packages loaded successfully.

        Args:
            packages: List of Package objects
        """
        self.current_packages = packages
        count = len(packages)
        self.package_count_label.setText(
            f"Successfully loaded {count} packages from WinGet!"
        )
        self.package_count_label.setStyleSheet("padding: 10px; color: green; font-weight: bold;")
        self.status_label.setText(f"Completed: Found {count} packages")
        self.status_label.setStyleSheet("padding: 10px; color: green;")

        # Show first few package names as proof
        if packages:
            sample = [pkg.name for pkg in packages[:5]]
            print(f"Sample packages: {sample}")

    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """
        Handle error.

        Args:
            error_message: Error message
        """
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("padding: 10px; color: red; font-weight: bold;")
        print(f"Error occurred: {error_message}")

    @pyqtSlot()
    def on_operation_finished(self):
        """Handle operation completion."""
        self.test_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Clean up worker
        if self.current_worker:
            self.current_worker.wait()  # Wait for thread to finish
            self.current_worker.deleteLater()  # Schedule for deletion
            self.current_worker = None


def main():
    """Main entry point for PyQt6 GUI."""
    # Create QApplication
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("WinPacMan")
    app.setOrganizationName("WinPacMan")

    # Create and show main window
    window = WinPacManWindow()
    window.show()

    # Start event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
