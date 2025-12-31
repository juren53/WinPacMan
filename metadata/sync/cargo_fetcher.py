"""
Cargo Sparse Index fetcher.

Fetches package metadata from crates.io using the new Sparse Index protocol.
The Sparse Index is much faster than cloning the entire Git repository.
"""

import requests
import json
from typing import Optional, List, Dict, Any


class CargoFetcher:
    """
    Fetches package metadata from crates.io Sparse Index.

    API Documentation:
    - Sparse Index: https://index.crates.io/
    - Format: Newline-delimited JSON (NDJSON)
    - URL Structure: https://index.crates.io/<prefix>/<crate_name>
    - crates.io API: https://crates.io/api/v1/crates/<crate_name>

    Prefix Calculation:
    - 1 char: 1/<name>
    - 2 chars: 2/<name>
    - 3 chars: 3/<first-char>/<name>
    - 4+ chars: <first-2-chars>/<next-2-chars>/<name>

    Note: crates.io has ~140,000 crates, which is manageable but still large.
    We'll use a similar strategy to NPM: fetch popular crates via search.
    """

    SPARSE_INDEX_BASE = "https://index.crates.io"
    CRATES_IO_API = "https://crates.io/api/v1"

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

    def _calculate_prefix(self, crate_name: str) -> str:
        """
        Calculate the sparse index prefix for a crate name.

        Args:
            crate_name: The crate name

        Returns:
            Prefix path for the crate

        Examples:
            >>> _calculate_prefix('a')
            '1/a'
            >>> _calculate_prefix('ab')
            '2/ab'
            >>> _calculate_prefix('abc')
            '3/a/abc'
            >>> _calculate_prefix('serde')
            'se/rd/serde'
        """
        name_lower = crate_name.lower()
        length = len(name_lower)

        if length == 1:
            return f"1/{name_lower}"
        elif length == 2:
            return f"2/{name_lower}"
        elif length == 3:
            return f"3/{name_lower[0]}/{name_lower}"
        else:
            return f"{name_lower[:2]}/{name_lower[2:4]}/{name_lower}"

    def get_crate_details(self, crate_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed metadata for a specific crate using sparse index.

        Args:
            crate_name: Crate name (e.g., 'serde', 'tokio')

        Returns:
            Crate metadata dictionary or None if not found

        Example:
            >>> fetcher = CargoFetcher()
            >>> crate = fetcher.get_crate_details('serde')
            >>> print(crate['name'], crate['version'])
            'serde' '1.0.210'
        """
        print(f"[CargoFetcher] Fetching details for '{crate_name}'...")

        try:
            prefix = self._calculate_prefix(crate_name)
            url = f"{self.SPARSE_INDEX_BASE}/{prefix}"

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse newline-delimited JSON
            # Each line is a separate version of the crate
            # We want the latest version (last line typically, but we'll find max version)
            lines = response.text.strip().split('\n')
            if not lines:
                print(f"[CargoFetcher] No versions found for '{crate_name}'")
                return None

            # Parse all versions and find the latest
            latest_version = None
            latest_data = None

            for line in lines:
                if not line.strip():
                    continue

                try:
                    data = json.loads(line)
                    # Check if this is not yanked (removed)
                    if data.get('yanked', False):
                        continue

                    version = data.get('vers', '')
                    if not latest_version or self._compare_versions(version, latest_version) > 0:
                        latest_version = version
                        latest_data = data

                except json.JSONDecodeError:
                    continue

            if latest_data:
                return self._normalize_crate_details(latest_data)

            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"[CargoFetcher] Crate '{crate_name}' not found")
            else:
                print(f"[CargoFetcher] HTTP error fetching '{crate_name}': {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[CargoFetcher] Network error fetching '{crate_name}': {e}")
            return None
        except Exception as e:
            print(f"[CargoFetcher] Error fetching '{crate_name}': {e}")
            return None

    def search_crates(self, query: str, per_page: int = 20) -> List[Dict[str, Any]]:
        """
        Search for crates on crates.io.

        Args:
            query: Search query string
            per_page: Number of results per page (max 100)

        Returns:
            List of crate metadata dictionaries

        Example:
            >>> fetcher = CargoFetcher()
            >>> results = fetcher.search_crates('serde', per_page=10)
            >>> for crate in results:
            ...     print(crate['name'], crate['version'])
        """
        print(f"[CargoFetcher] Searching crates.io for '{query}'...")

        try:
            url = f"{self.CRATES_IO_API}/crates"
            params = {
                'q': query,
                'per_page': min(per_page, 100)  # API max is 100
            }

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            crates = data.get('crates', [])

            print(f"[CargoFetcher] Found {len(crates)} crates")

            results = []
            for crate in crates:
                results.append(self._normalize_search_result(crate))

            return results

        except requests.exceptions.RequestException as e:
            print(f"[CargoFetcher] HTTP error during search: {e}")
            return []
        except Exception as e:
            print(f"[CargoFetcher] Error during search: {e}")
            return []

    def _normalize_search_result(self, crate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize search result to common format.

        Args:
            crate: Raw crate data from crates.io search API

        Returns:
            Normalized crate metadata dictionary
        """
        return {
            'package_id': crate.get('name', ''),
            'name': crate.get('name', ''),
            'version': crate.get('max_version', ''),
            'description': crate.get('description', ''),
            'author': '',  # Not in search results, need full API call
            'publisher': '',
            'homepage': crate.get('homepage', ''),
            'license': '',  # Not in search results
            'tags': crate.get('keywords', []),
            'download_count': crate.get('downloads', 0),
            'last_updated': crate.get('updated_at', ''),
        }

    def _normalize_crate_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize sparse index crate details to common format.

        Args:
            data: Raw crate data from sparse index

        Returns:
            Normalized crate metadata dictionary
        """
        # Extract authors (list)
        authors = data.get('authors', [])
        author_str = ', '.join(authors) if authors else ''

        # Extract features
        features = data.get('features', {})
        feature_names = list(features.keys())

        return {
            'package_id': data.get('name', ''),
            'name': data.get('name', ''),
            'version': data.get('vers', ''),
            'description': '',  # Not in sparse index, need full API
            'author': author_str,
            'publisher': author_str,
            'homepage': '',  # Not in sparse index
            'license': '',  # Not in sparse index
            'tags': feature_names,  # Use features as tags
            'download_count': 0,  # Not in sparse index
            'last_updated': '',
        }

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two semantic versions.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            Positive if v1 > v2, negative if v1 < v2, 0 if equal
        """
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]

            # Pad shorter version with zeros
            max_len = max(len(parts1), len(parts2))
            parts1 += [0] * (max_len - len(parts1))
            parts2 += [0] * (max_len - len(parts2))

            for p1, p2 in zip(parts1, parts2):
                if p1 > p2:
                    return 1
                elif p1 < p2:
                    return -1

            return 0

        except (ValueError, AttributeError):
            # Fallback to string comparison
            return (v1 > v2) - (v1 < v2)
