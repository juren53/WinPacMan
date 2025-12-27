"""
Installed packages discovery via Windows Registry scanning.

Provides fast package discovery by scanning Windows Registry Uninstall keys
and using fingerprint detection to identify package manager sources.
"""

import winreg
import os
import json
from typing import List, Optional, Set
from dataclasses import dataclass

from core.models import UniversalPackageMetadata, PackageManager


@dataclass
class RegistryPackageInfo:
    """Raw package information from Windows Registry."""
    display_name: str
    display_version: str
    install_location: Optional[str] = None
    install_source: Optional[str] = None
    install_date: Optional[str] = None
    publisher: Optional[str] = None
    uninstall_string: Optional[str] = None


class InstalledRegistryProvider:
    """
    Fast installed packages discovery via Windows Registry.

    Scans Windows Registry Uninstall keys to discover installed applications
    and uses fingerprint detection to determine package manager source.

    Performance: ~1-2 seconds for complete system scan
    """

    REGISTRY_PATHS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    def scan_registry(self) -> List[UniversalPackageMetadata]:
        """
        Scan all registry uninstall keys for installed applications.

        Returns:
            List of UniversalPackageMetadata objects with install information
        """
        print("[InstalledRegistryProvider] Starting registry scan...")
        packages = []

        for hive, path in self.REGISTRY_PATHS:
            packages.extend(self._scan_registry_key(hive, path))

        print(f"[InstalledRegistryProvider] Found {len(packages)} packages in registry")
        return packages

    def _scan_registry_key(self, hive, path: str) -> List[UniversalPackageMetadata]:
        """
        Scan a single registry key for installed applications.

        Args:
            hive: Registry hive (HKLM or HKCU)
            path: Registry path to scan

        Returns:
            List of UniversalPackageMetadata objects
        """
        packages = []

        try:
            with winreg.OpenKey(hive, path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]

                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as app_key:
                            # Extract package info
                            pkg_info = self._extract_package_info(app_key)

                            if pkg_info and pkg_info.display_name:
                                # Detect package manager source via fingerprints
                                install_source = self.detect_manager(
                                    pkg_info.install_source,
                                    pkg_info.install_location,
                                    pkg_info.display_name
                                )

                                # Create UniversalPackageMetadata object
                                # Use install_source as manager for proper display
                                manager_enum = self._map_source_to_manager(install_source)

                                package = UniversalPackageMetadata(
                                    package_id=pkg_info.display_name,  # Use display name as ID
                                    name=pkg_info.display_name,
                                    version=pkg_info.display_version or "Unknown",
                                    manager=manager_enum,
                                    description="",  # Not available in registry
                                    publisher=pkg_info.publisher,
                                    is_installed=True,
                                    installed_version=pkg_info.display_version,
                                    install_date=pkg_info.install_date,
                                    install_source=install_source,
                                    install_location=pkg_info.install_location
                                )

                                packages.append(package)

                    except OSError:
                        # Skip inaccessible subkeys
                        continue

        except FileNotFoundError:
            # Registry key doesn't exist
            pass
        except Exception as e:
            print(f"[InstalledRegistryProvider] Error scanning {path}: {e}")

        return packages

    def _extract_package_info(self, app_key) -> Optional[RegistryPackageInfo]:
        """
        Extract package information from a registry key.

        Args:
            app_key: Open registry key handle

        Returns:
            RegistryPackageInfo object or None
        """
        def get_value(name: str) -> Optional[str]:
            """Get registry value, return None if not found."""
            try:
                value = winreg.QueryValueEx(app_key, name)[0]
                return value.strip() if value and isinstance(value, str) else value
            except FileNotFoundError:
                return None

        # Get display name (required)
        display_name = get_value("DisplayName")
        if not display_name:
            return None  # Skip entries without names

        return RegistryPackageInfo(
            display_name=display_name,
            display_version=get_value("DisplayVersion"),
            install_location=get_value("InstallLocation"),
            install_source=get_value("InstallSource"),
            install_date=get_value("InstallDate"),
            publisher=get_value("Publisher"),
            uninstall_string=get_value("UninstallString")
        )

    def _map_source_to_manager(self, install_source: str) -> PackageManager:
        """
        Map install source string to PackageManager enum.

        Args:
            install_source: Install source string (winget, chocolatey, scoop, msstore, unknown)

        Returns:
            PackageManager enum value
        """
        mapping = {
            'winget': PackageManager.WINGET,
            'chocolatey': PackageManager.CHOCOLATEY,
            'scoop': PackageManager.SCOOP,
            'msstore': PackageManager.MSSTORE,
            'unknown': PackageManager.UNKNOWN
        }
        return mapping.get(install_source, PackageManager.UNKNOWN)

    def detect_manager(self, install_source: Optional[str],
                      install_location: Optional[str],
                      display_name: str) -> str:
        """
        Detect package manager source using fingerprint analysis.

        Detection Rules (in order of priority):
        1. WinGet: InstallSource contains "winget" or "appinstaller"
        2. Chocolatey: InstallLocation/InstallSource contains "chocolatey" or "choco"
        3. Scoop: InstallLocation contains "scoop"
        4. MS Store: InstallLocation contains "WindowsApps"
        5. Unknown: No fingerprint detected

        Args:
            install_source: InstallSource registry value
            install_location: InstallLocation registry value
            display_name: DisplayName registry value

        Returns:
            Manager identifier: "winget", "chocolatey", "scoop", "msstore", "unknown"
        """
        install_source = (install_source or "").lower()
        install_location = (install_location or "").lower()
        display_name = (display_name or "").lower()

        # WinGet detection
        if "winget" in install_source or "appinstaller" in install_source:
            return "winget"

        # Chocolatey detection
        if "chocolatey" in install_location or "chocolatey" in install_source:
            return "chocolatey"
        if "choco" in install_source:
            return "chocolatey"

        # Scoop detection (usually in user profile)
        if "scoop" in install_location or "scoop" in install_source:
            return "scoop"

        # MS Store detection
        if "windowsapps" in install_location:
            return "msstore"

        # No fingerprint detected
        return "unknown"


class ScoopInstalledProvider:
    """
    Scoop-specific installed packages provider.

    Scoop doesn't use Windows Registry, so we scan its app directories directly.
    """

    def get_scoop_apps(self) -> List[UniversalPackageMetadata]:
        r"""
        Scan Scoop installation directory for installed packages.

        Scoop structure:
        - %USERPROFILE%\scoop\apps\<app_name>\current\ (symlink to active version)
        - manifest.json contains version and metadata

        Returns:
            List of UniversalPackageMetadata objects for Scoop packages
        """
        scoop_path = os.path.expandvars(r"%USERPROFILE%\scoop\apps")

        if not os.path.exists(scoop_path):
            # Scoop not installed
            return []

        print(f"[ScoopInstalledProvider] Scanning {scoop_path}...")
        packages = []

        try:
            for app_name in os.listdir(scoop_path):
                app_dir = os.path.join(scoop_path, app_name)
                current_dir = os.path.join(app_dir, "current")

                # Scoop uses 'current' symlink to point to active version
                if os.path.exists(current_dir):
                    version = "Unknown"
                    manifest_path = os.path.join(current_dir, "manifest.json")

                    # Read version from manifest if available
                    if os.path.exists(manifest_path):
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                version = data.get("version", "Unknown")
                        except (json.JSONDecodeError, IOError):
                            pass

                    packages.append(UniversalPackageMetadata(
                        package_id=app_name,
                        name=app_name,
                        version=version,
                        manager=PackageManager.SCOOP,
                        description="",
                        is_installed=True,
                        installed_version=version,
                        install_source="scoop",
                        install_location=current_dir
                    ))

        except Exception as e:
            print(f"[ScoopInstalledProvider] Error scanning Scoop apps: {e}")

        print(f"[ScoopInstalledProvider] Found {len(packages)} Scoop packages")
        return packages
