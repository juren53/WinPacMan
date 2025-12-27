"""
Chocolatey metadata provider.

Provides package metadata from Chocolatey Community Repository
for the unified metadata cache system.
"""

import os
from typing import Iterator, Optional
from datetime import datetime, timedelta
from pathlib import Path

from core.models import UniversalPackageMetadata, PackageManager
from .base import MetadataProvider


class ChocolateyProvider(MetadataProvider):
    """
    Metadata provider for Chocolatey Community Repository.

    Data Sources:
    - Primary: Chocolatey OData API (NuGet v2)
    - Endpoint: https://community.chocolatey.org/api/v2/
    - Limit: 10,000 packages (CCR API restriction)
    """

    def __init__(self, cache_duration_hours: int = 24):
        """
        Initialize Chocolatey provider.

        Args:
            cache_duration_hours: Hours before cache is considered stale
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.last_sync_time = None

    def get_manager_name(self) -> str:
        """Get the package manager identifier."""
        return 'chocolatey'

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Get available packages from Chocolatey.

        Note: This method is primarily for initial testing.
        For production sync, use fetch_all_packages() instead.

        Yields:
            Package metadata objects
        """
        # For Chocolatey, we don't have a local database like WinGet
        # So this method will yield nothing - use fetch_all_packages() instead
        print("[ChocolateyProvider] No local database available.")
        print("[ChocolateyProvider] Use fetch_all_packages() to sync from API.")
        return iter([])

    def fetch_all_packages(self, progress_callback=None) -> Iterator[UniversalPackageMetadata]:
        """
        Fetch all packages from Chocolatey Community Repository.

        Args:
            progress_callback: Optional callback(current, total, message)

        Yields:
            UniversalPackageMetadata objects
        """
        from metadata.sync.chocolatey_odata_fetcher import ChocolateyODataFetcher

        print("[ChocolateyProvider] Fetching from Chocolatey Community Repository API...")

        fetcher = ChocolateyODataFetcher()

        for pkg_data in fetcher.fetch_all_packages(progress_callback):
            try:
                # Convert tags list to comma-separated string
                tags = pkg_data.get('tags', [])
                if isinstance(tags, list):
                    tags_str = ','.join(str(t) for t in tags)
                else:
                    tags_str = str(tags) if tags else ''

                # Build search tokens
                package_id = pkg_data['package_id']
                name = pkg_data.get('name', package_id)
                authors = pkg_data.get('authors', '')

                search_tokens = f"{package_id.lower()} {name.lower()} {authors.lower()}"

                # Create metadata object
                metadata = UniversalPackageMetadata(
                    package_id=package_id,
                    name=name,
                    version=pkg_data.get('version', ''),
                    manager=PackageManager.CHOCOLATEY,
                    description=pkg_data.get('description'),
                    author=authors,
                    publisher=pkg_data.get('publisher', authors),
                    homepage=pkg_data.get('homepage'),
                    license=pkg_data.get('license'),
                    tags=tags_str,
                    search_tokens=search_tokens,
                    cache_timestamp=datetime.now(),
                    is_installed=False
                )

                yield metadata

            except Exception as e:
                print(f"[ChocolateyProvider] Error converting package {pkg_data.get('package_id', 'unknown')}: {e}")
                continue

        # Update last sync time
        self.last_sync_time = datetime.now()

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific package.

        Args:
            package_id: Package identifier

        Returns:
            Package metadata or None if not found
        """
        # For Chocolatey, we could query the API directly for one package
        # But for now, we'll rely on the cache
        print(f"[ChocolateyProvider] Package details for '{package_id}' - check cache")
        return None

    def is_cache_stale(self) -> bool:
        """
        Check if cache needs refresh.

        Returns:
            True if cache is stale or has never been synced
        """
        if self.last_sync_time is None:
            return True

        age = datetime.now() - self.last_sync_time
        return age > self.cache_duration

    def get_sync_metadata(self) -> dict:
        """
        Get provider sync metadata.

        Returns:
            Dictionary with sync information
        """
        return {
            'provider': self.get_manager_name(),
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'cache_duration_hours': self.cache_duration.total_seconds() / 3600,
            'is_stale': self.is_cache_stale(),
            'data_source': 'Chocolatey Community Repository OData API',
            'api_endpoint': 'https://community.chocolatey.org/api/v2/',
            'max_packages': 10000
        }
