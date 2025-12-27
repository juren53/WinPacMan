"""
WinGet metadata provider.

Reads package metadata from WinGet's local SQLite database (installed.db).
"""

import sqlite3
import os
from typing import Iterator, Optional
from datetime import datetime
from .base import MetadataProvider
from core.models import UniversalPackageMetadata, PackageManager


class WinGetProvider(MetadataProvider):
    """
    Provider for WinGet using local installed.db SQLite database.

    WinGet maintains a local cache of the entire community repository at:
    %LOCALAPPDATA%\\Packages\\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\\LocalState\\Microsoft.Winget.Source_8wekyb3d8bbwe\\installed.db
    """

    # Default path to WinGet's package database
    DEFAULT_DB_PATH = os.path.expandvars(
        r'%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\Microsoft.Winget.Source_8wekyb3d8bbwe\installed.db'
    )

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize WinGet provider.

        Args:
            db_path: Path to installed.db (uses default if None)
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._last_check_time: Optional[datetime] = None
        self._db_mod_time: Optional[float] = None

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Read all available packages from WinGet's installed.db.

        Yields:
            UniversalPackageMetadata for each package in the repository
        """
        if not os.path.exists(self.db_path):
            print(f"[WinGetProvider] Database not found: {self.db_path}")
            return

        print(f"[WinGetProvider] Reading from: {self.db_path}")

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Access columns by name
            cursor = conn.cursor()

            # Query to get package information
            # WinGet's installed.db uses normalized tables with foreign key references
            query = """
            SELECT DISTINCT
                manifest.rowid as manifest_id,
                ids.id as package_id,
                names.name as name,
                versions.version as version,
                norm_publishers.norm_publisher as publisher
            FROM manifest
            LEFT JOIN ids ON manifest.id = ids.rowid
            LEFT JOIN names ON manifest.name = names.rowid
            LEFT JOIN versions ON manifest.version = versions.rowid
            LEFT JOIN norm_publishers_map ON manifest.rowid = norm_publishers_map.manifest
            LEFT JOIN norm_publishers ON norm_publishers_map.norm_publisher = norm_publishers.rowid
            ORDER BY manifest.rowid
            LIMIT 10000
            """

            cursor.execute(query)

            for row in cursor.fetchall():
                package_id = row['package_id'] or str(row['manifest_id'])

                # Create package metadata from row
                package_data = {
                    'package_id': package_id,
                    'name': row['name'] or package_id,
                    'version': row['version'] or 'Unknown',
                    'publisher': row['publisher']
                }

                yield self._create_metadata(package_data)

            conn.close()
            print(f"[WinGetProvider] Finished reading packages")

        except sqlite3.Error as e:
            print(f"[WinGetProvider] Database error: {e}")
        except Exception as e:
            print(f"[WinGetProvider] Error: {e}")
            import traceback
            traceback.print_exc()

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific package via 'winget show' command.

        Args:
            package_id: Package ID to query

        Returns:
            UniversalPackageMetadata or None
        """
        import subprocess

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
                return self._parse_winget_show(result.stdout, package_id)

        except subprocess.TimeoutExpired:
            print(f"[WinGetProvider] Timeout getting details for {package_id}")
        except Exception as e:
            print(f"[WinGetProvider] Error getting details for {package_id}: {e}")

        return None

    def is_cache_stale(self) -> bool:
        """
        Check if installed.db has been modified since last check.

        Returns:
            True if database file has been modified
        """
        if not os.path.exists(self.db_path):
            return False

        current_mod_time = os.path.getmtime(self.db_path)

        if self._db_mod_time is None:
            self._db_mod_time = current_mod_time
            return True

        if current_mod_time > self._db_mod_time:
            self._db_mod_time = current_mod_time
            return True

        return False

    def get_manager_name(self) -> str:
        """Get the manager identifier."""
        return 'winget'

    def _create_metadata(self, data: dict) -> UniversalPackageMetadata:
        """
        Create UniversalPackageMetadata from parsed data.

        Args:
            data: Dictionary with package information

        Returns:
            UniversalPackageMetadata object
        """
        # Generate search tokens
        search_tokens = self._generate_tokens(
            data['package_id'],
            data['name'],
            data.get('publisher', '')
        )

        tags_str = ','.join(data.get('tags', [])) if data.get('tags') else None

        return UniversalPackageMetadata(
            package_id=data['package_id'],
            name=data['name'],
            version=data['version'],
            manager=PackageManager.WINGET,
            publisher=data.get('publisher'),
            search_tokens=search_tokens,
            tags=tags_str,
            cache_timestamp=datetime.now()
        )

    def _generate_tokens(self, *fields) -> str:
        """
        Generate space-separated search tokens from text fields.

        Args:
            *fields: Text fields to tokenize

        Returns:
            Space-separated lowercase tokens
        """
        tokens = set()

        for field in fields:
            if field:
                # Split on common delimiters
                parts = field.lower().replace('.', ' ').replace('-', ' ').replace('_', ' ').split()
                tokens.update(parts)

        return ' '.join(sorted(tokens))

    def _parse_winget_show(self, output: str, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Parse output from 'winget show' command.

        Args:
            output: Command output text
            package_id: Package ID

        Returns:
            UniversalPackageMetadata or None
        """
        lines = output.splitlines()
        metadata = {
            'package_id': package_id,
            'name': package_id,
            'version': 'Unknown'
        }

        for line in lines:
            line = line.strip()

            if line.startswith('Version:'):
                metadata['version'] = line.split(':', 1)[1].strip()
            elif line.startswith('Publisher:'):
                metadata['publisher'] = line.split(':', 1)[1].strip()
            elif line.startswith('Author:'):
                metadata['author'] = line.split(':', 1)[1].strip()
            elif line.startswith('Description:'):
                metadata['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('Homepage:'):
                metadata['homepage'] = line.split(':', 1)[1].strip()
            elif line.startswith('License:'):
                metadata['license'] = line.split(':', 1)[1].strip()

        return self._create_metadata(metadata)

    def fetch_all_packages(self, progress_callback=None) -> Iterator[UniversalPackageMetadata]:
        """
        Fetch all packages from the full WinGet repository.

        This method uses the winget.run API for fast initial sync.
        For self-hosted/offline scenarios, use GitHub manifest sync instead.

        Args:
            progress_callback: Optional callback(current, total, message)

        Yields:
            UniversalPackageMetadata for each package in the repository
        """
        from metadata.sync.wingetrun_fetcher import WinGetRunFetcher

        print("[WinGetProvider] Fetching full repository from winget.run API...")

        fetcher = WinGetRunFetcher()

        for pkg_data in fetcher.fetch_all_packages(progress_callback):
            # Convert to UniversalPackageMetadata
            metadata = UniversalPackageMetadata(
                package_id=pkg_data['package_id'],
                name=pkg_data['name'],
                version=pkg_data['version'],
                manager=PackageManager.WINGET,
                description=pkg_data.get('description'),
                publisher=pkg_data.get('publisher'),
                homepage=pkg_data.get('homepage'),
                license=pkg_data.get('license'),
                tags=pkg_data.get('tags'),
                search_tokens=self._generate_tokens(
                    pkg_data['package_id'],
                    pkg_data['name'],
                    pkg_data.get('publisher', '')
                ),
                cache_timestamp=datetime.now()
            )

            yield metadata
