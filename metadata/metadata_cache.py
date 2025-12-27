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
            UNIQUE(package_id, manager)
        )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_manager ON packages(manager)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_installed ON packages(is_installed)")
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

    def register_provider(self, provider: MetadataProvider):
        """
        Register a package manager provider.

        Args:
            provider: MetadataProvider instance
        """
        self.providers.append(provider)
        print(f"[MetadataCache] Registered provider: {provider.get_manager_name()}")

    def refresh_cache(self, manager: Optional[str] = None, force: bool = False):
        """
        Refresh metadata cache from providers.

        Args:
            manager: Specific manager to refresh (None = all)
            force: Force refresh even if cache is fresh
        """
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

        # Build WHERE clause for manager filter
        manager_filter = ""
        params = [query]

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
