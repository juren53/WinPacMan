"""
NPM Registry API fetcher.

Fetches package metadata from the NPM registry using the NPM Registry API.
NPM has millions of packages, so we don't fetch all - we use search and individual lookups.
"""

import requests
from typing import Optional, List, Dict, Any


class NpmFetcher:
    """
    Fetches package metadata from NPM Registry.

    API Documentation:
    - Registry API: https://registry.npmjs.org/<package-name>
    - Search API: https://registry.npmjs.org/-/v1/search?text=<query>
    - Protocol: JSON-based REST API
    - Note: NPM has ~2-3 million packages - too many to fetch all at once
    """

    REGISTRY_BASE = "https://registry.npmjs.org"
    SEARCH_ENDPOINT = f"{REGISTRY_BASE}/-/v1/search"

    def __init__(self, timeout: int = 30):
        """
        Initialize fetcher.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WinPacMan/0.5.3c (Metadata Sync)',
            'Accept': 'application/json'
        })

    def search_packages(self, query: str, size: int = 20) -> List[Dict[str, Any]]:
        """
        Search for packages on NPM.

        Args:
            query: Search query string
            size: Maximum number of results to return (default: 20)

        Returns:
            List of package metadata dictionaries

        Example:
            >>> fetcher = NpmFetcher()
            >>> results = fetcher.search_packages('react', size=10)
            >>> for pkg in results:
            ...     print(pkg['name'], pkg['version'])
        """
        print(f"[NpmFetcher] Searching NPM for '{query}'...")

        try:
            params = {
                'text': query,
                'size': size
            }

            response = self.session.get(
                self.SEARCH_ENDPOINT,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            objects = data.get('objects', [])

            packages = []
            for obj in objects:
                pkg = obj.get('package', {})
                if pkg:
                    packages.append(self._normalize_search_result(pkg))

            print(f"[NpmFetcher] Found {len(packages)} packages")
            return packages

        except requests.exceptions.RequestException as e:
            print(f"[NpmFetcher] HTTP error during search: {e}")
            return []
        except Exception as e:
            print(f"[NpmFetcher] Error during search: {e}")
            return []

    def get_package_details(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific package.

        Args:
            package_name: Package name (e.g., 'react', 'express')

        Returns:
            Package metadata dictionary or None if not found

        Example:
            >>> fetcher = NpmFetcher()
            >>> pkg = fetcher.get_package_details('react')
            >>> print(pkg['description'])
            'React is a JavaScript library for building user interfaces.'
        """
        print(f"[NpmFetcher] Fetching details for '{package_name}'...")

        try:
            url = f"{self.REGISTRY_BASE}/{package_name}"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return self._normalize_package_details(data)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"[NpmFetcher] Package '{package_name}' not found")
            else:
                print(f"[NpmFetcher] HTTP error fetching '{package_name}': {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[NpmFetcher] Network error fetching '{package_name}': {e}")
            return None
        except Exception as e:
            print(f"[NpmFetcher] Error fetching '{package_name}': {e}")
            return None

    def _normalize_search_result(self, pkg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize search result to common format.

        Args:
            pkg: Raw package data from search API

        Returns:
            Normalized package metadata dictionary
        """
        # Extract maintainers/author
        maintainers = pkg.get('maintainers', [])
        author_name = ''
        if maintainers and len(maintainers) > 0:
            author_name = maintainers[0].get('username', '')

        # Extract author from package metadata if available
        author_obj = pkg.get('author')
        if author_obj and isinstance(author_obj, dict):
            author_name = author_obj.get('name', author_name)
        elif author_obj and isinstance(author_obj, str):
            author_name = author_obj

        # Extract links
        links = pkg.get('links', {})
        homepage = links.get('homepage') or links.get('repository') or links.get('npm', '')

        # Extract keywords/tags
        keywords = pkg.get('keywords', [])
        if isinstance(keywords, list):
            keywords = [str(k) for k in keywords]
        else:
            keywords = []

        return {
            'package_id': pkg.get('name', ''),
            'name': pkg.get('name', ''),
            'version': pkg.get('version', ''),
            'description': pkg.get('description', ''),
            'author': author_name,
            'publisher': pkg.get('publisher', {}).get('username', author_name),
            'homepage': homepage,
            'license': self._extract_license(pkg.get('license')),
            'tags': keywords,
            'download_count': 0,  # Not available in search results
            'last_updated': pkg.get('date', ''),
        }

    def _normalize_package_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize full package details to common format.

        Args:
            data: Raw package data from registry API

        Returns:
            Normalized package metadata dictionary
        """
        # Get latest version info
        latest_version = data.get('dist-tags', {}).get('latest', '')
        versions = data.get('versions', {})
        latest_data = versions.get(latest_version, {})

        # Extract author
        author_obj = latest_data.get('author') or data.get('author')
        author_name = ''
        if author_obj:
            if isinstance(author_obj, dict):
                author_name = author_obj.get('name', '')
            elif isinstance(author_obj, str):
                author_name = author_obj

        # Extract maintainers if no author
        if not author_name:
            maintainers = data.get('maintainers', [])
            if maintainers and len(maintainers) > 0:
                author_name = maintainers[0].get('name', '')

        # Extract homepage
        homepage = (
            latest_data.get('homepage') or
            data.get('homepage') or
            (data.get('repository', {}).get('url') if isinstance(data.get('repository'), dict) else data.get('repository')) or
            ''
        )

        # Extract keywords/tags
        keywords = latest_data.get('keywords') or data.get('keywords') or []
        if isinstance(keywords, list):
            keywords = [str(k) for k in keywords]
        else:
            keywords = []

        # Extract description
        description = latest_data.get('description') or data.get('description') or ''

        return {
            'package_id': data.get('name', ''),
            'name': data.get('name', ''),
            'version': latest_version,
            'description': description,
            'author': author_name,
            'publisher': author_name,
            'homepage': homepage,
            'license': self._extract_license(latest_data.get('license') or data.get('license')),
            'tags': keywords,
            'download_count': 0,  # Not easily available in package details
            'last_updated': data.get('time', {}).get('modified', ''),
        }

    def _extract_license(self, license_data: Any) -> str:
        """
        Extract license string from various formats.

        Args:
            license_data: License data (can be string, dict, or other format)

        Returns:
            License identifier string
        """
        if not license_data:
            return ''

        if isinstance(license_data, str):
            return license_data
        elif isinstance(license_data, dict):
            return license_data.get('type', '')
        elif isinstance(license_data, list):
            # Handle array of licenses
            if len(license_data) > 0:
                first = license_data[0]
                if isinstance(first, dict):
                    return first.get('type', '')
                return str(first)

        return str(license_data)
