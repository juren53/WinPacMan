"""
Enhanced package table widget with color coding.

Provides a custom table widget for displaying packages with manager-specific
color coding and sorting capabilities.
"""

from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import List, Optional

from core.models import Package, PackageManager, PackageStatus


class PackageTableWidget(QTableWidget):
    """
    Custom table widget for displaying packages with color coding.
    
    Features:
    - Color-coded rows by package manager
    - Sortable columns
    - Double-click for package details
    - Single selection mode
    """
    
    # Signals
    package_selected = pyqtSignal(Package)
    package_double_clicked = pyqtSignal(Package)
    
    # Color scheme for package managers
    MANAGER_COLORS = {
        PackageManager.WINGET: QColor("#E8F5E8"),      # Light green
        PackageManager.CHOCOLATEY: QColor("#FFF4E6"),  # Light orange
        PackageManager.PIP: QColor("#E6F3FF"),         # Light blue
        PackageManager.NPM: QColor("#FCE6F3"),         # Light pink
        PackageManager.CARGO: QColor("#FFE6E6"),       # Light red/coral
        PackageManager.SCOOP: QColor("#F0E6FF"),       # Light purple
        PackageManager.MSSTORE: QColor("#E6FFFA"),     # Light cyan
        PackageManager.UNKNOWN: QColor("#F5F5F5")      # Light gray
    }
    
    def __init__(self, parent=None):
        """Initialize the package table widget."""
        super().__init__(parent)
        self.packages: List[Package] = []
        self.setup_table()
    
    def setup_table(self):
        """Configure table structure and behavior."""
        # Set column count and headers
        self.setColumnCount(4)
        header_labels = ["Package Name", "Version", "Manager", "Description"]
        for col, label in enumerate(header_labels):
            header_item = QTableWidgetItem(label)
            header_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.horizontalHeaderItem(col) # Ensure item exists
            self.setHorizontalHeaderItem(col, header_item)
        
        # Configure column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        # Set initial column widths
        self.setColumnWidth(0, 300)
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Alternating row colors
        self.setAlternatingRowColors(True)
        
        # Selection behavior
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # Edit triggers (none - read-only table)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Connect signals
        self.itemDoubleClicked.connect(self._on_double_click)
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def set_packages(self, packages: List[Package]):
        """
        Set packages to display in the table.

        Args:
            packages: List of Package objects to display
        """
        print(f"[PackageTable] set_packages called with {len(packages)} packages")
        self.packages = packages

        # Disable sorting while populating (for performance)
        self.setSortingEnabled(False)
        print(f"[PackageTable] Sorting disabled")

        # Clear existing content
        self.setRowCount(0)
        self.setRowCount(len(packages))
        print(f"[PackageTable] Row count set to {len(packages)}")

        # Populate table
        for row, package in enumerate(packages):
            if row < 3:  # Debug first 3 packages
                print(f"[PackageTable] Row {row}: {package.name} v{package.version} ({package.manager.value})")

            # Package name - STORE PACKAGE OBJECT IN USER DATA
            name_item = QTableWidgetItem(package.name)
            name_item.setData(Qt.ItemDataRole.UserRole, package)  # Store Package object
            self.setItem(row, 0, name_item)

            # Version
            version_item = QTableWidgetItem(package.version)
            self.setItem(row, 1, version_item)

            # Manager - show the actual package manager name
            manager_display = self._format_manager_name(package.manager.value)
            manager_item = QTableWidgetItem(manager_display)
            self.setItem(row, 2, manager_item)

            # Description
            desc_item = QTableWidgetItem(package.description or "")
            self.setItem(row, 3, desc_item)

            # Color coding removed - using system theme for better readability
            # self._apply_row_color(row, package.manager)

        print(f"[PackageTable] All {len(packages)} rows populated")

        # Re-enable sorting
        self.setSortingEnabled(True)
        print(f"[PackageTable] Sorting re-enabled, table should now display")
    
    def _format_manager_name(self, manager_value: str) -> str:
        """
        Format package manager name for display.

        Args:
            manager_value: Raw manager value from enum (e.g., "winget", "unknown")

        Returns:
            Formatted display name (e.g., "WinGet", "Unknown")
        """
        # Special formatting for specific managers
        formatting_map = {
            'winget': 'WinGet',
            'chocolatey': 'Chocolatey',
            'pip': 'Pip',
            'npm': 'NPM',
            'cargo': 'Cargo',
            'scoop': 'Scoop',
            'msstore': 'MS Store',
            'unknown': 'Unknown'
        }

        return formatting_map.get(manager_value, manager_value.capitalize())

    def _apply_row_color(self, row: int, manager: PackageManager):
        """
        Apply manager-specific color to row.

        Args:
            row: Row index
            manager: Package manager type
        """
        color = self.MANAGER_COLORS.get(manager, QColor("#FFFFFF"))
        text_color = QColor("#000000")  # Black text for readability

        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(color)
                item.setForeground(text_color)
    
    def get_selected_package(self) -> Optional[Package]:
        """
        Get currently selected package.

        Returns:
            Selected Package object or None
        """
        row = self.currentRow()
        if row < 0:
            return None

        # Get the Package object from the name column's user data
        # This works correctly even when the table is sorted
        name_item = self.item(row, 0)
        if name_item:
            package = name_item.data(Qt.ItemDataRole.UserRole)
            return package

        return None
    
    def _on_selection_changed(self):
        """Handle selection change event."""
        package = self.get_selected_package()
        if package:
            self.package_selected.emit(package)
    
    def _on_double_click(self, item):
        """Handle double-click event."""
        package = self.get_selected_package()
        if package:
            self.package_double_clicked.emit(package)
    
    def clear_packages(self):
        """Clear all packages from the table."""
        self.packages = []
        self.setRowCount(0)
