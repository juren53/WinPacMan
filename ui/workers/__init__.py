"""
Worker threads for WinPacMan PyQt6 GUI.

This module provides QThread-based workers for non-blocking package operations.
Uses PyQt6 signals for thread-safe communication with the UI.
"""

from .signals import PackageSignals
from .package_worker import (
    PackageListWorker,
    PackageInstallWorker,
    PackageUninstallWorker
)

__all__ = [
    'PackageSignals',
    'PackageListWorker',
    'PackageInstallWorker',
    'PackageUninstallWorker'
]
