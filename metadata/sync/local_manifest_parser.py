"""
Local WinGet manifest parser.

Parses YAML manifests from a locally cloned microsoft/winget-pkgs repository.
This is the fastest and most reliable method for initial repository sync.
"""

import yaml
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from datetime import datetime
from packaging import version as pkg_version


class LocalManifestParser:
    """
    Parses WinGet manifests from local repository clone.

    Repository structure:
    manifests/[first-letter]/[Publisher]/[PackageName]/[Version]/
        ├── [Publisher].[PackageName].yaml (version manifest)
        ├── [Publisher].[PackageName].installer.yaml (installer manifest)
        └── [Publisher].[PackageName].locale.en-US.yaml (default locale)
    """

    def __init__(self, repo_path: str):
        """
        Initialize parser.

        Args:
            repo_path: Path to cloned winget-pkgs repository
        """
        self.repo_path = Path(repo_path)
        self.manifests_dir = self.repo_path / "manifests"

        if not self.manifests_dir.exists():
            raise ValueError(f"Manifests directory not found: {self.manifests_dir}")

    def find_all_packages(self) -> list[tuple[str, str]]:
        """
        Find all unique packages in the repository.

        Returns:
            List of (package_id, latest_version_path) tuples
        """
        print("[LocalParser] Scanning repository structure...")

        packages = {}  # package_id -> (version_str, version_path)

        # Walk through the manifests directory
        # Structure: manifests/[letter]/[Publisher]/[PackageName]/[Version]/
        for letter_dir in self.manifests_dir.iterdir():
            if not letter_dir.is_dir():
                continue

            for publisher_dir in letter_dir.iterdir():
                if not publisher_dir.is_dir():
                    continue

                for package_dir in publisher_dir.iterdir():
                    if not package_dir.is_dir():
                        continue

                    # Package ID is Publisher.PackageName
                    package_id = f"{publisher_dir.name}.{package_dir.name}"

                    # Find all version directories
                    versions = []
                    for version_dir in package_dir.iterdir():
                        if version_dir.is_dir():
                            versions.append((version_dir.name, version_dir))

                    if not versions:
                        continue

                    # Sort versions and get the latest
                    try:
                        # Use packaging library for proper semantic version sorting
                        versions.sort(key=lambda x: pkg_version.parse(x[0]), reverse=True)
                    except Exception:
                        # Fallback to string sorting if version parsing fails
                        versions.sort(reverse=True)

                    latest_version, latest_path = versions[0]
                    packages[package_id] = (latest_version, latest_path)

        print(f"[LocalParser] Found {len(packages)} unique packages")
        return [(pkg_id, str(path)) for pkg_id, (ver, path) in packages.items()]

    def parse_package(self, package_id: str, version_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse manifest files for a specific package version.

        Args:
            package_id: Package identifier (e.g., "Microsoft.VisualStudioCode")
            version_path: Path to version directory

        Returns:
            Dictionary with package metadata or None
        """
        version_dir = Path(version_path)

        if not version_dir.exists():
            return None

        # Look for manifest files
        # Priority: version manifest > installer manifest > locale manifest
        manifest_data = {}

        # Try to find and parse each type of manifest
        for yaml_file in version_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data:
                        # Merge data (later files override earlier ones)
                        manifest_data.update(data)
            except Exception as e:
                # Skip files that fail to parse
                continue

        if not manifest_data:
            return None

        # Extract metadata
        try:
            return {
                'package_id': package_id,
                'name': manifest_data.get('PackageName', package_id),
                'version': manifest_data.get('PackageVersion', version_dir.name),
                'publisher': manifest_data.get('Publisher', ''),
                'description': manifest_data.get('ShortDescription',
                                                manifest_data.get('Description', '')),
                'homepage': manifest_data.get('PackageUrl', ''),
                'license': manifest_data.get('License', ''),
                'tags': manifest_data.get('Tags', []),
            }
        except Exception as e:
            print(f"[LocalParser] Error parsing {package_id}: {e}")
            return None

    def parse_all_packages(self, progress_callback=None) -> Iterator[Dict[str, Any]]:
        """
        Parse all packages in the repository.

        Args:
            progress_callback: Optional callback(current, total, message)

        Yields:
            Package metadata dictionaries
        """
        packages = self.find_all_packages()
        total = len(packages)

        print(f"[LocalParser] Parsing {total} packages...")

        for i, (package_id, version_path) in enumerate(packages, 1):
            if progress_callback and i % 100 == 0:
                progress_callback(i, total, f"Parsing package {i}/{total}")

            metadata = self.parse_package(package_id, version_path)
            if metadata:
                yield metadata

        print(f"[LocalParser] Finished parsing {total} packages")
