"""
Base provider for package metadata.

Defines the abstract interface that all package manager metadata providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Iterator, Optional
from core.models import UniversalPackageMetadata


class MetadataProvider(ABC):
    """
    Abstract base class for package manager metadata providers.

    Each package manager (WinGet, Chocolatey, Pip, etc.) implements this interface
    to provide access to its repository metadata in a unified format.
    """

    @abstractmethod
    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Yield all available packages from this manager's repository.

        Returns:
            Iterator of UniversalPackageMetadata objects

        Note:
            For large repositories (Pip, NPM), this may be a no-op and search
            should be used instead to avoid fetching millions of packages.
        """
        pass

    @abstractmethod
    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific package.

        Args:
            package_id: Unique package identifier

        Returns:
            UniversalPackageMetadata object or None if not found
        """
        pass

    @abstractmethod
    def is_cache_stale(self) -> bool:
        """
        Check if the local cache needs refreshing.

        Returns:
            True if cache should be updated, False otherwise
        """
        pass

    @abstractmethod
    def get_manager_name(self) -> str:
        """
        Get the package manager identifier.

        Returns:
            Manager name (e.g., 'winget', 'chocolatey', 'pip')
        """
        pass

    def search_packages(self, query: str) -> Iterator[UniversalPackageMetadata]:
        """
        Search for packages matching query.

        Default implementation uses get_available_packages() and filters.
        Providers can override for more efficient search.

        Args:
            query: Search query string

        Returns:
            Iterator of matching UniversalPackageMetadata objects
        """
        query_lower = query.lower()

        for package in self.get_available_packages():
            if (query_lower in package.name.lower() or
                query_lower in package.package_id.lower() or
                (package.description and query_lower in package.description.lower())):
                yield package
