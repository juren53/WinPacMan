"""
Custom signal definitions for WinPacMan PyQt6 workers.

Provides type-safe signals for package operations, progress updates,
and error handling across worker threads.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from typing import List


class PackageSignals(QObject):
    """
    Signals for package operations.

    These signals provide thread-safe communication between worker threads
    and the main UI thread. All signals are emitted from worker threads and
    should be connected to slots in the main thread.
    """

    # Progress signals
    progress = pyqtSignal(int, int, str)  # current, total, message
    """
    Emitted when operation progress updates.
    Args:
        current (int): Current progress value
        total (int): Total progress value
        message (str): Human-readable progress message
    """

    # Completion signals
    packages_loaded = pyqtSignal(list)    # List[Package]
    """
    Emitted when package list loading completes successfully.
    Args:
        packages (list): List of Package objects
    """

    operation_complete = pyqtSignal(object)  # OperationResult
    """
    Emitted when install/uninstall operation completes.
    Args:
        result (OperationResult): Result of the operation
    """

    # Error signals
    error_occurred = pyqtSignal(str)      # error message
    """
    Emitted when an error occurs during operation.
    Args:
        message (str): Error message
    """

    # Status signals
    started = pyqtSignal()
    """Emitted when operation starts."""

    finished = pyqtSignal()
    """Emitted when operation finishes (success or failure)."""
