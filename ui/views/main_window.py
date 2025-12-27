"""
Main application window for WinPacMan.

Provides the main user interface for WinPacMan using PyQt6
with modern styling.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QStatusBar, QApplication,
    QInputDialog, QDialog, QDialogButtonBox, QCheckBox, QTextEdit,
    QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QAction
from typing import List, Optional

from core.models import PackageManager, Package, PackageStatus
from services.package_service import PackageManagerService
from services.settings_service import SettingsService
from ui.workers.package_worker import (
    PackageListWorker,
    PackageInstallWorker,
    PackageUninstallWorker
)
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
        self.current_install_worker: Optional[PackageInstallWorker] = None
        self.current_uninstall_worker: Optional[PackageUninstallWorker] = None
        self.selected_package: Optional[Package] = None
        self.verbose_mode = False  # Show detailed package manager output

        # Animated spinner for progress indication
        self.spinner_frames = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
        self.spinner_index = 0
        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self._update_spinner)
        self.progress_message = ""

        # Persistent status message (shows package count)
        self.persistent_status = "Ready"

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
        # Create menu bar
        self.create_menu_bar()

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
        self.package_table.package_selected.connect(
            self.on_package_selected
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

        # Progress label (shows loading status)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        layout.addWidget(self.progress_label)

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

        # Verbose mode checkbox
        self.verbose_checkbox = QCheckBox("Verbose")
        self.verbose_checkbox.setToolTip("Show detailed package manager output during operations")
        self.verbose_checkbox.stateChanged.connect(self.on_verbose_toggled)
        layout.addWidget(self.verbose_checkbox)

        # Spacer to push version to far right
        layout.addStretch()

        # Version label in upper right corner
        version_text = self._get_version_info()
        self.version_label = QLabel(version_text)
        self.version_label.setStyleSheet("color: #808080; font-size: 9pt;")  # Subdued gray color
        layout.addWidget(self.version_label)

        return layout

    def create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

    def create_menu_bar(self):
        """Create menu bar with File, Edit, View, Config, and Help menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        # Placeholder for future actions
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        # Placeholder for future actions

        # View menu
        view_menu = menubar.addMenu("&View")
        # Placeholder for future actions

        # Config menu
        config_menu = menubar.addMenu("&Config")
        view_config_action = QAction("&View Configuration", self)
        view_config_action.triggered.connect(self.show_configuration)
        config_menu.addAction(view_config_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        user_guide_action = QAction("&User Guide", self)
        user_guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(user_guide_action)

        changelog_action = QAction("&Change Log", self)
        changelog_action.triggered.connect(self.show_changelog)
        help_menu.addAction(changelog_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def get_selected_manager(self) -> PackageManager:
        """Get currently selected package manager."""
        manager_map = {
            "WinGet": PackageManager.WINGET,
            "Chocolatey": PackageManager.CHOCOLATEY,
            "Pip": PackageManager.PIP,
            "NPM": PackageManager.NPM
        }
        return manager_map[self.manager_combo.currentText()]

    def _get_version_info(self) -> str:
        """Extract version and date from CHANGELOG.md for display."""
        import os
        import re

        changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "CHANGELOG.md")
        version = "Unknown"
        date_time = "Unknown"

        if os.path.exists(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for first version line: ## [0.3.0] - 2025-12-26 21:20
                    match = re.search(r'##\s+\[([^\]]+)\]\s+-\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)', content)
                    if match:
                        version = match.group(1)
                        date_time = match.group(2)
            except Exception:
                pass

        return f"v{version} ({date_time})"

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
        self.progress_label.setVisible(False)
        self.status_label.setText(f"Selected: {text}")

        # Disable Install/Uninstall buttons when manager changes
        self.selected_package = None
        self.install_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

    def search_packages(self):
        """Search packages (placeholder for Phase 4)."""
        QMessageBox.information(
            self,
            "Coming Soon",
            "Search functionality will be implemented in Phase 4."
        )

    @pyqtSlot(Package)
    def on_package_selected(self, package: Package):
        """Handle package selection change - enable/disable buttons."""
        self.selected_package = package

        # Enable buttons only if no operation is in progress
        if not self.operation_in_progress:
            self.install_btn.setEnabled(True)
            self.uninstall_btn.setEnabled(True)

    def on_verbose_toggled(self, state):
        """Handle verbose mode checkbox toggle."""
        self.verbose_mode = (state == Qt.CheckState.Checked.value)
        status = "enabled" if self.verbose_mode else "disabled"
        print(f"[MainWindow] Verbose mode {status}")

    def install_package(self):
        """Install selected package or manual package ID (WinGet only)."""
        # 1. Handle manual package ID entry if no package selected
        if not self.selected_package:
            # Check if WinGet is selected
            current_manager = self.get_selected_manager()
            if current_manager != PackageManager.WINGET:
                QMessageBox.warning(
                    self,
                    "No Package Selected",
                    "Please select a package from the list to install.\n\n"
                    "Manual package ID entry is only available for WinGet."
                )
                return

            # Show input dialog for WinGet package ID
            package_id, ok = QInputDialog.getText(
                self,
                "Install WinGet Package",
                "Enter WinGet package ID to install:\n"
                "(e.g., Microsoft.PowerToys, Git.Git, 7zip.7zip)",
                text=""
            )

            if not ok or not package_id.strip():
                return  # User cancelled or entered nothing

            package_id = package_id.strip()

            # Create temporary Package object for manual entry
            package_to_install = Package(
                name=package_id,
                id=package_id,
                version="latest",
                manager=PackageManager.WINGET,
                status=PackageStatus.AVAILABLE
            )
        else:
            # Use selected package from table
            package_to_install = self.selected_package

        # 2. Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Confirm Installation",
            f"Install {package_to_install.name} ({package_to_install.version})?\n\n"
            f"Package Manager: {package_to_install.manager.value}\n"
            f"This operation may take several minutes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 3. Check no operation in progress
        if self.operation_in_progress:
            QMessageBox.warning(
                self,
                "Operation In Progress",
                "Please wait for the current operation to complete."
            )
            return

        # 4. Create worker
        self.current_install_worker = PackageInstallWorker(
            self.package_service,
            package_to_install.manager,
            package_to_install.id
        )

        # 5. Connect signals
        self.current_install_worker.signals.started.connect(
            lambda: self.on_operation_started(f"Installing {package_to_install.name}...")
        )
        self.current_install_worker.signals.progress.connect(self.on_progress_update)
        self.current_install_worker.signals.operation_complete.connect(
            self.on_install_complete
        )
        self.current_install_worker.signals.error_occurred.connect(self.on_error)
        self.current_install_worker.signals.finished.connect(
            self.on_operation_finished
        )

        # 6. Start worker
        self.current_install_worker.start()

    def uninstall_package(self):
        """Uninstall selected package."""
        # 1. Validate selection exists
        if not self.selected_package:
            QMessageBox.warning(
                self,
                "No Package Selected",
                "Please select a package to uninstall."
            )
            return

        # 2. Show confirmation dialog (stronger warning)
        reply = QMessageBox.warning(
            self,
            "Confirm Uninstallation",
            f"Uninstall {self.selected_package.name} ({self.selected_package.version})?\n\n"
            f"Package Manager: {self.selected_package.manager.value}\n\n"
            f"WARNING: This action cannot be undone.\n"
            f"Make sure you don't need this package before proceeding.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # 3. Check no operation in progress
        if self.operation_in_progress:
            QMessageBox.warning(
                self,
                "Operation In Progress",
                "Please wait for the current operation to complete."
            )
            return

        # 4. Create worker
        self.current_uninstall_worker = PackageUninstallWorker(
            self.package_service,
            self.selected_package.manager,
            self.selected_package.id
        )

        # 5. Connect signals
        self.current_uninstall_worker.signals.started.connect(
            lambda: self.on_operation_started(f"Uninstalling {self.selected_package.name}...")
        )
        self.current_uninstall_worker.signals.progress.connect(self.on_progress_update)
        self.current_uninstall_worker.signals.operation_complete.connect(
            self.on_uninstall_complete
        )
        self.current_uninstall_worker.signals.error_occurred.connect(self.on_error)
        self.current_uninstall_worker.signals.finished.connect(
            self.on_operation_finished
        )

        # 6. Start worker
        self.current_uninstall_worker.start()

    def _update_spinner(self):
        """Update animated spinner (called by timer)."""
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
        spinner = self.spinner_frames[self.spinner_index]
        self.progress_label.setText(f"{spinner} {self.progress_message}")

    @pyqtSlot(str)
    def on_operation_started(self, message: str):
        """Handle operation start."""
        print(f"[MainWindow] on_operation_started: {message}")
        self.operation_in_progress = True
        self.disable_controls()
        self.status_label.setText(message)
        self.progress_label.setVisible(True)

        # Start animated spinner
        self.progress_message = "Starting..."
        self.spinner_index = 0
        self.spinner_timer.start(100)  # Update every 100ms

    @pyqtSlot(int, int, str)
    def on_progress_update(self, current: int, total: int, message: str):
        """Handle progress update (thread-safe via signal)."""
        print(f"[MainWindow] on_progress_update: {current}/{total} - {message}")

        # Update progress message (spinner updates automatically via timer)
        self.progress_message = message
        self.status_label.setText(message)

        # Force UI to update immediately
        QApplication.processEvents()

    @pyqtSlot(list)
    def on_packages_loaded(self, packages: List[Package]):
        """Handle loaded packages."""
        print(f"[MainWindow] on_packages_loaded: Received {len(packages)} packages")
        self.current_packages = packages
        self.package_table.set_packages(packages)
        print(f"[MainWindow] Package table updated with {len(packages)} packages")

        # Show package count in status bar (keep it visible)
        package_word = "package" if len(packages) == 1 else "packages"
        self.persistent_status = f"{len(packages)} {package_word} loaded - Ready"
        self.status_label.setText(self.persistent_status)

    @pyqtSlot(object)
    def on_install_complete(self, result):
        """Handle installation completion."""
        # Log the operation
        self._log_operation(result)

        # Show verbose output if enabled
        if self.verbose_mode:
            self._show_verbose_output(result)

        if result.success:
            QMessageBox.information(
                self,
                "Installation Successful",
                result.message
            )
            # Auto-refresh to show newly installed package
            self.refresh_packages()
        else:
            QMessageBox.critical(
                self,
                "Installation Failed",
                result.message
            )

    @pyqtSlot(object)
    def on_uninstall_complete(self, result):
        """Handle uninstallation completion."""
        # Log the operation
        self._log_operation(result)

        # Show verbose output if enabled
        if self.verbose_mode:
            self._show_verbose_output(result)

        if result.success:
            QMessageBox.information(
                self,
                "Uninstallation Successful",
                result.message
            )
            # Auto-refresh to remove uninstalled package
            self.refresh_packages()
        else:
            QMessageBox.critical(
                self,
                "Uninstallation Failed",
                result.message
            )

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

        # Stop animated spinner
        self.spinner_timer.stop()
        self.progress_label.setVisible(False)
        self.progress_label.setText("")

        # Clean up worker
        if self.current_worker:
            self.current_worker.wait()
            self.current_worker.deleteLater()
            self.current_worker = None

        # Clean up install worker
        if self.current_install_worker:
            self.current_install_worker.wait()
            self.current_install_worker.deleteLater()
            self.current_install_worker = None

        # Clean up uninstall worker
        if self.current_uninstall_worker:
            self.current_uninstall_worker.wait()
            self.current_uninstall_worker.deleteLater()
            self.current_uninstall_worker = None

    def _get_winget_install_location(self, package_id: str) -> Optional[str]:
        """
        Get installation location for a WinGet package.

        Strategy:
        1. Try Windows Registry (for traditionally installed apps)
        2. If not found, query WinGet directly (for WinGet-managed apps)

        Uses very strict matching to avoid false positives. Better to show no path
        than the wrong path.
        """
        import winreg
        import os
        import re
        import subprocess

        def normalize_name(name: str) -> str:
            """Normalize name by removing spaces, hyphens, and lowercasing."""
            return re.sub(r'[\s\-_]', '', name.lower())

        def get_install_path(app_key, debug_name=None):
            """Try to extract install location from registry key using multiple methods."""
            # Method 1: InstallLocation field
            try:
                install_location = winreg.QueryValueEx(app_key, "InstallLocation")[0]
                if install_location and install_location.strip() and os.path.exists(install_location.strip()):
                    return install_location.strip()
            except FileNotFoundError:
                pass

            # Method 2: InstallPath field
            try:
                install_path = winreg.QueryValueEx(app_key, "InstallPath")[0]
                if install_path and install_path.strip() and os.path.exists(install_path.strip()):
                    return install_path.strip()
            except FileNotFoundError:
                pass

            # Method 3: Extract from UninstallString (often contains path to uninstaller)
            try:
                uninstall_string = winreg.QueryValueEx(app_key, "UninstallString")[0]
                if uninstall_string:
                    if debug_name and "vim" in debug_name.lower():
                        print(f"[DEBUG] {debug_name} UninstallString: {uninstall_string}")

                    # Extract directory from uninstall path
                    # e.g., "C:\Program Files\Vim\vim91\uninstall.exe" -> "C:\Program Files\Vim"
                    match = re.search(r'^"?([A-Z]:[^"]+?)\\[^\\]+\.exe', uninstall_string, re.IGNORECASE)
                    if match:
                        path = match.group(1)
                        # Go up one or two directories to find the base install folder
                        parent = os.path.dirname(path)

                        if debug_name and "vim" in debug_name.lower():
                            print(f"[DEBUG] Extracted path: {path}, Parent: {parent}")
                            print(f"[DEBUG] Parent exists: {os.path.exists(parent) if parent else 'N/A'}")
                            print(f"[DEBUG] Path exists: {os.path.exists(path) if path else 'N/A'}")

                        if parent and os.path.exists(parent):
                            return parent
                        if path and os.path.exists(path):
                            return path
            except FileNotFoundError:
                if debug_name and "vim" in debug_name.lower():
                    print(f"[DEBUG] {debug_name} has no UninstallString")

            # Method 4: Extract from InstallString
            try:
                install_string = winreg.QueryValueEx(app_key, "InstallString")[0]
                if install_string:
                    match = re.search(r'^"?([A-Z]:[^"]+?)\\[^\\]+\.exe', install_string, re.IGNORECASE)
                    if match:
                        path = match.group(1)
                        parent = os.path.dirname(path)
                        if parent and os.path.exists(parent):
                            return parent
                        if path and os.path.exists(path):
                            return path
            except FileNotFoundError:
                pass

            return None

        try:
            print(f"[InstallPath] Looking for: {package_id}")

            # Skip package IDs that are just version numbers (e.g., "4.7.1", "1.2.3")
            # These won't match anything meaningful in the registry
            if re.match(r'^\d+(\.\d+)*$', package_id):
                print(f"[InstallPath] Skipping version-only package ID")
                return None

            # Handle ARP (Add/Remove Programs) registry paths from WinGet
            # Format: ARP\Machine\X64\PackageName or ARP\User\X64\PackageName
            actual_package_id = package_id
            target_hive = None  # None means search all hives

            if package_id.startswith("ARP\\"):
                parts = package_id.split("\\")
                if len(parts) >= 4:
                    # Extract: ARP\Machine\X64\Vim 9.1 -> "Vim 9.1"
                    actual_package_id = "\\".join(parts[3:])

                    # Determine which registry hive to search
                    if parts[1].lower() == "machine":
                        target_hive = "HKLM"
                    elif parts[1].lower() == "user":
                        target_hive = "HKCU"

                    print(f"[InstallPath] Detected ARP format, extracted: {actual_package_id} (hive: {target_hive or 'all'})")

            # Filter registry paths based on target hive
            all_registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "HKLM"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", "HKCU"),
            ]

            # For ARP packages, search the indicated hive first, then fall back to all hives
            # (WinGet's ARP path might not always be accurate)
            if target_hive:
                # Search target hive first
                registry_paths = [(hkey, path) for hkey, path, hive in all_registry_paths if hive == target_hive]
                # Then add other hives as fallback
                registry_paths.extend([(hkey, path) for hkey, path, hive in all_registry_paths if hive != target_hive])
                print(f"[InstallPath] Will search {target_hive} first, then other hives")
            else:
                registry_paths = [(hkey, path) for hkey, path, _ in all_registry_paths]

            # Prepare search terms: full package ID and individual parts
            package_id_normalized = normalize_name(actual_package_id)
            package_parts = actual_package_id.split('.')

            # Create list of search terms to try (in priority order)
            search_terms = []

            # For ARP packages, the package ID IS the subkey name - prioritize exact match
            if package_id.startswith("ARP\\"):
                # Try exact subkey match first with highest confidence
                search_terms.append((actual_package_id, "arp_subkey", 120))  # Exact match (not normalized)
                search_terms.append((package_id_normalized, "arp_normalized", 100))

                # Also try just the base name without version numbers
                # "Vim 9.1" -> "Vim"
                base_name = re.sub(r'\s+\d+(\.\d+)*$', '', actual_package_id).strip()
                if base_name and base_name != actual_package_id:
                    search_terms.append((normalize_name(base_name), "arp_base", 90))
                    print(f"[InstallPath] ARP base name: {base_name}")

            elif len(package_parts) > 1:
                # For "CPUID.HWMonitor", try: full ID, last part, first part
                search_terms.append((package_id_normalized, "full_id", 100))  # Base confidence for full ID

                # Only add parts that aren't just version numbers
                last_part = package_parts[-1]
                first_part = package_parts[0]

                if not re.match(r'^\d+$', last_part) and len(last_part) > 2:
                    search_terms.append((normalize_name(last_part), "product", 80))  # Product name

                if not re.match(r'^\d+$', first_part) and len(first_part) > 2:
                    search_terms.append((normalize_name(first_part), "publisher", 70))  # Publisher name

            else:
                # Single-part ID (if it's not a version number)
                if len(actual_package_id) > 2:
                    search_terms.append((package_id_normalized, "full_id", 100))

            # If we ended up with no search terms, bail out
            if not search_terms:
                print(f"[InstallPath] No valid search terms could be generated")
                return None

            print(f"[InstallPath] Search terms: {[term for term, _, _ in search_terms]}")

            # Collect all candidates with confidence scores
            candidates = []
            registry_entries_scanned = 0
            registry_entries_total = 0  # Including those without paths
            sample_entries = []  # For debug: collect sample of what we're checking
            sample_all_entries = []  # All entries including those without install paths

            for hkey, registry_path in registry_paths:
                try:
                    with winreg.OpenKey(hkey, registry_path) as reg_key:
                        num_subkeys = winreg.QueryInfoKey(reg_key)[0]
                        for i in range(num_subkeys):
                            try:
                                subkey_name = winreg.EnumKey(reg_key, i)
                                with winreg.OpenKey(reg_key, subkey_name) as app_key:
                                    try:
                                        display_name = winreg.QueryValueEx(app_key, "DisplayName")[0]
                                        install_path = get_install_path(app_key, debug_name=display_name)

                                        # Track ALL entries with DisplayName (even without install path)
                                        if display_name:
                                            registry_entries_total += 1
                                            if len(sample_all_entries) < 20:
                                                has_path = "✓" if install_path else "✗"
                                                sample_all_entries.append(f"{has_path} {display_name} (subkey: {subkey_name})")

                                        if not install_path or not display_name:
                                            continue

                                        registry_entries_scanned += 1

                                        # Collect sample entries for debug (first 10)
                                        if len(sample_entries) < 10:
                                            sample_entries.append(f"{display_name} (subkey: {subkey_name})")

                                        display_normalized = normalize_name(display_name)
                                        subkey_normalized = normalize_name(subkey_name)

                                        # Try each search term and use the highest confidence match
                                        best_confidence = 0
                                        match_reason = ""

                                        for search_term, term_type, base_confidence in search_terms:
                                            confidence = 0

                                            # For ARP packages, check both subkey AND display name
                                            if term_type in ["arp_subkey", "arp_normalized", "arp_base"]:
                                                # Try exact subkey match (case-sensitive for arp_subkey)
                                                if term_type == "arp_subkey":
                                                    if search_term == subkey_name:
                                                        confidence = base_confidence + 30
                                                        match_reason = f"subkey_exact_arp"
                                                    elif search_term.lower() == subkey_name.lower():
                                                        confidence = base_confidence + 20
                                                        match_reason = f"subkey_exact_arp_ci"
                                                    # Also check display name for ARP exact match
                                                    elif search_term == display_name:
                                                        confidence = base_confidence + 25
                                                        match_reason = f"display_exact_arp"
                                                    elif search_term.lower() == display_name.lower():
                                                        confidence = base_confidence + 15
                                                        match_reason = f"display_exact_arp_ci"
                                                else:
                                                    # For normalized/base ARP terms, check normalized fields
                                                    if search_term == subkey_normalized:
                                                        confidence = base_confidence + 20
                                                        match_reason = f"subkey_exact_{term_type}"
                                                    elif search_term == display_normalized:
                                                        confidence = base_confidence + 15
                                                        match_reason = f"display_exact_{term_type}"
                                                    elif display_normalized.startswith(search_term) and len(search_term) > 3:
                                                        confidence = base_confidence + 5
                                                        match_reason = f"display_starts_{term_type}"
                                                    elif search_term in subkey_normalized and len(search_term) > 3:
                                                        confidence = base_confidence
                                                        match_reason = f"subkey_contains_{term_type}"

                                            # Check registry subkey name (normalized) for non-ARP
                                            elif search_term == subkey_normalized:
                                                confidence = base_confidence + 20
                                                match_reason = f"subkey_exact_{term_type}"
                                            elif search_term in subkey_normalized and len(search_term) > 3:
                                                confidence = base_confidence + 10
                                                match_reason = f"subkey_contains_{term_type}"
                                            # Check display name for non-ARP
                                            elif display_normalized == search_term:
                                                confidence = base_confidence
                                                match_reason = f"display_exact_{term_type}"
                                            elif display_normalized.startswith(search_term):
                                                confidence = base_confidence - 10
                                                match_reason = f"display_starts_{term_type}"
                                            elif search_term in display_normalized and len(search_term) > 3:
                                                # Only match if it's a whole word (surrounded by non-letters)
                                                pattern = rf'(^|[^a-z]){re.escape(search_term)}($|[^a-z])'
                                                if re.search(pattern, display_normalized):
                                                    confidence = base_confidence - 20
                                                    match_reason = f"display_word_{term_type}"

                                            # Update best confidence
                                            if confidence > best_confidence:
                                                best_confidence = confidence
                                                match_reason = match_reason

                                        # Boost if install path contains any search term
                                        if best_confidence > 0:
                                            for search_term, term_type, _ in search_terms:
                                                if search_term in install_path.lower() and len(search_term) > 3:
                                                    best_confidence += 5
                                                    break

                                        # Only add if we have a reasonable match
                                        if best_confidence >= 60:
                                            candidates.append((best_confidence, display_name, install_path, match_reason, subkey_name))

                                    except FileNotFoundError:
                                        pass
                            except OSError:
                                continue
                except FileNotFoundError:
                    continue

            # Debug output
            print(f"[InstallPath] Scanned {registry_entries_scanned} entries with install paths ({registry_entries_total} total entries)")
            if not candidates and registry_entries_total > 0:
                print(f"[InstallPath] Sample of ALL registry entries (✓=has path, ✗=no path):")
                for entry in sample_all_entries:
                    print(f"  {entry}")

            # Sort by confidence (highest first)
            candidates.sort(key=lambda x: x[0], reverse=True)

            if candidates:
                print(f"[InstallPath] Found {len(candidates)} candidates:")
                for conf, name, path, reason, subkey in candidates[:5]:  # Show top 5
                    print(f"  [{conf}] {name}")
                    print(f"       Reason: {reason}, Subkey: {subkey}")
                    print(f"       Path: {path}")

                # Only return if confidence is high enough (>= 70 to be more strict)
                if candidates[0][0] >= 70:
                    print(f"[InstallPath] ✓ Returning best match: {candidates[0][1]}")
                    return candidates[0][2]
                else:
                    print(f"[InstallPath] ✗ Best match confidence too low ({candidates[0][0]}), returning None")
            else:
                print(f"[InstallPath] No candidates found in registry")

            # Fallback: Query WinGet directly for installation location
            # NOTE: Only works for WinGet-managed packages (not ARP entries)
            if not package_id.startswith("ARP\\"):
                print(f"[InstallPath] Trying winget show as fallback...")
                try:
                    result = subprocess.run(
                        ['winget', 'show', '--id', package_id, '--accept-source-agreements'],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding='utf-8',
                        errors='ignore'
                    )

                    if result.returncode == 0:
                        # Parse output for "Install Location:" or "Installation Folder:"
                        for line in result.stdout.splitlines():
                            line_lower = line.lower().strip()
                            if 'install location:' in line_lower or 'installation folder:' in line_lower:
                                # Extract path after the colon
                                parts = line.split(':', 1)
                                if len(parts) == 2:
                                    install_path = parts[1].strip()
                                    if install_path and os.path.exists(install_path):
                                        print(f"[InstallPath] ✓ Found via winget show: {install_path}")
                                        return install_path
                                    else:
                                        print(f"[InstallPath] Path from winget doesn't exist: {install_path}")
                        print(f"[InstallPath] winget show returned no install location")
                    else:
                        print(f"[InstallPath] winget show failed (exit code {result.returncode})")

                except subprocess.TimeoutExpired:
                    print(f"[InstallPath] winget show timed out")
                except Exception as e:
                    print(f"[InstallPath] winget show error: {e}")
            else:
                print(f"[InstallPath] ARP packages don't support winget show, skipping fallback")

            return None

        except Exception as e:
            print(f"[InstallPath] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return None

    def on_package_details(self, package: Package):
        """Show package details dialog with copy to clipboard functionality."""
        # Get installation location for WinGet packages
        install_location = None
        if package.manager == PackageManager.WINGET:
            install_location = self._get_winget_install_location(package.id)

        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Package Details")
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)

        # Package info
        info_text = (
            f"Name: {package.name}\n"
            f"Version: {package.version}\n"
            f"Manager: {package.manager.value}\n"
            f"Description: {package.description or 'N/A'}"
        )

        info_label = QLabel(info_text)
        info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(info_label)

        # Installation location section (if available)
        if install_location:
            layout.addSpacing(10)

            location_label = QLabel(f"<b>Installation Location:</b>")
            layout.addWidget(location_label)

            path_label = QLabel(install_location)
            path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            path_label.setStyleSheet("padding: 5px; background-color: palette(base); border: 1px solid palette(mid);")
            layout.addWidget(path_label)

            # Copy button
            copy_button = QPushButton("Copy Path to Clipboard")
            copy_button.clicked.connect(lambda: self._copy_to_clipboard(install_location))
            layout.addWidget(copy_button)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def _copy_to_clipboard(self, text: str):
        """Copy text to system clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Show brief feedback, then restore persistent status
        self.status_label.setText(f"Copied to clipboard: {text}")
        QTimer.singleShot(3000, lambda: self.status_label.setText(self.persistent_status))

    def _show_verbose_output(self, result):
        """
        Show detailed package manager output in a dialog.

        Displays stdout, stderr, and exit code from package manager operations.
        Useful for debugging installation/uninstallation issues.
        """
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Verbose Output - {result.operation.title()} {result.package}")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)

        # Header with operation info
        header_text = (
            f"<b>Operation:</b> {result.operation}<br>"
            f"<b>Package:</b> {result.package}<br>"
            f"<b>Success:</b> {'✓ Yes' if result.success else '✗ No'}<br>"
            f"<b>Exit Code:</b> {result.details.get('exit_code', 'N/A')}"
        )
        header_label = QLabel(header_text)
        layout.addWidget(header_label)

        # Stdout section
        stdout_text = result.details.get('stdout', '').strip()
        if stdout_text:
            layout.addSpacing(10)
            stdout_label = QLabel("<b>Standard Output (stdout):</b>")
            layout.addWidget(stdout_label)

            stdout_display = QTextEdit()
            stdout_display.setReadOnly(True)
            stdout_display.setPlainText(stdout_text)
            stdout_display.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
            layout.addWidget(stdout_display)

        # Stderr section
        stderr_text = result.details.get('stderr', '').strip()
        if stderr_text:
            layout.addSpacing(10)
            stderr_label = QLabel("<b>Standard Error (stderr):</b>")
            layout.addWidget(stderr_label)

            stderr_display = QTextEdit()
            stderr_display.setReadOnly(True)
            stderr_display.setPlainText(stderr_text)
            stderr_display.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; color: #d32f2f;")
            layout.addWidget(stderr_display)

        # If no output, show message
        if not stdout_text and not stderr_text:
            no_output_label = QLabel("<i>No output captured from package manager.</i>")
            layout.addWidget(no_output_label)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def _log_operation(self, result):
        """Log operation to history file."""
        from core.config import config_manager
        import json

        log_file = config_manager.get_data_file_path("operation_history.json")

        # Load existing history
        history = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        # Add new entry
        history.append(result.to_dict())

        # Keep only last 100 operations
        history = history[-100:]

        # Save back
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Failed to log operation: {e}")

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

        # Always enable Install (supports manual WinGet package ID entry)
        self.install_btn.setEnabled(True)

        # Only enable Uninstall if package is selected
        if self.selected_package:
            self.uninstall_btn.setEnabled(True)

    def show_user_guide(self):
        """Show user guide (placeholder)."""
        QMessageBox.information(
            self,
            "User Guide",
            "User Guide - Coming Soon\n\n"
            "Comprehensive documentation will be available in a future release.\n\n"
            "For now, please refer to the README.md and CLAUDE.md files in the project repository."
        )

    def show_changelog(self):
        """Display CHANGELOG.md in a dialog."""
        import os

        # Find CHANGELOG.md in project root
        changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "CHANGELOG.md")

        if not os.path.exists(changelog_path):
            QMessageBox.warning(self, "Change Log", "CHANGELOG.md file not found.")
            return

        # Read changelog
        try:
            with open(changelog_path, 'r', encoding='utf-8') as f:
                changelog_content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CHANGELOG.md:\n{str(e)}")
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Log")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)

        layout = QVBoxLayout(dialog)

        # Changelog content
        changelog_display = QTextEdit()
        changelog_display.setReadOnly(True)
        changelog_display.setPlainText(changelog_content)
        changelog_display.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
        layout.addWidget(changelog_display)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def show_about(self):
        """Show About dialog with version and date."""
        import os
        import re

        # Extract version and date/time from CHANGELOG.md
        changelog_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "CHANGELOG.md")
        version = "Unknown"
        date_time = "Unknown"

        if os.path.exists(changelog_path):
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for first version line: ## [0.3.0] - 2025-12-26 21:20
                    match = re.search(r'##\s+\[([^\]]+)\]\s+-\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)', content)
                    if match:
                        version = match.group(1)
                        date_time = match.group(2)
            except Exception:
                pass

        about_text = f"""<h2>WinPacMan</h2>
<p><b>Version:</b> {version}</p>
<p><b>Release Date:</b> {date_time}</p>
<p><b>Description:</b> Unified Windows Package Manager</p>
<p>A modern PyQt6 GUI for managing packages across WinGet, Chocolatey, Pip, and NPM.</p>
<br>
<p><b>Supported Package Managers:</b></p>
<ul>
<li>WinGet - Windows Package Manager</li>
<li>Chocolatey - The Package Manager for Windows</li>
<li>Pip - Python Package Installer</li>
<li>NPM - Node Package Manager</li>
</ul>
<br>
<p>🤖 Built with <a href="https://claude.com/claude-code">Claude Code</a></p>
<p>© 2025 WinPacMan Project</p>
"""

        QMessageBox.about(self, "About WinPacMan", about_text)

    def show_configuration(self):
        """Show configuration file in read-only dialog."""
        from core.config import config_manager
        import json

        # Get config file path
        config_file = config_manager.config_file

        if not config_file.exists():
            QMessageBox.warning(self, "Configuration", "Configuration file not found.")
            return

        # Read config
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            # Pretty print JSON
            config_text = json.dumps(config_data, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read configuration:\n{str(e)}")
            return

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Configuration")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)

        layout = QVBoxLayout(dialog)

        # Header with file path
        path_label = QLabel(f"<b>Configuration File:</b> {config_file}")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(path_label)

        layout.addSpacing(10)

        # Config content
        config_display = QTextEdit()
        config_display.setReadOnly(True)
        config_display.setPlainText(config_text)
        config_display.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace;")
        layout.addWidget(config_display)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

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
