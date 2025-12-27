"""
Metadata cache service.

Central service for managing unified package metadata cache with fast FTS search.
"""

import sqlite3
import os
from typing import List, Optional, Iterator
from datetime import datetime
from core.models import UniversalPackageMetadata, PackageManager
from .providers.base import MetadataProvider


class MetadataCacheService:
    """
    Central service for managing unified package metadata cache.

    Provides:
    - SQLite cache database with FTS5 full-text search
    - Provider registration and management
    - Cache refresh from providers
    - Fast search across all registered package managers
    """

    def __init__(self, cache_db_path: str):
        """
        Initialize the metadata cache service.

        Args:
            cache_db_path: Path to SQLite cache database
        """
        self.cache_db_path = cache_db_path
        self.providers: List[MetadataProvider] = []
        self._init_database()

    def _init_database(self):
        """Initialize the cache database schema."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)

        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Main packages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id TEXT NOT NULL,
            name TEXT NOT NULL,
            version TEXT NOT NULL,
            manager TEXT NOT NULL,
            description TEXT,
            author TEXT,
            publisher TEXT,
            homepage TEXT,
            license TEXT,
            extra_metadata TEXT,
            search_tokens TEXT,
            tags TEXT,
            cache_timestamp INTEGER,
            is_installed INTEGER DEFAULT 0,
            installed_version TEXT,
            install_date TEXT,
            install_source TEXT,
            install_location TEXT,
            UNIQUE(package_id, manager)
        )
        """)

        # Migrate existing databases - add new columns if they don't exist
        self._migrate_schema(cursor)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manager ON packages(manager)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installed ON packages(is_installed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_install_source ON packages(install_source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON packages(cache_timestamp)")

        # Create FTS5 virtual table for full-text search
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS packages_fts USING fts5(
            package_id, name, description, search_tokens, tags,
            content='packages',
            content_rowid='id'
        )
        """)

        # Create triggers to keep FTS index in sync
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS packages_ai AFTER INSERT ON packages BEGIN
            INSERT INTO packages_fts(rowid, package_id, name, description, search_tokens, tags)
            VALUES (new.id, new.package_id, new.name, new.description, new.search_tokens, new.tags);
        END
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS packages_ad AFTER DELETE ON packages BEGIN
            DELETE FROM packages_fts WHERE rowid = old.id;
        END
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS packages_au AFTER UPDATE ON packages BEGIN
            UPDATE packages_fts SET
                package_id = new.package_id,
                name = new.name,
                description = new.description,
                search_tokens = new.search_tokens,
                tags = new.tags
            WHERE rowid = new.id;
        END
        """)

        conn.commit()
        conn.close()

        print(f"[MetadataCache] Initialized database: {self.cache_db_path}")

    def _migrate_schema(self, cursor):
        """
        Migrate existing database schema to add new columns.

        Handles upgrading existing databases that don't have the installed
        package tracking columns.
        """
        # Get existing columns
        cursor.execute("PRAGMA table_info(packages)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # Add missing columns
        new_columns = {
            'installed_version': 'TEXT',
            'install_date': 'TEXT',
            'install_source': 'TEXT',
            'install_location': 'TEXT'
        }

        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                print(f"[MetadataCache] Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE packages ADD COLUMN {column_name} {column_type}")

    def register_provider(self, provider: MetadataProvider):
        """
        Register a package manager provider.

        Args:
            provider: MetadataProvider instance
        """
        self.providers.append(provider)
        print(f"[MetadataCache] Registered provider: {provider.get_manager_name()}")

    def refresh_cache(self, manager: Optional[str] = None, packages=None, force: bool = False):
        """
        Refresh metadata cache from providers.

        Args:
            manager: Specific manager to refresh (None = all)
            packages: Optional iterator/list of packages to cache (if None, fetch from provider)
            force: Force refresh even if cache is fresh
        """
        # If packages provided, bulk update for specified manager
        if packages is not None:
            if not manager:
                raise ValueError("Manager name required when providing packages")

            print(f"[MetadataCache] Bulk updating cache for {manager}...")

            # Clear existing cache for this manager
            self._clear_manager_cache(manager)

            # Insert new metadata
            count = 0
            for package in packages:
                self._insert_package(package)
                count += 1

                if count % 500 == 0:
                    print(f"[MetadataCache] Cached {count} packages from {manager}...")

            print(f"[MetadataCache] Finished caching {count} packages from {manager}")
            return

        # Default behavior: fetch from providers
        for provider in self.providers:
            # Skip if not specified
            if manager and provider.get_manager_name() != manager:
                continue

            # Skip if cache is fresh and not forcing
            if not force and not provider.is_cache_stale():
                print(f"[MetadataCache] Cache fresh for {provider.get_manager_name()}, skipping")
                continue

            print(f"[MetadataCache] Refreshing cache for {provider.get_manager_name()}...")

            # Clear existing cache for this manager
            self._clear_manager_cache(provider.get_manager_name())

            # Insert new metadata
            count = 0
            for package in provider.get_available_packages():
                self._insert_package(package)
                count += 1

                if count % 100 == 0:
                    print(f"[MetadataCache] Cached {count} packages from {provider.get_manager_name()}...")

            print(f"[MetadataCache] Finished caching {count} packages from {provider.get_manager_name()}")

    def search(self, query: str, managers: Optional[List[str]] = None, limit: int = 100) -> List[UniversalPackageMetadata]:
        """
        Search across all managers using FTS.

        Args:
            query: Search query string
            managers: List of managers to search (None = all)
            limit: Maximum results to return

        Returns:
            List of matching UniversalPackageMetadata objects
        """
        conn = sqlite3.connect(self.cache_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Sanitize query for FTS5: quote special characters
        # FTS5 special chars: " - ( ) : * AND OR NOT
        # Escape double quotes and wrap in quotes for phrase search
        fts_query = query.replace('"', '""')  # Escape existing quotes
        fts_query = f'"{fts_query}"'  # Wrap in quotes for phrase search

        # Build WHERE clause for manager filter
        manager_filter = ""
        params = [fts_query]

        if managers:
            placeholders = ','.join(['?' for _ in managers])
            manager_filter = f"AND p.manager IN ({placeholders})"
            params.extend(managers)

        # FTS search query
        sql = f"""
        SELECT p.* FROM packages p
        JOIN packages_fts fts ON p.id = fts.rowid
        WHERE packages_fts MATCH ?
        {manager_filter}
        ORDER BY rank
        LIMIT ?
        """

        params.append(limit)

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_package(row))

        conn.close()

        return results

    def get_package_count(self, manager: Optional[str] = None) -> int:
        """
        Get count of cached packages.

        Args:
            manager: Specific manager (None = all)

        Returns:
            Package count
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        if manager:
            cursor.execute("SELECT COUNT(*) FROM packages WHERE manager = ?", (manager,))
        else:
            cursor.execute("SELECT COUNT(*) FROM packages")

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def _clear_manager_cache(self, manager: str):
        """
        Clear all cached packages for a specific manager.

        Args:
            manager: Manager name
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM packages WHERE manager = ?", (manager,))

        conn.commit()
        conn.close()

    def _insert_package(self, package: UniversalPackageMetadata):
        """
        Insert or update a package in the cache.

        Args:
            package: UniversalPackageMetadata to insert
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT OR REPLACE INTO packages (
            package_id, name, version, manager,
            description, author, publisher, homepage, license,
            extra_metadata, search_tokens, tags,
            cache_timestamp, is_installed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            package.package_id,
            package.name,
            package.version,
            package.manager.value,
            package.description,
            package.author,
            package.publisher,
            package.homepage,
            package.license,
            package.extra_metadata,
            package.search_tokens,
            package.tags,
            int(package.cache_timestamp.timestamp()) if package.cache_timestamp else None,
            1 if package.is_installed else 0
        ))

        conn.commit()
        conn.close()

    def sync_installed_packages_from_registry(self, validate: bool = True):
        """
        Sync installed package state from Windows Registry.

        Uses registry scanning for fast discovery (1-2 seconds) with optional
        validation against package manager databases for accuracy.

        Args:
            validate: If True, cross-reference with manager-specific databases
                     (Currently not implemented, reserved for future enhancement)
        """
        from metadata.providers.installed_registry_provider import (
            InstalledRegistryProvider,
            ScoopInstalledProvider
        )

        print("[MetadataCache] Syncing installed packages from registry...")

        # Tier 1: Registry scan
        registry_provider = InstalledRegistryProvider()
        packages = registry_provider.scan_registry()

        # Add Scoop packages (doesn't use registry)
        scoop_provider = ScoopInstalledProvider()
        packages.extend(scoop_provider.get_scoop_apps())

        # TODO: Tier 2: Validation (future enhancement)
        # if validate:
        #     winget_validator = WinGetValidationProvider()
        #     packages = winget_validator.validate(packages)
        #
        #     choco_validator = ChocolateyValidationProvider()
        #     packages = choco_validator.validate(packages)

        # Update cache with installed state
        self._update_installed_state(packages)

        print(f"[MetadataCache] Synced {len(packages)} installed packages")

    def get_installed_packages(self, managers: Optional[List[str]] = None,
                               source: Optional[str] = None) -> List[UniversalPackageMetadata]:
        """
        Get all installed packages, optionally filtered by manager or source.

        Args:
            managers: Filter by package manager repository (winget, chocolatey, etc.)
                     None = all managers
            source: Filter by install source (winget, chocolatey, manual, scoop, msstore)
                   None = all sources

        Returns:
            List of UniversalPackageMetadata objects for installed packages
        """
        conn = sqlite3.connect(self.cache_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM packages WHERE is_installed = 1"
        params = []

        if managers:
            placeholders = ','.join('?' * len(managers))
            query += f" AND manager IN ({placeholders})"
            params.extend(managers)

        if source:
            query += " AND install_source = ?"
            params.append(source)

        cursor.execute(query, params)
        packages = [self._row_to_package(row) for row in cursor.fetchall()]

        conn.close()
        return packages

    def get_manager_for_package(self, package_id: str, package_name: str = None) -> Optional[str]:
        """
        Query available packages cache to determine which manager can manage a package.

        This is used for installed packages where registry fingerprinting failed to
        detect the source manager. We lookup the package in available repos to find
        which manager can still manage it.

        Args:
            package_id: Package ID to search for
            package_name: Optional package name for fuzzy matching

        Returns:
            Manager name (winget, chocolatey, etc.) or None if not found in repos
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Try exact package_id match first
        cursor.execute("""
            SELECT manager FROM packages
            WHERE package_id = ? AND is_installed = 0
            LIMIT 1
        """, (package_id,))

        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]

        # Try case-insensitive package_id match
        cursor.execute("""
            SELECT manager FROM packages
            WHERE LOWER(package_id) = LOWER(?) AND is_installed = 0
            LIMIT 1
        """, (package_id,))

        row = cursor.fetchone()
        if row:
            conn.close()
            return row[0]

        # If package_name provided, try name match as fallback
        if package_name:
            cursor.execute("""
                SELECT manager FROM packages
                WHERE LOWER(name) = LOWER(?) AND is_installed = 0
                LIMIT 1
            """, (package_name,))

            row = cursor.fetchone()
            if row:
                conn.close()
                return row[0]

        conn.close()
        return None

    def _update_installed_state(self, packages: List):
        """
        Update cache with installed package state from registry scan.

        Strategy:
        - Clear all is_installed flags (all packages marked as not installed)
        - Insert or update packages from registry scan
        - Mark them as installed with install metadata

        Args:
            packages: List of PackageMetadata objects from registry scan
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Clear existing installed flags
        cursor.execute("UPDATE packages SET is_installed = 0")
        print("[MetadataCache] Cleared existing installed flags")

        # Insert or update packages
        for pkg in packages:
            # Try to find existing package in cache by ID and manager
            cursor.execute("""
                SELECT id FROM packages
                WHERE package_id = ? AND manager = ?
            """, (pkg.package_id, pkg.manager.value))

            existing = cursor.fetchone()

            if existing:
                # Update existing package with installed state
                cursor.execute("""
                    UPDATE packages SET
                        is_installed = 1,
                        installed_version = ?,
                        install_date = ?,
                        install_source = ?,
                        install_location = ?
                    WHERE package_id = ? AND manager = ?
                """, (pkg.installed_version, pkg.install_date, pkg.install_source,
                      pkg.install_location, pkg.package_id, pkg.manager.value))
            else:
                # Insert new package (not in available repos - manual install)
                cursor.execute("""
                    INSERT INTO packages (
                        package_id, name, version, manager, description,
                        author, publisher, homepage, license,
                        extra_metadata, search_tokens, tags, cache_timestamp,
                        is_installed, installed_version, install_date,
                        install_source, install_location
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """, (
                    pkg.package_id, pkg.name, pkg.version, pkg.manager.value,
                    pkg.description or "", pkg.author or "", pkg.publisher or "",
                    pkg.homepage or "", pkg.license or "", pkg.extra_metadata or "",
                    pkg.search_tokens or "", ','.join(pkg.tags) if pkg.tags else "",
                    int(datetime.now().timestamp()),
                    pkg.installed_version, pkg.install_date,
                    pkg.install_source, pkg.install_location
                ))

        conn.commit()
        conn.close()

    def _row_to_package(self, row: sqlite3.Row) -> UniversalPackageMetadata:
        """
        Convert database row to UniversalPackageMetadata.

        Args:
            row: SQLite row

        Returns:
            UniversalPackageMetadata object
        """
        return UniversalPackageMetadata(
            package_id=row['package_id'],
            name=row['name'],
            version=row['version'],
            manager=PackageManager(row['manager']),
            description=row['description'],
            author=row['author'],
            publisher=row['publisher'],
            homepage=row['homepage'],
            license=row['license'],
            extra_metadata=row['extra_metadata'],
            search_tokens=row['search_tokens'],
            tags=row['tags'],
            cache_timestamp=datetime.fromtimestamp(row['cache_timestamp']) if row['cache_timestamp'] else None,
            is_installed=bool(row['is_installed'])
        )
