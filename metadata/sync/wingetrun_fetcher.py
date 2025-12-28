"""
WinGet.run API fetcher for fast initial repository sync.

Uses the winget.run REST API to quickly populate the cache with
the full WinGet repository. This is much faster than GitHub API
for initial sync (minutes vs hours).
"""

import requests
from typing import Iterator, Dict, Any, Optional
from datetime import datetime


class WinGetRunFetcher:
    """
    Fetches WinGet package metadata from winget.run API.

    This is a third-party service that maintains a complete index
    of the WinGet repository. Use for initial sync, then switch
    to GitHub for updates to avoid dependency on third-party service.
    """

    API_BASE = "https://api.winget.run/v2"
    PACKAGES_ENDPOINT = f"{API_BASE}/packages"

    def __init__(self):
        """Initialize the fetcher."""
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'WinPacMan/0.3.2'

    def fetch_package_list(self) -> list[str]:
        """
        Fetch list of all package IDs.

        Returns:
            List of package IDs
        """
        print("[WinGetRun] Fetching package list...")

        try:
            response = self.session.get(self.PACKAGES_ENDPOINT, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # The response is a list of package objects
                package_ids = [pkg.get('Id', pkg.get('PackageIdentifier', ''))
                              for pkg in data if isinstance(pkg, dict)]

                print(f"[WinGetRun] Found {len(package_ids)} packages")
                return package_ids

            else:
                print(f"[WinGetRun] Request failed: {response.status_code}")
                return []

        except requests.RequestException as e:
            print(f"[WinGetRun] Request error: {e}")
            return []

    def fetch_package_details(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed metadata for a specific package.

        Args:
            package_id: Package identifier

        Returns:
            Package metadata dictionary or None
        """
        url = f"{self.PACKAGES_ENDPOINT}/{package_id}"

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return None

        except requests.RequestException:
            return None

    def fetch_all_packages(self, progress_callback=None) -> Iterator[Dict[str, Any]]:
        """
        Fetch all packages with metadata, handling pagination.
        Args:
            progress_callback: Optional callback(current, total, message)
        Yields:
            Package metadata dictionaries
        """
        print("[WinGetRun] Fetching all packages...")
        page = 0
        take = 100  # Number of items per page
        total_fetched = 0
        total_packages = -1  # Unknown at first

        while True:
            try:
                # Fetch a page of packages
                url = f"{self.PACKAGES_ENDPOINT}?page={page}&take={take}"
                response = self.session.get(url, timeout=60)

                if response.status_code != 200:
                    print(f"[WinGetRun] Request failed: {response.status_code}")
                    break

                data = response.json()

                if total_packages == -1:
                    total_packages = data.get('Total', 0)
                if total_packages > 0:
                    print(f"[WinGetRun] Found {total_packages} packages in total.")


                # Response format: {"Packages": [...], "Total": ...}
                if isinstance(data, dict) and 'Packages' in data:
                    packages = data['Packages']
                else:
                    print(f"[WinGetRun] Unexpected response format: {type(data)}")
                    break

                if not packages:  # No more packages
                    break

                if total_packages > 0 and progress_callback:
                    progress_callback(total_fetched, total_packages, f"Fetched {total_fetched}/{total_packages} packages")

                for pkg in packages:
                    # Parse package data
                    parsed = self.parse_package_data(pkg)
                    if parsed:
                        yield parsed

                total_fetched += len(packages)
                page += 1

            except requests.RequestException as e:
                print(f"[WinGetRun] Error fetching packages: {e}")
                break

    def parse_package_data(self, pkg_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse winget.run package data into our metadata format.

        Args:
            pkg_data: Raw package data from API

        Returns:
            Metadata dictionary compatible with UniversalPackageMetadata
        """
        try:
            # Get the latest version info
            latest = pkg_data.get('Latest', {})

            package_id = pkg_data.get('Id', pkg_data.get('PackageIdentifier', ''))
            name = pkg_data.get('Name', pkg_data.get('PackageName', package_id))

            # Version can be in different places
            version = (latest.get('PackageVersion') or
                      pkg_data.get('Version') or
                      pkg_data.get('LatestVersion') or
                      'Unknown')

            publisher = (latest.get('Publisher') or
                        pkg_data.get('Publisher') or
                        '')

            description = (latest.get('ShortDescription') or
                          latest.get('Description') or
                          pkg_data.get('Description') or
                          '')

            homepage = (latest.get('PackageUrl') or
                       latest.get('Homepage') or
                       pkg_data.get('Homepage') or
                       '')

            license_info = latest.get('License', '')

            # Tags
            tags = latest.get('Tags', [])
            if isinstance(tags, list):
                tags_str = ','.join(tags)
            else:
                tags_str = str(tags) if tags else ''

            return {
                'package_id': package_id,
                'name': name,
                'version': version,
                'publisher': publisher,
                'description': description,
                'homepage': homepage,
                'license': license_info,
                'tags': tags_str,
                'fetched_time': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[WinGetRun] Error parsing package data: {e}")
            return None
