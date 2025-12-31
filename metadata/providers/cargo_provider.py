"""
Cargo metadata provider.

Provides package metadata from crates.io for the unified metadata cache system.
"""

from typing import Iterator, Optional
from datetime import datetime, timedelta

from core.models import UniversalPackageMetadata, PackageManager
from .base import MetadataProvider


class CargoProvider(MetadataProvider):
    """
    Metadata provider for crates.io (Cargo/Rust packages).

    Data Sources:
    - Primary: crates.io Sparse Index (https://index.crates.io/)
    - Search API: https://crates.io/api/v1/crates
    - Format: Newline-delimited JSON (NDJSON) for sparse index

    Note: crates.io has ~140,000 crates. We fetch popular crates via search.
    """

    def __init__(self, cache_duration_hours: int = 24):
        """
        Initialize Cargo provider.

        Args:
            cache_duration_hours: Hours before cache is considered stale
        """
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.last_sync_time = None

    def get_manager_name(self) -> str:
        """Get the package manager identifier."""
        return 'cargo'

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Get available packages from crates.io.

        Note: crates.io has ~140,000 crates. We don't fetch all at once.
        Use search_packages() instead for finding packages.

        Yields:
            Nothing - returns empty iterator
        """
        print("[CargoProvider] crates.io has ~140,000 crates.")
        print("[CargoProvider] Use search_packages() to find specific crates.")
        print("[CargoProvider] Use fetch_all_packages() to cache popular crates.")
        return iter([])

    def search_packages(self, query: str, max_results: int = 20) -> Iterator[UniversalPackageMetadata]:
        """
        Search for crates on crates.io.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Yields:
            UniversalPackageMetadata objects for matching crates
        """
        from metadata.sync.cargo_fetcher import CargoFetcher

        print(f"[CargoProvider] Searching crates.io for '{query}'...")

        fetcher = CargoFetcher()
        results = fetcher.search_crates(query, per_page=max_results)

        for crate_data in results:
            try:
                metadata = self._convert_to_metadata(crate_data)
                if metadata:
                    yield metadata
            except Exception as e:
                print(f"[CargoProvider] Error converting crate {crate_data.get('package_id', 'unknown')}: {e}")
                continue

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific crate.

        Args:
            package_id: Crate name

        Returns:
            Package metadata or None if not found
        """
        from metadata.sync.cargo_fetcher import CargoFetcher

        print(f"[CargoProvider] Getting details for '{package_id}'...")

        fetcher = CargoFetcher()
        crate_data = fetcher.get_crate_details(package_id)

        if crate_data:
            return self._convert_to_metadata(crate_data)

        return None

    def fetch_all_packages(self, progress_callback=None, limit: int = 1000) -> Iterator[UniversalPackageMetadata]:
        """
        Fetch popular crates from crates.io for cache.

        Note: crates.io has ~140,000 crates, so we don't fetch ALL packages.
        Instead, we fetch popular crates by searching for common keywords.
        This is called 'fetch_all_packages' to match the interface expected by
        the metadata cache refresh logic.

        Args:
            progress_callback: Optional callback(current, total, message)
            limit: Maximum number of packages to fetch

        Yields:
            UniversalPackageMetadata objects
        """
        from metadata.sync.cargo_fetcher import CargoFetcher

        print(f"[CargoProvider] Fetching top {limit} popular crates...")

        fetcher = CargoFetcher()

        # Strategy: Search for common Rust-related keywords to get popular crates
        popular_searches = [
            'serde', 'tokio', 'async', 'web', 'http', 'cli', 'parser', 'crypto',
            'database', 'logging', 'testing', 'serialization', 'networking', 'json',
            'api', 'framework', 'library', 'utility', 'tool', 'macros', 'derive',
            'error', 'config', 'time', 'random', 'collections'
        ]

        fetched_count = 0
        seen_crates = set()

        for search_term in popular_searches:
            if fetched_count >= limit:
                break

            results = fetcher.search_crates(search_term, per_page=50)

            for crate_data in results:
                if fetched_count >= limit:
                    break

                package_id = crate_data.get('package_id', '')
                if package_id in seen_crates:
                    continue

                seen_crates.add(package_id)

                try:
                    metadata = self._convert_to_metadata(crate_data)
                    if metadata:
                        yield metadata
                        fetched_count += 1

                        if progress_callback and fetched_count % 10 == 0:
                            progress_callback(fetched_count, limit,
                                            f"Fetched {fetched_count}/{limit} crates")

                except Exception as e:
                    print(f"[CargoProvider] Error converting crate {package_id}: {e}")
                    continue

        print(f"[CargoProvider] Fetch complete. Total crates: {fetched_count}")
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

    def _convert_to_metadata(self, crate_data: dict) -> Optional[UniversalPackageMetadata]:
        """
        Convert crate data to UniversalPackageMetadata.

        Args:
            crate_data: Crate data dictionary from fetcher

        Returns:
            UniversalPackageMetadata object or None
        """
        try:
            # Convert tags list to comma-separated string
            tags = crate_data.get('tags', [])
            if isinstance(tags, list):
                tags_str = ','.join(str(t) for t in tags)
            else:
                tags_str = str(tags) if tags else ''

            # Build search tokens
            package_id = crate_data['package_id']
            name = crate_data.get('name', package_id)
            author = crate_data.get('author', '')

            search_tokens = f"{package_id.lower()} {name.lower()} {author.lower()}"

            # Create metadata object
            metadata = UniversalPackageMetadata(
                package_id=package_id,
                name=name,
                version=crate_data.get('version', ''),
                manager=PackageManager.CARGO,
                description=crate_data.get('description'),
                author=author,
                publisher=crate_data.get('publisher', author),
                homepage=crate_data.get('homepage'),
                license=crate_data.get('license'),
                tags=tags_str,
                search_tokens=search_tokens,
                cache_timestamp=datetime.now(),
                is_installed=False
            )

            return metadata

        except KeyError as e:
            print(f"[CargoProvider] Missing required field in crate data: {e}")
            return None
        except Exception as e:
            print(f"[CargoProvider] Error converting crate data: {e}")
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
            'data_source': 'crates.io Sparse Index',
            'index_url': 'https://index.crates.io',
            'api_url': 'https://crates.io/api/v1',
            'note': 'crates.io has ~140,000 crates - use search or fetch popular crates'
        }
