"""
Main application window for WinPacMan.

Provides the main user interface for WinPacMan using PyQt6
with modern styling.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QComboBox, QStatusBar, QApplication,
    QInputDialog, QDialog, QDialogButtonBox, QCheckBox, QTextEdit,
    QMenuBar, QMenu, QLineEdit, QTabWidget, QRadioButton, QButtonGroup,
    QTextBrowser, QTableWidget, QTableWidgetItem, QHeaderView
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
from metadata import MetadataCacheService, WinGetProvider, ScoopProvider, ChocolateyProvider
from core.config import config_manager
from ui.components.package_table import PackageTableWidget
from utils.system_utils import WindowsPowerManager

# Markdown rendering imports
import markdown
from markdown.extensions import fenced_code, tables, nl2br, sane_lists
from pygments.formatters import HtmlFormatter
import os
import re


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

        # Initialize metadata cache
        cache_db_path = config_manager.get_data_file_path("metadata_cache.db")
        self.metadata_cache = MetadataCacheService(cache_db_path)

        # Register WinGet provider
        winget_provider = WinGetProvider()
        self.metadata_cache.register_provider(winget_provider)

        # Register Chocolatey provider
        chocolatey_provider = ChocolateyProvider()
        self.metadata_cache.register_provider(chocolatey_provider)

        # Register Scoop provider
        scoop_provider = ScoopProvider()
        self.metadata_cache.register_provider(scoop_provider)

        # State
        self.current_packages: List[Package] = []
        self.operation_in_progress = False
        self.current_worker: Optional[PackageListWorker] = None
        self.current_install_worker: Optional[PackageInstallWorker] = None
        self.current_uninstall_worker: Optional[PackageUninstallWorker] = None
        self.selected_package: Optional[Package] = None
        self.verbose_mode = False  # Show detailed package manager output
        self.table_mode = None  # 'installed' or 'available' - tracks what's currently in the table

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

        # Restore saved window geometry or use defaults
        self.restore_window_geometry()

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

        # Header with version info in upper right
        header_layout = QHBoxLayout()
        header_layout.addStretch()  # Push version label to the right

        # Version label
        version_info = self._get_version_info()
        self.version_label = QLabel(version_info)
        self.version_label.setStyleSheet("color: #666666; font-size: 9pt; padding-bottom: 5px;")
        header_layout.addWidget(self.version_label)

        main_layout.addLayout(header_layout)

        # Repository tabs at the top
        self.create_repository_tabs()
        main_layout.addWidget(self.repo_tabs)

        # Create horizontal control panel (Left: Installed controls, Right: Available controls)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(20)
        control_layout.setContentsMargins(0, 0, 0, 0)

        # Left side - Installed Packages controls
        left_controls = self.create_installed_controls()
        control_layout.addLayout(left_controls, 1)

        # Right side - Available Packages controls
        right_controls = self.create_available_controls()
        control_layout.addLayout(right_controls, 1)

        main_layout.addLayout(control_layout)
        main_layout.setSpacing(5)  # Reduce spacing between control panel and table

        # Single large package table (shared by both functions)
        self.package_table = PackageTableWidget()
        self.package_table.package_double_clicked.connect(self.on_package_details)
        self.package_table.package_selected.connect(self.on_package_selected)
        main_layout.addWidget(self.package_table)

        # Status bar at bottom
        self.create_status_bar()

    def create_installed_controls(self) -> QVBoxLayout:
        """Create left side controls for Installed packages."""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Header
        header = QLabel("Installed Packages")
        header.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(header)

        # List Installed Packages button
        self.list_installed_btn = QPushButton("List Installed Packages")
        self.list_installed_btn.clicked.connect(self.list_installed_packages)
        layout.addWidget(self.list_installed_btn)

        # Uninstall button
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self.uninstall_package)
        self.uninstall_btn.setEnabled(False)  # Disabled until data appears
        layout.addWidget(self.uninstall_btn)

        return layout

    def create_available_controls(self) -> QVBoxLayout:
        """Create right side controls for Available packages."""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Header
        header = QLabel("Available Packages")
        header.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(header)

        # Search box layout
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search available packages...")
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.search_packages)
        search_layout.addWidget(self.search_input)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_packages)
        self.search_btn.setEnabled(False)  # Disabled until user types
        search_layout.addWidget(self.search_btn)

        layout.addLayout(search_layout)

        # Install button
        self.install_btn = QPushButton("Install")
        self.install_btn.clicked.connect(self.install_package)
        self.install_btn.setEnabled(False)  # Disabled until data appears
        layout.addWidget(self.install_btn)

        # Progress label (shows loading status)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #0078d4; font-weight: bold;")
        layout.addWidget(self.progress_label)

        return layout

    def create_repository_tabs(self):
        """Create repository filter tabs."""
        self.repo_tabs = QTabWidget()
        self.repo_tabs.setMaximumHeight(40)

        # Define available repositories
        # Future: Add more tabs as providers are implemented (Pip, NPM, etc.)
        self.tab_managers = {
            'All Packages': None,  # None means all managers
            'WinGet': ['winget'],
            'Chocolatey': ['chocolatey'],
            'Scoop': ['scoop'],
            # 'Pip': ['pip'],  # Future
            # 'NPM': ['npm'],  # Future
        }

        # Create tabs
        for tab_name in self.tab_managers.keys():
            # Create empty widget for each tab (we use one shared package table)
            tab_widget = QWidget()
            self.repo_tabs.addTab(tab_widget, tab_name)

        # Connect tab change signal
        self.repo_tabs.currentChanged.connect(self.on_tab_changed)

        # Set default tab to "All Packages"
        self.repo_tabs.setCurrentIndex(0)

        # Update tab labels with package counts
        self.update_tab_counts()

    def update_tab_counts(self):
        """Update tab labels with package counts from cache."""
        try:
            # Get counts for each manager
            winget_count = self.metadata_cache.get_package_count('winget')
            choco_count = self.metadata_cache.get_package_count('chocolatey')
            scoop_count = self.metadata_cache.get_package_count('scoop')
            total_count = winget_count + choco_count + scoop_count

            # Update tab labels
            for i in range(self.repo_tabs.count()):
                tab_name = list(self.tab_managers.keys())[i]
                if tab_name == 'All Packages':
                    label = f"All Packages ({total_count:,})" if total_count > 0 else "All Packages"
                elif tab_name == 'WinGet':
                    label = f"WinGet ({winget_count:,})" if winget_count > 0 else "WinGet"
                elif tab_name == 'Chocolatey':
                    label = f"Chocolatey ({choco_count:,})" if choco_count > 0 else "Chocolatey"
                elif tab_name == 'Scoop':
                    label = f"Scoop ({scoop_count:,})" if scoop_count > 0 else "Scoop"
                else:
                    label = tab_name

                self.repo_tabs.setTabText(i, label)

        except Exception as e:
            print(f"[MainWindow] Error updating tab counts: {e}")


    def create_status_bar(self):
        """Create status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Status label
        self.status_label = QLabel(self.persistent_status)
        self.status_bar.addWidget(self.status_label)

    def create_menu_bar(self):
        """Create menu bar with File, Config, and Help menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Config menu
        config_menu = menubar.addMenu("&Config")
        view_config_action = QAction("&View Configuration", self)
        view_config_action.triggered.connect(self.show_configuration)
        config_menu.addAction(view_config_action)

        refresh_cache_action = QAction("&Refresh Metadata Cache", self)
        refresh_cache_action.triggered.connect(self.refresh_metadata_cache)
        config_menu.addAction(refresh_cache_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        self.verbose_action = QAction("&Verbose Output", self)
        self.verbose_action.setCheckable(True)
        self.verbose_action.setChecked(False)
        self.verbose_action.setToolTip("Show detailed package manager output during operations")
        self.verbose_action.triggered.connect(self.on_verbose_toggled)
        view_menu.addAction(self.verbose_action)

        cache_summary_action = QAction("&Cache Summary", self)
        cache_summary_action.triggered.connect(self.show_cache_summary)
        view_menu.addAction(cache_summary_action)

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

    def show_cache_summary(self):
        """Show a dialog with a summary of the package cache in table format."""
        from datetime import datetime

        # Helper function to format time ago
        def format_time_ago(dt: datetime) -> str:
            """Format datetime as 'X time ago' string."""
            if not dt:
                return "Never"

            now = datetime.now()
            delta = now - dt

            seconds = delta.total_seconds()

            if seconds < 60:
                return "Just now"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif seconds < 2592000:
                weeks = int(seconds / 604800)
                return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            else:
                months = int(seconds / 2592000)
                return f"{months} month{'s' if months != 1 else ''} ago"

        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Cache Summary")
        dialog.setMinimumWidth(750)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout(dialog)

        # Title
        title_label = QLabel("<h2>Package Cache Summary</h2>")
        layout.addWidget(title_label)

        # Create table with refresh button column
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Provider", "Package Count", "Last Updated", "Actions"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # Function to refresh table data
        def refresh_table_data():
            """Update table with current cache data."""
            # Clear existing rows
            table.setRowCount(0)

            provider_total = 0
            row_index = 0

            # Populate provider rows
            for display_name, manager_name in providers:
                count = self.metadata_cache.get_package_count(manager_name)
                freshness = self.metadata_cache.get_cache_freshness(manager_name)
                freshness_str = format_time_ago(freshness)

                provider_total += count

                table.insertRow(row_index)
                table.setItem(row_index, 0, QTableWidgetItem(display_name))
                table.setItem(row_index, 1, QTableWidgetItem(f"{count:,}"))
                table.setItem(row_index, 2, QTableWidgetItem(freshness_str))

                # Center align count and freshness columns
                table.item(row_index, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.item(row_index, 2).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Add refresh button
                refresh_btn = QPushButton("Refresh")
                refresh_btn.setMaximumWidth(80)

                # Use closure to capture manager_name
                def make_refresh_handler(mgr_name, mgr_display):
                    def handler():
                        refresh_provider(mgr_name, mgr_display)
                    return handler

                refresh_btn.clicked.connect(make_refresh_handler(manager_name, display_name))
                table.setCellWidget(row_index, 3, refresh_btn)

                row_index += 1

            # Add separator row
            table.insertRow(row_index)
            for col in range(4):
                table.setItem(row_index, col, QTableWidgetItem(""))
                table.item(row_index, col).setBackground(Qt.GlobalColor.lightGray)
            table.setRowHeight(row_index, 2)
            row_index += 1

            # Add installed packages row
            installed_packages = self.metadata_cache.get_installed_packages()
            installed_count = len(installed_packages)

            table.insertRow(row_index)
            table.setItem(row_index, 0, QTableWidgetItem("Installed"))
            table.setItem(row_index, 1, QTableWidgetItem(f"{installed_count:,}"))
            table.setItem(row_index, 2, QTableWidgetItem("Live"))
            table.setItem(row_index, 3, QTableWidgetItem(""))

            # Bold the installed row
            font = table.item(row_index, 0).font()
            font.setBold(True)
            for col in range(3):
                table.item(row_index, col).setFont(font)
            table.item(row_index, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.item(row_index, 2).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            row_index += 1

            # Add another separator
            table.insertRow(row_index)
            for col in range(4):
                table.setItem(row_index, col, QTableWidgetItem(""))
                table.item(row_index, col).setBackground(Qt.GlobalColor.lightGray)
            table.setRowHeight(row_index, 2)
            row_index += 1

            # Add total row
            total_count = provider_total + installed_count
            table.insertRow(row_index)
            table.setItem(row_index, 0, QTableWidgetItem("Total"))
            table.setItem(row_index, 1, QTableWidgetItem(f"{total_count:,}"))
            table.setItem(row_index, 2, QTableWidgetItem(""))
            table.setItem(row_index, 3, QTableWidgetItem(""))

            # Bold the total row
            font = table.item(row_index, 0).font()
            font.setBold(True)
            for col in range(3):
                table.item(row_index, col).setFont(font)
            table.item(row_index, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        # Function to refresh a specific provider
        def refresh_provider(manager_name: str, display_name: str):
            """Refresh cache for a specific provider."""
            # Disable all refresh buttons during operation
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 3)
                if widget and isinstance(widget, QPushButton):
                    widget.setEnabled(False)

            # Show progress in status
            title_label.setText(f"<h2>Package Cache Summary - Refreshing {display_name}...</h2>")
            QApplication.processEvents()

            try:
                # Prevent system sleep during cache refresh
                with WindowsPowerManager.prevent_sleep():
                    # Refresh the cache
                    self.metadata_cache.refresh_cache(manager=manager_name, force=True)

                # Update table data
                refresh_table_data()

                # Update tab counts in main window
                self.update_tab_counts()

                # Show success
                title_label.setText(f"<h2>Package Cache Summary - {display_name} Refreshed ✓</h2>")

                # Reset title after 2 seconds
                QTimer.singleShot(2000, lambda: title_label.setText("<h2>Package Cache Summary</h2>"))

            except Exception as e:
                # Show error
                title_label.setText("<h2>Package Cache Summary</h2>")
                QMessageBox.critical(
                    dialog,
                    "Refresh Failed",
                    f"Failed to refresh {display_name} cache:\n{str(e)}"
                )

            # Re-enable all refresh buttons
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 3)
                if widget and isinstance(widget, QPushButton):
                    widget.setEnabled(True)

        # Function to refresh all providers
        def refresh_all_providers():
            """Refresh cache for all providers."""
            # Disable buttons
            refresh_all_btn.setEnabled(False)
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 3)
                if widget and isinstance(widget, QPushButton):
                    widget.setEnabled(False)

            title_label.setText("<h2>Package Cache Summary - Refreshing All Providers...</h2>")
            QApplication.processEvents()

            try:
                # Prevent system sleep during all cache refreshes
                with WindowsPowerManager.prevent_sleep():
                    # Refresh all providers
                    for display_name, manager_name in providers:
                        title_label.setText(f"<h2>Package Cache Summary - Refreshing {display_name}...</h2>")
                        QApplication.processEvents()
                        self.metadata_cache.refresh_cache(manager=manager_name, force=True)

                # Update table data
                refresh_table_data()

                # Update tab counts in main window
                self.update_tab_counts()

                # Show success
                title_label.setText("<h2>Package Cache Summary - All Providers Refreshed ✓</h2>")
                QTimer.singleShot(2000, lambda: title_label.setText("<h2>Package Cache Summary</h2>"))

            except Exception as e:
                title_label.setText("<h2>Package Cache Summary</h2>")
                QMessageBox.critical(
                    dialog,
                    "Refresh Failed",
                    f"Failed to refresh cache:\n{str(e)}"
                )

            # Re-enable buttons
            refresh_all_btn.setEnabled(True)
            for row in range(table.rowCount()):
                widget = table.cellWidget(row, 3)
                if widget and isinstance(widget, QPushButton):
                    widget.setEnabled(True)

        # Get data for each provider
        providers = [
            ('WinGet', 'winget'),
            ('Chocolatey', 'chocolatey'),
            ('Scoop', 'scoop')
        ]

        # Initial table population
        refresh_table_data()

        layout.addWidget(table)

        # Button layout
        button_layout = QHBoxLayout()

        # Refresh All button
        refresh_all_btn = QPushButton("Refresh All")
        refresh_all_btn.clicked.connect(refresh_all_providers)
        button_layout.addWidget(refresh_all_btn)

        button_layout.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def get_active_tab_name(self) -> str:
        """Get the name of the currently active tab (without count)."""
        index = self.repo_tabs.currentIndex()
        return list(self.tab_managers.keys())[index]

    def get_active_managers(self) -> Optional[List[str]]:
        """Get the list of managers for the active tab (None means all)."""
        index = self.repo_tabs.currentIndex()
        tab_name = list(self.tab_managers.keys())[index]
        return self.tab_managers.get(tab_name)

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

    def list_installed_packages(self):
        """List installed packages in the shared table."""
        print("[MainWindow] list_installed_packages called")
        if self.operation_in_progress:
            print("[MainWindow] Operation already in progress, showing warning")
            QMessageBox.warning(
                self,
                "Operation In Progress",
                "Please wait for the current operation to complete."
            )
            return

        # Show progress
        self.status_label.setText("Scanning Windows Registry for installed packages...")
        self.progress_label.setVisible(True)
        self.progress_label.setText("⏳ Scanning registry...")
        QApplication.processEvents()

        try:
            # Sync installed packages from registry (fast: 1-2 seconds)
            self.metadata_cache.sync_installed_packages_from_registry(validate=True)

            # Get installed packages from cache
            tab_name = self.get_active_tab_name()
            managers_filter = self.get_active_managers()

            installed = self.metadata_cache.get_installed_packages(managers=managers_filter)

            # Convert to Package objects with smart manager resolution
            packages = [m.to_package(cache_service=self.metadata_cache) for m in installed]

            # Store and display in shared table
            self.current_packages = packages
            self.package_table.set_packages(packages)
            self.table_mode = 'installed'  # Track that table now shows installed packages

            # Disable both buttons until a package is selected
            self.install_btn.setEnabled(False)
            self.uninstall_btn.setEnabled(False)
            self.selected_package = None

            # Update status
            package_word = "package" if len(packages) == 1 else "packages"
            source_desc = tab_name if managers_filter else "All Packages"
            self.persistent_status = f"{len(packages)} installed {package_word} loaded from {source_desc}"
            self.status_label.setText(self.persistent_status)
            self.progress_label.setVisible(False)

            print(f"[MainWindow] Loaded {len(packages)} installed packages from registry")

        except Exception as e:
            print(f"[MainWindow] Error syncing installed packages: {e}")
            import traceback
            traceback.print_exc()

            self.progress_label.setVisible(False)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load installed packages from registry:\n{str(e)}"
            )

    def on_package_selected(self, package: Package):
        """Handle package selection - enable appropriate button based on table mode."""
        self.selected_package = package

        # Enable the appropriate button based on what's in the table
        if not self.operation_in_progress:
            if self.table_mode == 'installed':
                self.uninstall_btn.setEnabled(True)
                self.install_btn.setEnabled(False)
            elif self.table_mode == 'available':
                self.install_btn.setEnabled(True)
                self.uninstall_btn.setEnabled(False)

    def on_tab_changed(self, index: int):
        """Handle repository tab change - clear table."""
        tab_name = self.repo_tabs.tabText(index)

        # Clear table
        self.package_table.clear_packages()
        self.progress_label.setVisible(False)
        self.table_mode = None

        # Update status
        self.status_label.setText(f"Tab changed to: {tab_name}")

        # Disable Install/Uninstall buttons when tab changes
        self.selected_package = None
        self.install_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

        # Update search placeholder
        self.search_input.setPlaceholderText(f"Search available packages in {tab_name}...")

    def on_search_text_changed(self, text: str):
        """Handle search text changes - trigger search on Enter or button click only."""
        # Enable/disable search button based on input
        self.search_btn.setEnabled(len(text.strip()) > 0)

    def search_packages(self):
        """Search available packages and display in the shared table."""
        query = self.search_input.text().strip()

        if not query:
            QMessageBox.warning(self, "No Query", "Please enter a search term.")
            return

        # Get managers from active tab
        managers_filter = self.get_active_managers()
        tab_name = self.get_active_tab_name()

        print(f"[MainWindow] Searching for '{query}' in available packages ({tab_name})")

        repo_text = tab_name.lower()

        try:
            # Check if cache needs refresh
            cache_count = self.metadata_cache.get_package_count('winget')

            if cache_count == 0:
                # First time - refresh cache
                reply = QMessageBox.question(
                    self,
                    "Initialize Cache",
                    "The package metadata cache is empty. Would you like to initialize it now?\n\n"
                    "This will take about 30 seconds and only needs to be done once.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    self.refresh_metadata_cache()
                    # After refresh, search again
                    self.search_packages()
                return

            # Search the cache with selected repositories
            results = self.metadata_cache.search(query, managers=managers_filter, limit=100)

            if results:
                # Convert to Package objects
                packages = [metadata.to_package(cache_service=self.metadata_cache) for metadata in results]

                # Store and display in shared table
                self.current_packages = packages
                self.package_table.set_packages(packages)
                self.table_mode = 'available'  # Track that table now shows available packages

                # Disable both buttons until a package is selected
                self.install_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)
                self.selected_package = None

                self.persistent_status = f"Found {len(packages)} results for '{query}' in {repo_text}"
                self.status_label.setText(self.persistent_status)

                print(f"[MainWindow] Found {len(packages)} results from {repo_text}")
            else:
                self.package_table.clear_packages()
                self.table_mode = None
                self.persistent_status = f"No results found for '{query}' in {repo_text}"
                self.status_label.setText(self.persistent_status)
                QMessageBox.information(
                    self,
                    "No Results",
                    f"No packages found matching '{query}' in {repo_text}."
                )

        except Exception as e:
            print(f"[MainWindow] Search error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Search Error",
                f"An error occurred while searching: {str(e)}"
            )


    def refresh_metadata_cache(self):
        """Refresh the metadata cache from providers."""
        print("[MainWindow] Refreshing metadata cache...")

        # Show progress
        self.status_label.setText("Refreshing package metadata cache...")
        QApplication.processEvents()  # Update UI

        try:
            # Prevent system sleep during cache refresh
            with WindowsPowerManager.prevent_sleep():
                for provider in self.metadata_cache.providers:
                    self.metadata_cache.refresh_cache(manager=provider.get_manager_name(), force=True)

            total_count = self.metadata_cache.get_package_count()
            self.status_label.setText(f"Cache refreshed: {total_count} packages indexed")

            QMessageBox.information(
                self,
                "Cache Refreshed",
                f"Successfully cached {total_count} packages."
            )

        except Exception as e:
            print(f"[MainWindow] Cache refresh error: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Cache Error",
                f"An error occurred while refreshing cache: {str(e)}"
            )


    def on_verbose_toggled(self, checked: bool):
        """Handle verbose mode menu toggle."""
        self.verbose_mode = checked
        status = "enabled" if self.verbose_mode else "disabled"
        print(f"[MainWindow] Verbose mode {status}")

    def install_package(self):
        """Install selected package or manual package ID (WinGet only)."""
        # 1. Handle manual package ID entry if no package selected
        if not self.selected_package:
            # Check if WinGet tab is selected or All Packages tab
            active_managers = self.get_active_managers()
            # Allow manual entry only on WinGet tab or All Packages tab
            is_winget_context = (
                active_managers is None or  # All Packages
                (active_managers and 'winget' in active_managers)  # WinGet tab
            )

            if not is_winget_context:
                QMessageBox.warning(
                    self,
                    "No Package Selected",
                    "Please select a package from the list to install.\n\n"
                    "Manual package ID entry is only available on the WinGet or All Packages tab."
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
                "Please select an installed package to uninstall."
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
        """Handle loaded packages (legacy method - kept for compatibility)."""
        print(f"[MainWindow] on_packages_loaded: Received {len(packages)} packages")
        # This method is kept for compatibility but is no longer used in the new UI
        # Packages are now loaded directly via list_installed_packages() and search_packages()

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
            self.list_installed_packages()
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
            self.list_installed_packages()
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

        def get_install_path(app_key):
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
                    # Extract directory from uninstall path
                    # e.g., "C:\Program Files\Vim\vim91\uninstall.exe" -> "C:\Program Files\Vim"
                    match = re.search(r'^"?([A-Z]:[^"]+?)\\[^\\]+\.exe', uninstall_string, re.IGNORECASE)
                    if match:
                        path = match.group(1)

                        # Decide whether to use path or parent directory
                        # Check if path looks like a versioned subdirectory (e.g., "vim91", "v1.2.3")
                        path_basename = os.path.basename(path).lower()

                        # Patterns that indicate a versioned subdirectory
                        is_version_subdir = (
                            re.search(r'(^|[^a-z])(v?\d+\.?\d*|bin|app|x64|x86|win\d+)$', path_basename) or
                            'uninstall' in path_basename
                        )

                        if is_version_subdir:
                            # Use parent directory for versioned subdirs (e.g., vim91 -> Vim)
                            parent = os.path.dirname(path)
                            if parent and os.path.exists(parent):
                                return parent

                        # Use the extracted path itself
                        if path and os.path.exists(path):
                            return path
            except FileNotFoundError:
                pass

            # Method 4: Extract from InstallString
            try:
                install_string = winreg.QueryValueEx(app_key, "InstallString")[0]
                if install_string:
                    match = re.search(r'^"?([A-Z]:[^"]+?)\\[^\\]+\.exe', install_string, re.IGNORECASE)
                    if match:
                        path = match.group(1)
                        path_basename = os.path.basename(path).lower()

                        # Check if path looks like a versioned subdirectory
                        is_version_subdir = (
                            re.search(r'(^|[^a-z])(v?\d+\.?\d*|bin|app|x64|x86|win\d+)$', path_basename) or
                            'uninstall' in path_basename or
                            'install' in path_basename
                        )

                        if is_version_subdir:
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
                                        install_path = get_install_path(app_key)

                                        # Track ALL entries with DisplayName (even without install path)
                                        if display_name:
                                            registry_entries_total += 1
                                            if len(sample_all_entries) < 20:
                                                has_path = "[+]" if install_path else "[-]"
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
                print(f"[InstallPath] Sample of ALL registry entries ([+]=has path, [-]=no path):")
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
                    print(f"[InstallPath] [OK] Returning best match: {candidates[0][1]}")
                    return candidates[0][2]
                else:
                    print(f"[InstallPath] [SKIP] Best match confidence too low ({candidates[0][0]}), returning None")
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
                                        print(f"[InstallPath] [OK] Found via winget show: {install_path}")
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

        # Package info - show source for installed packages
        if package.status == PackageStatus.INSTALLED:
            info_text = (
                f"Name: {package.name}\n"
                f"Version: {package.version}\n"
                f"Status: Installed\n"
                f"Source: {self._format_manager_name(package.manager.value)}\n"
                f"Description: {package.description or 'N/A'}"
            )
        else:
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

    def _format_manager_name(self, manager_value: str) -> str:
        """
        Format package manager name for display.

        Args:
            manager_value: Raw manager value from enum (e.g., "winget", "unknown")

        Returns:
            Formatted display name (e.g., "WinGet", "Unknown")
        """
        formatting_map = {
            'winget': 'WinGet',
            'chocolatey': 'Chocolatey',
            'pip': 'Pip',
            'npm': 'NPM',
            'scoop': 'Scoop',
            'msstore': 'MS Store',
            'unknown': 'Unknown'
        }
        return formatting_map.get(manager_value, manager_value.capitalize())

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
            f"<b>Success:</b> {'Yes' if result.success else 'No'}<br>"
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
        self.repo_tabs.setEnabled(False)
        self.list_installed_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        self.install_btn.setEnabled(False)
        self.uninstall_btn.setEnabled(False)

    def enable_controls(self):
        """Enable controls after operation."""
        self.repo_tabs.setEnabled(True)
        self.list_installed_btn.setEnabled(True)

        # Only enable search if there's text in the search box
        self.search_btn.setEnabled(len(self.search_input.text().strip()) > 0)

        # Only enable Install/Uninstall if package is selected based on table mode
        if self.selected_package:
            if self.table_mode == 'installed':
                self.uninstall_btn.setEnabled(True)
            elif self.table_mode == 'available':
                self.install_btn.setEnabled(True)

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

    def show_keyboard_shortcuts(self):
        """Show keyboard shortcuts dialog with rendered markdown."""
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

    def restore_window_geometry(self):
        """Restore window size and position from saved settings."""
        try:
            # Get saved window state
            window_state = self.settings_service.get_window_state()

            if window_state:
                # Restore size
                width = window_state.get('width', 1000)
                height = window_state.get('height', 700)
                self.resize(width, height)

                # Restore position
                x = window_state.get('x')
                y = window_state.get('y')
                if x is not None and y is not None:
                    self.move(x, y)

                # Restore maximized state
                if window_state.get('maximized', False):
                    self.showMaximized()

                print(f"[MainWindow] Restored window geometry: {width}x{height} at ({x}, {y})")
            else:
                # Use default size if no saved state
                self.resize(1000, 700)
                print("[MainWindow] Using default window geometry: 1000x700")

        except Exception as e:
            print(f"[MainWindow] Error restoring window geometry: {e}")
            # Fall back to default size
            self.resize(1000, 700)

    def save_window_geometry(self):
        """Save current window size and position to settings."""
        try:
            # Get current geometry
            geometry = self.geometry()
            is_maximized = self.isMaximized()

            # Save window state
            window_state = {
                'width': geometry.width(),
                'height': geometry.height(),
                'x': geometry.x(),
                'y': geometry.y(),
                'maximized': is_maximized
            }

            self.settings_service.set_window_state(window_state)
            print(f"[MainWindow] Saved window geometry: {window_state}")

        except Exception as e:
            print(f"[MainWindow] Error saving window geometry: {e}")

    def closeEvent(self, event):
        """Handle window close event - save geometry before closing."""
        # Save window geometry
        self.save_window_geometry()

        # Accept the close event
        event.accept()

    # Markdown Help System Methods
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
