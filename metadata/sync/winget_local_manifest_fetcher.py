"""
Fetcher for WinGet packages by cloning and parsing local manifests from winget-pkgs GitHub repository.
"""

import os
import subprocess
import yaml
from typing import Iterator, Dict, Any, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path

from core.models import UniversalPackageMetadata, PackageManager
from packaging.version import Version # Import Version for comparison


class WinGetLocalManifestFetcher:
    """
    Fetches WinGet package metadata by cloning and parsing the
    microsoft/winget-pkgs GitHub repository locally.
    """

    REPO_URL = "https://github.com/microsoft/winget-pkgs"
    # Local path to store the cloned repository
    # Using a subdirectory within WinPacMan's data directory
    REPO_PATH = Path(os.path.expandvars(r"%LOCALAPPDATA%\WinPacMan\winget-pkgs"))
    
    def __init__(self):
        self._ensure_repo_exists()

    def _ensure_repo_exists(self):
        """
        Ensures the winget-pkgs repository is cloned and up to date.
        """
        if not self.REPO_PATH.exists():
            print(f"[WinGetLocalManifestFetcher] Cloning {self.REPO_URL} to {self.REPO_PATH}...")
            try:
                subprocess.run(
                    ['git', 'clone', self.REPO_URL, str(self.REPO_PATH)],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"[WinGetLocalManifestFetcher] Repository cloned successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[WinGetLocalManifestFetcher] Error cloning repository: {e.stderr}")
                raise
            except FileNotFoundError:
                print("[WinGetLocalManifestFetcher] 'git' command not found. Please install Git.")
                raise
        else:
            print(f"[WinGetLocalManifestFetcher] Updating {self.REPO_PATH}...")
            try:
                subprocess.run(
                    ['git', 'pull'],
                    cwd=str(self.REPO_PATH),
                    check=True,
                    capture_output=True,
                    text=True
                )
                print(f"[WinGetLocalManifestFetcher] Repository updated successfully.")
            except subprocess.CalledProcessError as e:
                print(f"[WinGetLocalManifestFetcher] Error updating repository: {e.stderr}")
                raise
            except FileNotFoundError:
                print("[WinGetLocalManifestFetcher] 'git' command not found. Please install Git.")
                raise

    def fetch_all_packages(self, progress_callback=None) -> Iterator[UniversalPackageMetadata]:
        """
        Parses local YAML manifests to yield UniversalPackageMetadata objects,
        filtering for the latest version of each package and skipping locale manifests.
        Uses a two-pass approach for accurate progress reporting and memory efficiency.
        """
        print(f"[WinGetLocalManifestFetcher] Scanning manifests from {self.REPO_PATH} for total count...")
        manifests_path = self.REPO_PATH / 'manifests'
        if not manifests_path.exists():
            print(f"[WinGetLocalManifestFetcher] Manifests path not found: {manifests_path}")
            return iter([])

        # First pass: Count processable files for accurate total_files for the progress bar
        total_processable_files = 0
        for path in manifests_path.rglob('*.yaml'):
            if ".locale." not in path.name:
                total_processable_files += 1

        if total_processable_files == 0:
            print(f"[WinGetLocalManifestFetcher] No processable YAML manifests found in {manifests_path}")
            return iter([])
        
        print(f"[WinGetLocalManifestFetcher] Found {total_processable_files} processable manifests. Starting detailed parsing...")

        from packaging.version import Version # Use packaging.version.Version for robust version comparison

        latest_packages: Dict[str, Dict[str, Any]] = {} # PackageIdentifier -> latest manifest data
        
        processed_files_count = 0
        for path in manifests_path.rglob('*.yaml'):
            if ".locale." in path.name:
                continue # Skip locale manifests

            processed_files_count += 1
            # Print to console for granular feedback
            print(f"[WinGetLocalManifestFetcher] Processed {processed_files_count}/{total_processable_files} - {path.name}")
            if progress_callback:
                progress_callback(processed_files_count, total_processable_files, f"Processing {path.name}")

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    manifest = yaml.safe_load(f)

                    package_id = manifest.get('PackageIdentifier')
                    package_version_str = manifest.get('PackageVersion')
                    
                    if not package_id or not package_version_str:
                        continue # Skip invalid manifests

                    try:
                        current_version = Version(package_version_str)
                    except Exception:
                        continue # Skip manifests with unparseable versions

                    if package_id not in latest_packages:
                        latest_packages[package_id] = manifest
                    else:
                        stored_version_str = latest_packages[package_id].get('PackageVersion')
                        try:
                            stored_version = Version(stored_version_str)
                        except Exception:
                            # If stored version is unparseable, replace with current valid one
                            latest_packages[package_id] = manifest
                            continue

                        if current_version > stored_version:
                            latest_packages[package_id] = manifest
            except (yaml.YAMLError, IOError) as e:
                print(f"[WinGetLocalManifestFetcher] Error reading or parsing manifest {path}: {e}")
            except Exception as e:
                print(f"[WinGetLocalManifestFetcher] Unexpected error processing {path}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[WinGetLocalManifestFetcher] Found {len(latest_packages)} unique packages. Yielding latest versions...")

        # Now, yield UniversalPackageMetadata for the latest version of each package
        for package_id, manifest in latest_packages.items():
            package_version = manifest.get('PackageVersion')
            name = manifest.get('PackageName', package_id)
            publisher = manifest.get('Publisher')
            description = manifest.get('ShortDescription') or manifest.get('Description')
            homepage = manifest.get('PackageUrl')
            license_info = manifest.get('License')
            tags = manifest.get('Tags', [])
            if isinstance(tags, list):
                tags_str = ','.join(tags)
            else:
                tags_str = str(tags) if tags else ''

            yield UniversalPackageMetadata(
                package_id=package_id,
                name=name,
                version=package_version,
                manager=PackageManager.WINGET,
                description=description,
                publisher=publisher,
                homepage=homepage,
                license=license_info,
                tags=tags_str,
                cache_timestamp=datetime.now()
            )
