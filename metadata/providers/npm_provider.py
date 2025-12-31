"""
NPM metadata provider.

Provides package metadata from NPM Registry for the unified metadata cache system.
"""

from typing import Iterator, Optional
from datetime import datetime, timedelta

from core.models import UniversalPackageMetadata, PackageManager
from .base import MetadataProvider


class NpmProvider(MetadataProvider):
    """
    Metadata provider for NPM Registry.

    Data Sources:
    - Primary: NPM Registry API (JSON-based REST API)
    - Registry: https://registry.npmjs.org/<package-name>
    - Search: https://registry.npmjs.org/-/v1/search

    Note: NPM has ~2-3 million packages. We don't fetch all packages at once.
    Instead, we rely on search and individual package lookups.
    """

    def __init__(self, cache_duration_hours: int = 24):
        """
        Initialize NPM provider.

        Args:
            cache_duration_hours: Hours before cache is considered stale
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.last_sync_time = None

    def get_manager_name(self) -> str:
        """Get the package manager identifier."""
        return 'npm'

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Get available packages from NPM.

        Note: NPM has millions of packages, so we don't fetch all at once.
        Use search_packages() instead for finding packages.

        Yields:
            Nothing - returns empty iterator
        """
        print("[NpmProvider] NPM has millions of packages.")
        print("[NpmProvider] Use search_packages() to find specific packages.")
        print("[NpmProvider] Use fetch_popular_packages() to cache top packages.")
        return iter([])

    def search_packages(self, query: str, max_results: int = 20) -> Iterator[UniversalPackageMetadata]:
        """
        Search for packages on NPM.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Yields:
            UniversalPackageMetadata objects for matching packages
        """
        from metadata.sync.npm_fetcher import NpmFetcher

        print(f"[NpmProvider] Searching NPM for '{query}'...")

        fetcher = NpmFetcher()
        results = fetcher.search_packages(query, size=max_results)

        for pkg_data in results:
            try:
                metadata = self._convert_to_metadata(pkg_data)
                if metadata:
                    yield metadata
            except Exception as e:
                print(f"[NpmProvider] Error converting package {pkg_data.get('package_id', 'unknown')}: {e}")
                continue

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific package.

        Args:
            package_id: Package identifier (NPM package name)

        Returns:
            Package metadata or None if not found
        """
        from metadata.sync.npm_fetcher import NpmFetcher

        print(f"[NpmProvider] Getting details for '{package_id}'...")

        fetcher = NpmFetcher()
        pkg_data = fetcher.get_package_details(package_id)

        if pkg_data:
            return self._convert_to_metadata(pkg_data)

        return None

    def fetch_popular_packages(self, progress_callback=None, limit: int = 1000) -> Iterator[UniversalPackageMetadata]:
        """
        Fetch popular/trending packages from NPM for cache.

        This is an alternative to fetching ALL packages (which would be millions).
        We can search for popular packages or use NPM's trending/popular endpoints.

        Args:
            progress_callback: Optional callback(current, total, message)
            limit: Maximum number of packages to fetch

        Yields:
            UniversalPackageMetadata objects
        """
        from metadata.sync.npm_fetcher import NpmFetcher

        print(f"[NpmProvider] Fetching top {limit} popular NPM packages...")

        fetcher = NpmFetcher()

        # Strategy: Search for common keywords to get popular packages
        # This is a workaround since NPM doesn't have a direct "popular packages" API
        popular_searches = [
            'framework', 'library', 'react', 'vue', 'angular', 'express',
            'typescript', 'webpack', 'babel', 'eslint', 'jest', 'node',
            'build', 'cli', 'util', 'tool', 'test', 'http', 'server'
        ]

        fetched_count = 0
        seen_packages = set()

        for search_term in popular_searches:
            if fetched_count >= limit:
                break

            results = fetcher.search_packages(search_term, size=50)

            for pkg_data in results:
                if fetched_count >= limit:
                    break

                package_id = pkg_data.get('package_id', '')
                if package_id in seen_packages:
                    continue

                seen_packages.add(package_id)

                try:
                    metadata = self._convert_to_metadata(pkg_data)
                    if metadata:
                        yield metadata
                        fetched_count += 1

                        if progress_callback and fetched_count % 10 == 0:
                            progress_callback(fetched_count, limit,
                                            f"Fetched {fetched_count}/{limit} packages")

                except Exception as e:
                    print(f"[NpmProvider] Error converting package {package_id}: {e}")
                    continue

        print(f"[NpmProvider] Fetch complete. Total packages: {fetched_count}")
        self.last_sync_time = datetime.now()

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

    def _convert_to_metadata(self, pkg_data: dict) -> Optional[UniversalPackageMetadata]:
        """
        Convert NPM package data to UniversalPackageMetadata.

        Args:
            pkg_data: Package data dictionary from fetcher

        Returns:
            UniversalPackageMetadata object or None
        """
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
            author = pkg_data.get('author', '')

            search_tokens = f"{package_id.lower()} {name.lower()} {author.lower()}"

            # Create metadata object
            metadata = UniversalPackageMetadata(
                package_id=package_id,
                name=name,
                version=pkg_data.get('version', ''),
                manager=PackageManager.NPM,
                description=pkg_data.get('description'),
                author=author,
                publisher=pkg_data.get('publisher', author),
                homepage=pkg_data.get('homepage'),
                license=pkg_data.get('license'),
                tags=tags_str,
                search_tokens=search_tokens,
                cache_timestamp=datetime.now(),
                is_installed=False
            )

            return metadata

        except KeyError as e:
            print(f"[NpmProvider] Missing required field in package data: {e}")
            return None
        except Exception as e:
            print(f"[NpmProvider] Error converting package data: {e}")
            return None

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
            'data_source': 'NPM Registry API',
            'registry_url': 'https://registry.npmjs.org',
            'note': 'NPM has millions of packages - use search or fetch popular packages'
        }
