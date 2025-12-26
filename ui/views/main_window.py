"""
Main application window for WinPacMan.

Provides the main user interface for WinPacMan using PyQt6
with modern styling.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QProgressBar, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont
from typing import List, Optional

from core.models import PackageManager, Package
from services.package_service import PackageManagerService
from services.settings_service import SettingsService
from ui.workers.package_worker import PackageListWorker
from ui.components.package_table import PackageTableWidget


class WinPacManMainWindow(QMainWindow):
    """
    Main application window with modern styling.

    Features:
    - Package manager selection
    - Non-blocking package operations via QThread workers
    - Real-time progress updates via signals
    - Color-coded package display
    """

    def __init__(self):
        super().__init__()

        # Services
        self.package_service = PackageManagerService()
        self.settings_service = SettingsService()

        # State
        self.current_packages: List[Package] = []
        self.operation_in_progress = False
        self.current_worker: Optional[PackageListWorker] = None

        # Setup
        self.init_window()
        self.init_ui()
        self.apply_theme()

    def init_window(self):
        """Initialize window properties."""
        self.setWindowTitle("WinPacMan - Windows Package Manager")
        self.resize(1000, 700)

    def init_ui(self):
        """Setup user interface."""
        # Create main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Control panel
        control_layout = self.create_control_panel()
        main_layout.addLayout(control_layout)

        # Package table
        self.package_table = PackageTableWidget()
        self.package_table.package_double_clicked.connect(
            self.on_package_details
        )
        main_layout.addWidget(self.package_table)

        # Status bar at bottom
        self.create_status_bar()

    def create_control_panel(self) -> QHBoxLayout:
        """Create control panel with manager selector and buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Label
        label = QLabel("Package Manager:")
        layout.addWidget(label)

        # Package manager selector
        self.manager_combo = QComboBox()
        self.manager_combo.addItems(["WinGet", "Chocolatey", "Pip", "NPM"])
        self.manager_combo.setCurrentIndex(0)
        self.manager_combo.setFixedWidth(150)
        self.manager_combo.currentTextChanged.connect(self.on_manager_changed)
        layout.addWidget(self.manager_combo)

        # Spacer
        layout.addStretch()

        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_packages)
        layout.addWidget(self.refresh_btn)

        # Search button (placeholder for Phase 4)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_packages)
        self.search_btn.setEnabled(False)
        layout.addWidget(self.search_btn)

        # Install button (placeholder for Phase 3)
        self.install_btn = QPushButton("Install")
        self.install_btn.clicked.connect(self.install_package)
        self.install_btn.setEnabled(False)
        layout.addWidget(self.install_btn)

        # Uninstall button (placeholder for Phase 3)
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self.uninstall_package)
        self.uninstall_btn.setEnabled(False)
        layout.addWidget(self.uninstall_btn)

        return layout

    def create_status_bar(self):
        """Create status bar with progress indicator."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar (on right side)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def get_selected_manager(self) -> PackageManager:
        """Get currently selected package manager."""
        manager_map = {
            "WinGet": PackageManager.WINGET,
            "Chocolatey": PackageManager.CHOCOLATEY,
            "Pip": PackageManager.PIP,
            "NPM": PackageManager.NPM
        }
        return manager_map[self.manager_combo.currentText()]

    def refresh_packages(self):
        """Refresh package list using QThread worker."""
        print("[MainWindow] refresh_packages called")
        if self.operation_in_progress:
            print("[MainWindow] Operation already in progress, showing warning")
            QMessageBox.warning(
                self,
                "Operation In Progress",
                "Please wait for the current operation to complete."
            )
            return

        manager = self.get_selected_manager()
        print(f"[MainWindow] Selected manager: {manager.value}")

        # Create and configure worker
        print("[MainWindow] Creating PackageListWorker")
        self.current_worker = PackageListWorker(
            self.package_service,
            manager
        )

        # Connect signals
        print("[MainWindow] Connecting worker signals")
        self.current_worker.signals.started.connect(
            lambda: self.on_operation_started(
                f"Refreshing packages from {manager.value}..."
            )
        )
        self.current_worker.signals.progress.connect(self.on_progress_update)
        self.current_worker.signals.packages_loaded.connect(
            self.on_packages_loaded
        )
        self.current_worker.signals.error_occurred.connect(self.on_error)
        self.current_worker.signals.finished.connect(
            self.on_operation_finished
        )

        # Start worker
        print("[MainWindow] Starting worker thread")
        self.current_worker.start()

    def on_manager_changed(self, text: str):
        """Handle package manager selection change."""
        self.package_table.clear_packages()
        self.status_label.setText(f"Selected: {text}")

    def search_packages(self):
        """Search packages (placeholder for Phase 4)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Search functionality will be implemented in Phase 4."
        )

    def install_package(self):
        """Install package (placeholder for Phase 3)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Install functionality will be implemented in Phase 3."
        )

    def uninstall_package(self):
        """Uninstall package (placeholder for Phase 3)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Uninstall functionality will be implemented in Phase 3."
        )

    @pyqtSlot(str)
    def on_operation_started(self, message: str):
        """Handle operation start."""
        print(f"[MainWindow] on_operation_started: {message}")
        self.operation_in_progress = True
        self.disable_controls()
        self.status_label.setText(message)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

    @pyqtSlot(int, int, str)
    def on_progress_update(self, current: int, total: int, message: str):
        """Handle progress update (thread-safe via signal)."""
        print(f"[MainWindow] on_progress_update: {current}/{total} - {message}")
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

        self.status_label.setText(message)

    @pyqtSlot(list)
    def on_packages_loaded(self, packages: List[Package]):
        """Handle loaded packages."""
        print(f"[MainWindow] on_packages_loaded: Received {len(packages)} packages")
        self.current_packages = packages
        self.package_table.set_packages(packages)
        print(f"[MainWindow] Package table updated with {len(packages)} packages")

        # Show success message in status bar
        self.status_label.setText(f"Success: Loaded {len(packages)} packages")

        # Auto-clear success message after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))

    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """Handle error."""
        print(f"[MainWindow] on_error: {error_message}")
        QMessageBox.critical(
            self,
            "Error",
            error_message
        )

    @pyqtSlot()
    def on_operation_finished(self):
        """Handle operation completion."""
        print("[MainWindow] on_operation_finished")
        self.operation_in_progress = False
        self.enable_controls()
        self.progress_bar.setVisible(False)

        # Clean up worker
        if self.current_worker:
            self.current_worker.wait()
            self.current_worker.deleteLater()
            self.current_worker = None

    def on_package_details(self, package: Package):
        """Show package details dialog."""
        QMessageBox.information(
            self,
            "Package Details",
            f"Name: {package.name}\n"
            f"Version: {package.version}\n"
            f"Manager: {package.manager.value}\n"
            f"Description: {package.description or 'N/A'}"
        )

    def disable_controls(self):
        """Disable controls during operation."""
        self.manager_combo.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

    def enable_controls(self):
        """Enable controls after operation."""
        self.manager_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)

    def apply_theme(self):
        """Apply theme from settings."""
        theme = self.settings_service.get_theme()

        # Apply basic stylesheet based on theme
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1984d8;
                }
                QPushButton:disabled {
                    background-color: #2d2d2d;
                    color: #666666;
                }
                QComboBox {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #3d3d3d;
                    padding: 4px;
                }
                QLabel {
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
            """)
        else:
            # Light theme or auto (default PyQt6 styling)
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0078d4;
                    color: #ffffff;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1984d8;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """)
