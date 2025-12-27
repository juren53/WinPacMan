"""
Main application window for WinPacMan.

Provides the main user interface for WinPacMan using PyQt6
with modern styling.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QStatusBar, QApplication,
    QInputDialog, QDialog, QDialogButtonBox, QCheckBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QFont
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

        return layout

    def create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

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

        # Show success message in status bar
        self.status_label.setText(f"Success: Loaded {len(packages)} packages")

        # Auto-clear success message after 3 seconds
        QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))

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
        Get installation location for a WinGet package by querying Windows Registry.

        WinGet doesn't expose installation paths via CLI, so we query the registry
        where most applications register their install location.
        """
        import winreg
        import os

        try:
            # Common registry paths where apps register install info
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            ]

            # Extract the package name (last part of package ID after the dot)
            # e.g., "Mozilla.Firefox" -> "Firefox", "Obsidian.Obsidian" -> "Obsidian"
            package_name = package_id.split('.')[-1].lower()

            for hkey, registry_path in registry_paths:
                try:
                    # Open the uninstall registry key
                    with winreg.OpenKey(hkey, registry_path) as reg_key:
                        # Enumerate all subkeys (installed applications)
                        num_subkeys = winreg.QueryInfoKey(reg_key)[0]

                        for i in range(num_subkeys):
                            try:
                                subkey_name = winreg.EnumKey(reg_key, i)

                                with winreg.OpenKey(reg_key, subkey_name) as app_key:
                                    try:
                                        # Get the DisplayName
                                        display_name = winreg.QueryValueEx(app_key, "DisplayName")[0]

                                        # Check if this matches our package (case-insensitive)
                                        if package_name in display_name.lower() or display_name.lower() in package_name:
                                            # Try to get InstallLocation
                                            try:
                                                install_location = winreg.QueryValueEx(app_key, "InstallLocation")[0]
                                                if install_location and os.path.exists(install_location):
                                                    return install_location
                                            except FileNotFoundError:
                                                # InstallLocation not found, try InstallPath
                                                try:
                                                    install_path = winreg.QueryValueEx(app_key, "InstallPath")[0]
                                                    if install_path and os.path.exists(install_path):
                                                        return install_path
                                                except FileNotFoundError:
                                                    pass
                                    except FileNotFoundError:
                                        # DisplayName not found, skip this entry
                                        pass
                            except OSError:
                                # Can't access this subkey, skip it
                                continue

                except FileNotFoundError:
                    # Registry path doesn't exist
                    continue

        except Exception as e:
            print(f"Failed to get install location from registry: {e}")

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

        # Show brief feedback
        self.status_label.setText(f"Copied to clipboard: {text}")
        QTimer.singleShot(3000, lambda: self.status_label.setText("Ready"))

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
