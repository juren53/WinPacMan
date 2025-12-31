"""
Chocolatey Community Repository OData API fetcher.

Fetches package metadata from the Chocolatey Community Repository
using the NuGet v2 OData API protocol.
"""

import requests
import time
from typing import Iterator, Dict, Any, Optional
from xml.etree import ElementTree as ET


class ChocolateyODataFetcher:
    """
    Fetches package metadata from Chocolatey Community Repository.

    API Documentation:
    - https://docs.chocolatey.org/en-us/community-repository/api/
    - Endpoint: https://community.chocolatey.org/api/v2/
    - Protocol: NuGet v2 OData
    - Pagination: Uses skiptoken-based pagination to fetch ALL packages (10,676+)
    - No artificial limits - follows "next" links until complete
    """

    API_BASE = "https://community.chocolatey.org/api/v2"
    PACKAGES_ENDPOINT = f"{API_BASE}/Packages"

    # OData query parameters
    DEFAULT_PAGE_SIZE = 100
    # Note: No MAX_PACKAGES limit - we use skiptoken pagination to fetch all packages

    def __init__(self, timeout: int = 30):
        """
        Initialize fetcher.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WinPacMan/0.4.0 (Metadata Sync)',
            'Accept': 'application/atom+xml,application/xml'
        })

    def fetch_all_packages(self, progress_callback=None) -> Iterator[Dict[str, Any]]:
        """
        Fetch all packages from Chocolatey Community Repository.

        Args:
            progress_callback: Optional callback(current, total, message)

        Yields:
            Package metadata dictionaries

        Notes:
            - Uses skiptoken-based pagination to fetch ALL packages (10,676+)
            - Follows "next" links in XML response for seamless pagination
            - API automatically switches from $skip to $skiptoken after 10,000
            - Returns only latest version of each package
        """
        print("[ChocolateyFetcher] Starting fetch from Chocolatey Community Repository...")
        print(f"[ChocolateyFetcher] API: {self.PACKAGES_ENDPOINT}")
        print("[ChocolateyFetcher] Using skiptoken pagination to fetch all packages...")

        total_fetched = 0
        page_count = 0

        # Build initial URL with query parameters
        params = {
            '$filter': "IsLatestVersion eq true",
            '$orderby': 'Id'
        }

        # Construct initial URL
        current_url = self.PACKAGES_ENDPOINT + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])

        while current_url:
            page_count += 1

            try:
                print(f"[ChocolateyFetcher] Fetching page {page_count} ({total_fetched} packages so far)...")

                response = self.session.get(current_url, timeout=self.timeout)
                response.raise_for_status()

                # Parse Atom XML response
                packages = self._parse_atom_feed(response.text)

                if not packages:
                    print(f"[ChocolateyFetcher] No more packages found. Total: {total_fetched}")
                    break

                # Yield packages
                for pkg in packages:
                    yield pkg
                    total_fetched += 1

                    if progress_callback and total_fetched % 100 == 0:
                        progress_callback(total_fetched, total_fetched,
                                        f"Fetched {total_fetched} packages")

                # Extract next link from response
                next_url = self._extract_next_link(response.text)

                if next_url:
                    current_url = next_url
                else:
                    print(f"[ChocolateyFetcher] No next link found. End of data reached.")
                    break

                # Rate limiting - be respectful
                time.sleep(0.1)

            except requests.exceptions.RequestException as e:
                print(f"[ChocolateyFetcher] HTTP error at page {page_count}: {e}")
                # Stop on network errors
                break
            except Exception as e:
                print(f"[ChocolateyFetcher] Parse error at page {page_count}: {e}")
                import traceback
                traceback.print_exc()
                # Stop on parse errors
                break

        print(f"[ChocolateyFetcher] Fetch complete. Total packages: {total_fetched}, Pages: {page_count}")

    def _parse_atom_feed(self, xml_text: str) -> list[Dict[str, Any]]:
        """
        Parse Atom XML feed from NuGet v2 OData response.

        Args:
            xml_text: XML response text

        Returns:
            List of package metadata dictionaries
        """
        packages = []

        try:
            # Parse XML
            root = ET.fromstring(xml_text)

            # Namespaces used in Atom feed
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
                'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata'
            }

            # Find all entry elements
            entries = root.findall('atom:entry', ns)
            print(f"[ChocolateyFetcher] Found {len(entries)} entries in XML")

            for entry in entries:
                try:
                    pkg = self._parse_entry(entry, ns)
                    if pkg:
                        packages.append(pkg)
                    else:
                        print(f"[ChocolateyFetcher] _parse_entry returned None")
                except Exception as e:
                    # Skip malformed entries
                    print(f"[ChocolateyFetcher] Error parsing entry: {e}")
                    continue

        except ET.ParseError as e:
            print(f"[ChocolateyFetcher] XML parse error: {e}")
            return []

        return packages

    def _parse_entry(self, entry: ET.Element, ns: dict) -> Optional[Dict[str, Any]]:
        """
        Parse a single entry element from Atom feed.

        Args:
            entry: XML entry element
            ns: XML namespaces

        Returns:
            Package metadata dictionary or None
        """
        # Get package ID from entry title (NOT in properties)
        title_elem = entry.find('atom:title', ns)
        if title_elem is None or not title_elem.text:
            return None

        package_id = title_elem.text.strip()

        # Get properties element
        props = entry.find('m:properties', ns)
        if props is None:
            return None

        # Helper to get text from properties
        def get_text(name: str) -> str:
            elem = props.find(f'd:{name}', ns)
            return elem.text if elem is not None and elem.text else ''

        # Get tags and split into list
        tags_str = get_text('Tags')
        tags = [t.strip() for t in tags_str.split() if t.strip()] if tags_str else []

        return {
            'package_id': package_id,
            'name': get_text('Title') or package_id,
            'version': get_text('Version'),
            'description': get_text('Description'),
            'authors': '',  # Not available in Chocolatey feed
            'publisher': package_id.split('.')[0] if '.' in package_id else '',  # Extract from ID
            'homepage': get_text('ProjectUrl'),
            'license': get_text('LicenseUrl'),
            'tags': tags,
            'download_count': get_text('DownloadCount'),
            'is_prerelease': get_text('IsPrerelease') == 'true',
            'created': get_text('Created'),
            'last_updated': get_text('Published'),  # Use Published date
        }

    def _extract_next_link(self, xml_text: str) -> Optional[str]:
        """
        Extract the "next" link from Atom XML feed.

        Args:
            xml_text: XML response text

        Returns:
            Next page URL or None if no next link exists
        """
        try:
            root = ET.fromstring(xml_text)

            # Namespaces used in Atom feed
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            # Find link element with rel="next"
            next_link = root.find('atom:link[@rel="next"]', ns)

            if next_link is not None:
                href = next_link.get('href')
                return href

            return None

        except ET.ParseError as e:
            print(f"[ChocolateyFetcher] XML parse error extracting next link: {e}")
            return None
        except Exception as e:
            print(f"[ChocolateyFetcher] Error extracting next link: {e}")
            return None

    def get_package_count(self) -> int:
        """
        Get total count of packages in repository.

        Returns:
            Package count from API (note: API $count may be capped at 10,000)
        """
        try:
            # Use $count endpoint
            url = f"{self.PACKAGES_ENDPOINT}/$count"
            params = {'$filter': "IsLatestVersion eq true"}

            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            count = int(response.text.strip())
            # Note: API may return capped value, actual count fetched via pagination
            return count

        except Exception as e:
            print(f"[ChocolateyFetcher] Failed to get package count: {e}")
            return 0
