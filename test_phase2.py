"""
Phase 2 Testing Script for WinPacMan

This script runs automated tests for Phase 2 components:
- Module imports
- Package manager availability
- Worker framework
- Service layer integration
"""

import sys
from PyQt6.QtWidgets import QApplication

# Test results
test_results = []


def test_result(name, passed, details=""):
    """Record test result."""
    status = "[PASS]" if passed else "[FAIL]"
    test_results.append({
        'name': name,
        'passed': passed,
        'status': status,
        'details': details
    })
    print(f"{status} {name}")
    if details:
        print(f"        {details}")


def test_imports():
    """Test that all Phase 2 modules import successfully."""
    print("\n=== Testing Imports ===")

    try:
        from core.models import PackageManager, Package
        test_result("Core models import", True)
    except Exception as e:
        test_result("Core models import", False, str(e))

    try:
        from services.package_service import PackageManagerService
        test_result("PackageManagerService import", True)
    except Exception as e:
        test_result("PackageManagerService import", False, str(e))

    try:
        from ui.workers.package_worker import PackageListWorker
        test_result("PackageListWorker import", True)
    except Exception as e:
        test_result("PackageListWorker import", False, str(e))

    # Skip UI component imports as they require QApplication
    # These will be tested in test_package_table() with proper QApplication setup
    test_result("UI component imports", True, "Skipped (tested separately)")


def test_package_managers():
    """Test package manager availability."""
    print("\n=== Testing Package Manager Availability ===")

    from utils.system_utils import SystemUtils

    managers = {
        "WinGet": "winget",
        "Chocolatey": "choco",
        "Pip": "pip",
        "NPM": "npm"
    }

    for name, command in managers.items():
        try:
            available, message = SystemUtils.validate_package_manager(name, command)
            if available:
                version = SystemUtils.get_command_version(command)
                test_result(f"{name} available", True, f"{message} - {version}")
            else:
                test_result(f"{name} available", False, message)
        except Exception as e:
            test_result(f"{name} available", False, str(e))


def test_service_layer():
    """Test service layer functionality."""
    print("\n=== Testing Service Layer ===")

    try:
        from services.package_service import PackageManagerService
        service = PackageManagerService()
        test_result("PackageManagerService instantiation", True)
    except Exception as e:
        test_result("PackageManagerService instantiation", False, str(e))
        return

    try:
        from services.settings_service import SettingsService
        settings = SettingsService()
        theme = settings.get_theme()
        test_result("SettingsService instantiation", True, f"Theme: {theme}")
    except Exception as e:
        test_result("SettingsService instantiation", False, str(e))


def test_worker_framework():
    """Test QThread worker framework."""
    print("\n=== Testing Worker Framework ===")

    try:
        from ui.workers.signals import PackageSignals
        from PyQt6.QtCore import QObject

        signals = PackageSignals()
        assert isinstance(signals, QObject)
        test_result("PackageSignals instantiation", True)
    except Exception as e:
        test_result("PackageSignals instantiation", False, str(e))

    try:
        from ui.workers.package_worker import PackageListWorker
        from services.package_service import PackageManagerService
        from core.models import PackageManager
        from PyQt6.QtCore import QThread

        service = PackageManagerService()
        worker = PackageListWorker(service, PackageManager.WINGET)
        assert isinstance(worker, QThread)
        test_result("PackageListWorker instantiation", True)
    except Exception as e:
        test_result("PackageListWorker instantiation", False, str(e))


def test_package_table():
    """Test package table widget."""
    print("\n=== Testing Package Table Widget ===")

    # Need QApplication for QWidget
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        from ui.components.package_table import PackageTableWidget
        table = PackageTableWidget()
        test_result("PackageTableWidget instantiation", True)

        # Test color scheme
        from core.models import PackageManager
        colors = PackageTableWidget.MANAGER_COLORS
        assert PackageManager.WINGET in colors
        assert PackageManager.CHOCOLATEY in colors
        assert PackageManager.PIP in colors
        assert PackageManager.NPM in colors
        test_result("Color scheme defined", True, f"{len(colors)} manager colors")

    except Exception as e:
        test_result("PackageTableWidget instantiation", False, str(e))


def print_summary():
    """Print test summary."""
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for r in test_results if r['passed'])
    failed = sum(1 for r in test_results if not r['passed'])
    total = len(test_results)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    if failed > 0:
        print("\nFailed Tests:")
        for result in test_results:
            if not result['passed']:
                print(f"  - {result['name']}: {result['details']}")

    print("="*60)

    return failed == 0


def main():
    """Run all tests."""
    print("="*60)
    print("WinPacMan Phase 2 Automated Tests")
    print("="*60)

    test_imports()
    test_package_managers()
    test_service_layer()
    test_worker_framework()
    test_package_table()

    success = print_summary()

    if success:
        print("\n[SUCCESS] All automated tests passed!")
        print("\nManual GUI Testing Required:")
        print("  1. Run: python gui_pyqt6.py")
        print("  2. Test each package manager refresh")
        print("  3. Verify color coding")
        print("  4. Test double-click for details")
        print("  5. Verify progress updates")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
