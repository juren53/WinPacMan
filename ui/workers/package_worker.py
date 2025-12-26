"""
QThread-based workers for package operations.

Replaces threading.Thread-based PackageOperationWorker with PyQt6 QThread
workers that use signals for thread-safe communication.
"""

from PyQt6.QtCore import QThread
from typing import Callable, Optional, List

from core.models import Package, PackageManager, OperationResult
from services.package_service import PackageManagerService
from .signals import PackageSignals


class PackageListWorker(QThread):
    """
    Worker for listing installed packages in background thread.

    This worker calls PackageManagerService.get_installed_packages() in a
    background thread and emits signals for progress updates and completion.
    """

    def __init__(self, service: PackageManagerService, manager: PackageManager):
        """
        Initialize the worker.

        Args:
            service: PackageManagerService instance
            manager: Package manager to query (WINGET, CHOCOLATEY, PIP, NPM)
        """
        super().__init__()
        self.service = service
        self.manager = manager
        self.signals = PackageSignals()
        self._is_cancelled = False

    def run(self):
        """Execute package listing in background thread."""
        try:
            print(f"[Worker] Starting package list for {self.manager.value}")
            self.signals.started.emit()

            # Progress callback that emits signals
            def progress_callback(current: int, total: int, message: str):
                if not self._is_cancelled:
                    print(f"[Worker] Progress: {current}/{total} - {message}")
                    self.signals.progress.emit(current, total, message)

            # Call service layer (blocking operation)
            print(f"[Worker] Calling service.get_installed_packages({self.manager.value})")
            packages = self.service.get_installed_packages(
                self.manager,
                progress_callback
            )

            print(f"[Worker] Received {len(packages)} packages from service")

            # Emit result if not cancelled
            if not self._is_cancelled:
                print(f"[Worker] Emitting packages_loaded signal with {len(packages)} packages")
                self.signals.packages_loaded.emit(packages)
            else:
                print("[Worker] Operation was cancelled, not emitting packages")

        except Exception as e:
            # Emit error if not cancelled
            print(f"[Worker] ERROR: {type(e).__name__}: {str(e)}")
            if not self._is_cancelled:
                error_msg = f"Failed to list packages: {str(e)}"
                self.signals.error_occurred.emit(error_msg)
            import traceback
            traceback.print_exc()

        finally:
            # Always emit finished signal
            print("[Worker] Emitting finished signal")
            self.signals.finished.emit()

    def cancel(self):
        """
        Cancel the operation.

        Note: This sets a flag but doesn't forcefully stop the thread.
        The actual subprocess operation cannot be interrupted.
        """
        self._is_cancelled = True
        self.quit()


class PackageInstallWorker(QThread):
    """
    Worker for installing packages in background thread.

    This worker calls PackageManagerService.install_package() and emits
    signals for progress and completion.
    """

    def __init__(self, service: PackageManagerService,
                 manager: PackageManager, package_id: str):
        """
        Initialize the worker.

        Args:
            service: PackageManagerService instance
            manager: Package manager to use
            package_id: ID of package to install
        """
        super().__init__()
        self.service = service
        self.manager = manager
        self.package_id = package_id
        self.signals = PackageSignals()
        self._is_cancelled = False

    def run(self):
        """Execute package installation in background thread."""
        try:
            self.signals.started.emit()

            # Progress callback that emits signals
            def progress_callback(current: int, total: int, message: str):
                if not self._is_cancelled:
                    self.signals.progress.emit(current, total, message)

            # Call service layer (blocking operation)
            result = self.service.install_package(
                self.manager,
                self.package_id,
                progress_callback
            )

            # Emit result if not cancelled
            if not self._is_cancelled:
                self.signals.operation_complete.emit(result)

        except Exception as e:
            # Emit error if not cancelled
            if not self._is_cancelled:
                error_msg = f"Failed to install package: {str(e)}"
                self.signals.error_occurred.emit(error_msg)

        finally:
            # Always emit finished signal
            self.signals.finished.emit()

    def cancel(self):
        """Cancel the operation."""
        self._is_cancelled = True
        self.quit()


class PackageUninstallWorker(QThread):
    """
    Worker for uninstalling packages in background thread.

    This worker calls PackageManagerService.uninstall_package() and emits
    signals for progress and completion.
    """

    def __init__(self, service: PackageManagerService,
                 manager: PackageManager, package_id: str):
        """
        Initialize the worker.

        Args:
            service: PackageManagerService instance
            manager: Package manager to use
            package_id: ID of package to uninstall
        """
        super().__init__()
        self.service = service
        self.manager = manager
        self.package_id = package_id
        self.signals = PackageSignals()
        self._is_cancelled = False

    def run(self):
        """Execute package uninstallation in background thread."""
        try:
            self.signals.started.emit()

            # Progress callback that emits signals
            def progress_callback(current: int, total: int, message: str):
                if not self._is_cancelled:
                    self.signals.progress.emit(current, total, message)

            # Call service layer (blocking operation)
            result = self.service.uninstall_package(
                self.manager,
                self.package_id,
                progress_callback
            )

            # Emit result if not cancelled
            if not self._is_cancelled:
                self.signals.operation_complete.emit(result)

        except Exception as e:
            # Emit error if not cancelled
            if not self._is_cancelled:
                error_msg = f"Failed to uninstall package: {str(e)}"
                self.signals.error_occurred.emit(error_msg)

        finally:
            # Always emit finished signal
            self.signals.finished.emit()

    def cancel(self):
        """Cancel the operation."""
        self._is_cancelled = True
        self.quit()
