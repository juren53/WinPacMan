"""
Background synchronization service for package metadata.

Orchestrates periodic syncing of package metadata from various sources
into the local SQLite cache.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


class BackgroundSyncService:
    """
    Manages background synchronization of package metadata.

    Responsibilities:
    - Track sync status for each provider
    - Determine when sync is needed
    - Orchestrate sync operations
    - Report sync progress and errors
    """

    def __init__(self, cache_service):
        """
        Initialize the sync service.

        Args:
            cache_service: MetadataCacheService instance
        """
        self.cache = cache_service
        self.providers = {}
        self._init_sync_tracking()

    def _init_sync_tracking(self):
        """Initialize the sync tracking table in the database."""
        conn = sqlite3.connect(self.cache.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                provider TEXT PRIMARY KEY,
                last_sync_time DATETIME,
                last_sync_sha TEXT,
                package_count INTEGER DEFAULT 0,
                sync_status TEXT DEFAULT 'never',
                error_message TEXT,
                next_sync_time DATETIME
            )
        """)

        conn.commit()
        conn.close()

    def register_provider(self, provider):
        """
        Register a provider for background syncing.

        Args:
            provider: MetadataProvider instance
        """
        manager_name = provider.get_manager_name()
        self.providers[manager_name] = provider
        print(f"[BackgroundSync] Registered provider: {manager_name}")

    def needs_sync(self, manager_name: str, max_age_hours: int = 24) -> bool:
        """
        Check if a provider needs syncing.

        Args:
            manager_name: Provider identifier
            max_age_hours: Maximum age in hours before sync is needed

        Returns:
            True if sync is needed
        """
        conn = sqlite3.connect(self.cache.cache_db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT last_sync_time, sync_status
            FROM sync_metadata
            WHERE provider = ?
        """, (manager_name,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            # Never synced
            return True

        last_sync_time, sync_status = row

        if sync_status == 'never' or not last_sync_time:
            return True

        # Check if last sync is older than max_age
        try:
            last_sync = datetime.fromisoformat(last_sync_time)
            age = datetime.now() - last_sync
            return age > timedelta(hours=max_age_hours)
        except (ValueError, TypeError):
            return True

    def sync_provider(self, manager_name: str, progress_callback=None) -> Dict[str, Any]:
        """
        Synchronize a specific provider.

        Args:
            manager_name: Provider identifier
            progress_callback: Optional callback(current, total, message)

        Returns:
            Sync result dictionary with status, package_count, error
        """
        provider = self.providers.get(manager_name)

        if not provider:
            return {
                'status': 'error',
                'error': f'Provider {manager_name} not registered'
            }

        print(f"[BackgroundSync] Starting sync for {manager_name}...")

        try:
            # Mark sync as in progress
            self._update_sync_status(manager_name, 'in_progress', None)

            # Fetch packages from provider
            if hasattr(provider, 'fetch_all_packages'):
                packages = list(provider.fetch_all_packages(progress_callback))
            else:
                # Fallback to get_available_packages
                packages = list(provider.get_available_packages())

            if not packages:
                self._update_sync_status(
                    manager_name,
                    'failed',
                    'No packages fetched'
                )
                return {
                    'status': 'failed',
                    'error': 'No packages fetched',
                    'package_count': 0
                }

            # Bulk update cache
            print(f"[BackgroundSync] Caching {len(packages)} packages...")
            self.cache.refresh_cache(manager_name, packages)

            # Update sync status
            self._update_sync_status(
                manager_name,
                'success',
                None,
                package_count=len(packages)
            )

            print(f"[BackgroundSync] Sync complete for {manager_name}: {len(packages)} packages")

            return {
                'status': 'success',
                'package_count': len(packages),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = str(e)
            print(f"[BackgroundSync] Sync failed for {manager_name}: {error_msg}")

            self._update_sync_status(manager_name, 'failed', error_msg)

            return {
                'status': 'error',
                'error': error_msg,
                'package_count': 0
            }

    def _update_sync_status(
        self,
        manager_name: str,
        status: str,
        error_message: Optional[str],
        package_count: Optional[int] = None
    ):
        """Update sync status in the database."""
        conn = sqlite3.connect(self.cache.cache_db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        if package_count is not None:
            cursor.execute("""
                INSERT OR REPLACE INTO sync_metadata
                (provider, last_sync_time, sync_status, error_message, package_count, next_sync_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (manager_name, now, status, error_message, package_count, now))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO sync_metadata
                (provider, sync_status, error_message)
                VALUES (?, ?, ?)
            """, (manager_name, status, error_message))

        conn.commit()
        conn.close()

    def get_sync_status(self, manager_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get sync status for one or all providers.

        Args:
            manager_name: Specific provider or None for all

        Returns:
            Dictionary with sync status information
        """
        conn = sqlite3.connect(self.cache.cache_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if manager_name:
            cursor.execute("""
                SELECT * FROM sync_metadata WHERE provider = ?
            """, (manager_name,))
            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return {'provider': manager_name, 'sync_status': 'never'}

        else:
            cursor.execute("SELECT * FROM sync_metadata")
            rows = cursor.fetchall()
            conn.close()

            return {row['provider']: dict(row) for row in rows}

    def sync_all(self, progress_callback=None) -> Dict[str, Any]:
        """
        Sync all registered providers.

        Args:
            progress_callback: Optional callback(provider, current, total, message)

        Returns:
            Dictionary with results for each provider
        """
        results = {}

        for manager_name in self.providers:
            print(f"\n[BackgroundSync] Syncing {manager_name}...")

            def provider_progress(current, total, message):
                if progress_callback:
                    progress_callback(manager_name, current, total, message)

            result = self.sync_provider(manager_name, provider_progress)
            results[manager_name] = result

        return results
