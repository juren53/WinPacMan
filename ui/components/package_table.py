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

from core.models import Package, PackageManager


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
        PackageManager.NPM: QColor("#FCE6F3")          # Light pink
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
        self.setHorizontalHeaderLabels([
            "Package Name", "Version", "Manager", "Description"
        ])
        
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
        self.packages = packages
        
        # Disable sorting while populating (for performance)
        self.setSortingEnabled(False)
        
        # Clear existing content
        self.setRowCount(0)
        self.setRowCount(len(packages))
        
        # Populate table
        for row, package in enumerate(packages):
            # Package name
            name_item = QTableWidgetItem(package.name)
            self.setItem(row, 0, name_item)
            
            # Version
            version_item = QTableWidgetItem(package.version)
            self.setItem(row, 1, version_item)
            
            # Manager
            manager_item = QTableWidgetItem(package.manager.value)
            self.setItem(row, 2, manager_item)
            
            # Description
            desc_item = QTableWidgetItem(package.description or "")
            self.setItem(row, 3, desc_item)
            
            # Apply color coding
            self._apply_row_color(row, package.manager)
        
        # Re-enable sorting
        self.setSortingEnabled(True)
    
    def _apply_row_color(self, row: int, manager: PackageManager):
        """
        Apply manager-specific color to row.
        
        Args:
            row: Row index
            manager: Package manager type
        """
        color = self.MANAGER_COLORS.get(manager, QColor("#FFFFFF"))
        
        for col in range(self.columnCount()):
            item = self.item(row, col)
            if item:
                item.setBackground(color)
    
    def get_selected_package(self) -> Optional[Package]:
        """
        Get currently selected package.
        
        Returns:
            Selected Package object or None
        """
        row = self.currentRow()
        if 0 <= row < len(self.packages):
            return self.packages[row]
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
