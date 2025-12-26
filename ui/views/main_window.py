"""
Main application window with Windows 11 Fluent Design.

Provides the main user interface for WinPacMan using PyQt6 and
qfluentwidgets for modern Fluent Design styling.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSlot
from qfluentwidgets import (
    FluentWindow, NavigationItemPosition, FluentIcon,
    PushButton, ComboBox, ProgressBar, setTheme, Theme,
    InfoBar, InfoBarPosition
)
from typing import List, Optional

from core.models import PackageManager, Package
from services.package_service import PackageManagerService
from services.settings_service import SettingsService
from ui.workers.package_worker import PackageListWorker
from ui.components.package_table import PackageTableWidget


class WinPacManMainWindow(FluentWindow):
    """
    Main application window with modern Fluent Design.

    Features:
    - Windows 11 Fluent Design styling
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
        self.init_navigation()
        self.apply_theme()

    def init_window(self):
        """Initialize window properties."""
        self.setWindowTitle("WinPacMan - Windows Package Manager")
        self.resize(1000, 700)

        # Try to enable Mica effect (Windows 11 only)
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass  # Mica not available on this system

    def init_navigation(self):
        """Setup navigation interface."""
        # Create packages interface
        self.packages_interface = self.create_packages_interface()

        # Add to navigation
        self.addSubInterface(
            self.packages_interface,
            FluentIcon.LIBRARY,
            "Packages"
        )

    def create_packages_interface(self) -> QWidget:
        """Create main packages interface."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Control panel
        control_layout = self.create_control_panel()
        layout.addLayout(control_layout)

        # Package table
        self.package_table = PackageTableWidget()
        self.package_table.package_double_clicked.connect(
            self.on_package_details
        )
        layout.addWidget(self.package_table)

        # Status bar
        status_layout = self.create_status_bar()
        layout.addLayout(status_layout)

        return widget

    def create_control_panel(self) -> QHBoxLayout:
        """Create control panel with manager selector and buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Label
        label = QLabel("Package Manager:")
        layout.addWidget(label)

        # Package manager selector
        self.manager_combo = ComboBox()
        self.manager_combo.addItems(["WinGet", "Chocolatey", "Pip", "NPM"])
        self.manager_combo.setCurrentIndex(0)
        self.manager_combo.setFixedWidth(150)
        self.manager_combo.currentTextChanged.connect(self.on_manager_changed)
        layout.addWidget(self.manager_combo)

        # Spacer
        layout.addStretch()

        # Refresh button
        self.refresh_btn = PushButton(FluentIcon.SYNC, "Refresh")
        self.refresh_btn.clicked.connect(self.refresh_packages)
        layout.addWidget(self.refresh_btn)

        # Search button (placeholder for Phase 4)
        self.search_btn = PushButton(FluentIcon.SEARCH, "Search")
        self.search_btn.clicked.connect(self.search_packages)
        self.search_btn.setEnabled(False)
        layout.addWidget(self.search_btn)

        # Install button (placeholder for Phase 3)
        self.install_btn = PushButton(FluentIcon.DOWNLOAD, "Install")
        self.install_btn.clicked.connect(self.install_package)
        self.install_btn.setEnabled(False)
        layout.addWidget(self.install_btn)

        # Uninstall button (placeholder for Phase 3)
        self.uninstall_btn = PushButton(FluentIcon.DELETE, "Uninstall")
        self.uninstall_btn.clicked.connect(self.uninstall_package)
        self.uninstall_btn.setEnabled(False)
        layout.addWidget(self.uninstall_btn)

        return layout

    def create_status_bar(self) -> QHBoxLayout:
        """Create status bar with progress indicator."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        # Spacer
        layout.addStretch()

        # Progress bar
        self.progress_bar = ProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)
        layout.addWidget(self.progress_bar)

        return layout

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
        if self.operation_in_progress:
            InfoBar.warning(
                title="Operation In Progress",
                content="Please wait for the current operation to complete.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        manager = self.get_selected_manager()

        # Create and configure worker
        self.current_worker = PackageListWorker(
            self.package_service,
            manager
        )

        # Connect signals
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
        self.current_worker.start()

    def on_manager_changed(self, text: str):
        """Handle package manager selection change."""
        self.package_table.clear_packages()
        self.status_label.setText(f"Selected: {text}")

    def search_packages(self):
        """Search packages (placeholder for Phase 4)."""
        InfoBar.info(
            title="Coming Soon",
            content="Search functionality will be implemented in Phase 4.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def install_package(self):
        """Install package (placeholder for Phase 3)."""
        InfoBar.info(
            title="Coming Soon",
            content="Install functionality will be implemented in Phase 3.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    def uninstall_package(self):
        """Uninstall package (placeholder for Phase 3)."""
        InfoBar.info(
            title="Coming Soon",
            content="Uninstall functionality will be implemented in Phase 3.",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=self
        )

    @pyqtSlot(str)
    def on_operation_started(self, message: str):
        """Handle operation start."""
        self.operation_in_progress = True
        self.disable_controls()
        self.status_label.setText(message)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

    @pyqtSlot(int, int, str)
    def on_progress_update(self, current: int, total: int, message: str):
        """Handle progress update (thread-safe via signal)."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

        self.status_label.setText(message)

    @pyqtSlot(list)
    def on_packages_loaded(self, packages: List[Package]):
        """Handle loaded packages."""
        self.current_packages = packages
        self.package_table.set_packages(packages)

        # Show success notification
        InfoBar.success(
            title="Success",
            content=f"Loaded {len(packages)} packages",
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )

    @pyqtSlot(str)
    def on_error(self, error_message: str):
        """Handle error."""
        InfoBar.error(
            title="Error",
            content=error_message,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )

    @pyqtSlot()
    def on_operation_finished(self):
        """Handle operation completion."""
        self.operation_in_progress = False
        self.enable_controls()
        self.status_label.setText("Ready")
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
        if theme == "dark":
            setTheme(Theme.DARK)
        elif theme == "light":
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.AUTO)
