"""
GitHub manifest fetcher for WinGet packages.

Downloads and parses package manifests from the microsoft/winget-pkgs GitHub repository.
"""

import requests
import yaml
import time
from typing import Iterator, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


class GitHubManifestFetcher:
    """
    Fetches WinGet package manifests from the GitHub repository.

    The microsoft/winget-pkgs repository contains YAML manifests organized as:
    manifests/[first-letter]/[publisher]/[package-name]/[version]/
    """

    REPO_OWNER = "microsoft"
    REPO_NAME = "winget-pkgs"
    API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/master"

    # Rate limiting
    REQUESTS_PER_HOUR = 60  # GitHub unauthenticated rate limit
    REQUEST_DELAY = 3600 / REQUESTS_PER_HOUR  # ~60 seconds between requests

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the fetcher.

        Args:
            github_token: Optional GitHub personal access token for higher rate limits
        """
        self.github_token = github_token
        self.session = requests.Session()

        if github_token:
            self.session.headers['Authorization'] = f'token {github_token}'

        self.last_request_time = 0
        self.rate_limit_remaining = self.REQUESTS_PER_HOUR

    def _rate_limit_wait(self):
        """Implement rate limiting to avoid hitting GitHub API limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str, use_rate_limit: bool = True) -> Optional[requests.Response]:
        """
        Make a request to GitHub API with rate limiting.

        Args:
            url: URL to request
            use_rate_limit: Whether to apply rate limiting

        Returns:
            Response object or None if request failed
        """
        if use_rate_limit:
            self._rate_limit_wait()

        try:
            response = self.session.get(url, timeout=30)

            # Update rate limit info
            if 'X-RateLimit-Remaining' in response.headers:
                self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])

            if response.status_code == 200:
                return response
            elif response.status_code == 403:
                print(f"[GitHubFetcher] Rate limit exceeded. Remaining: {self.rate_limit_remaining}")
                return None
            else:
                print(f"[GitHubFetcher] Request failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            print(f"[GitHubFetcher] Request error: {e}")
            return None

    def get_package_list(self) -> list[str]:
        """
        Get a list of all package IDs from the repository.

        This uses a simplified approach: fetch the community.txt file which lists
        all package IDs, one per line.

        Returns:
            List of package IDs
        """
        print("[GitHubFetcher] Fetching package list from repository...")

        # Try to get the package list from a known index file
        # Note: This file doesn't exist by default, so we'll need to use an alternative approach

        # Alternative: Use GitHub tree API to browse the manifests directory
        url = f"{self.API_BASE}/git/trees/master?recursive=1"
        response = self._make_request(url)

        if not response:
            print("[GitHubFetcher] Failed to fetch repository tree")
            return []

        tree_data = response.json()

        # Extract package paths from the tree
        # Paths look like: manifests/m/Microsoft/VisualStudioCode/1.85.0/...
        package_ids = set()

        for item in tree_data.get('tree', []):
            path = item.get('path', '')
            if path.startswith('manifests/') and '/' in path[10:]:
                # Extract package ID from path
                parts = path.split('/')
                if len(parts) >= 4:
                    # manifests/[letter]/[Publisher]/[Package]/...
                    publisher = parts[2]
                    package = parts[3]
                    package_id = f"{publisher}.{package}"
                    package_ids.add(package_id)

        print(f"[GitHubFetcher] Found {len(package_ids)} unique packages")
        return sorted(package_ids)

    def fetch_package_manifest(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse the manifest for a specific package.

        Args:
            package_id: Package ID (e.g., "Microsoft.VisualStudioCode")

        Returns:
            Parsed manifest dictionary or None if not found
        """
        # Split package ID into publisher and package name
        parts = package_id.split('.', 1)
        if len(parts) != 2:
            print(f"[GitHubFetcher] Invalid package ID format: {package_id}")
            return None

        publisher, package = parts

        # Construct path to manifest
        # Format: manifests/[first-letter]/[Publisher]/[Package]/
        first_letter = publisher[0].lower()
        manifest_dir = f"manifests/{first_letter}/{publisher}/{package}"

        # We need to find the latest version
        # For simplicity, we'll try to fetch a version-agnostic manifest if it exists
        # Otherwise, we need to list versions and pick the latest

        # Try to find the latest version by browsing the directory
        url = f"{self.API_BASE}/contents/{manifest_dir}"
        response = self._make_request(url)

        if not response:
            return None

        try:
            contents = response.json()

            # Find version directories
            versions = []
            for item in contents:
                if item['type'] == 'dir':
                    versions.append(item['name'])

            if not versions:
                print(f"[GitHubFetcher] No versions found for {package_id}")
                return None

            # Sort versions (simple string sort, may not be perfect for semver)
            versions.sort(reverse=True)
            latest_version = versions[0]

            # Fetch the installer manifest (or version manifest)
            version_path = f"{manifest_dir}/{latest_version}"
            version_url = f"{self.API_BASE}/contents/{version_path}"
            version_response = self._make_request(version_url)

            if not version_response:
                return None

            version_contents = version_response.json()

            # Look for the main installer manifest file
            manifest_file = None
            for item in version_contents:
                if item['name'].endswith('.installer.yaml') or item['name'].endswith('.yaml'):
                    manifest_file = item
                    break

            if not manifest_file:
                print(f"[GitHubFetcher] No manifest file found for {package_id} v{latest_version}")
                return None

            # Download and parse the YAML manifest
            manifest_url = manifest_file['download_url']
            manifest_response = self._make_request(manifest_url, use_rate_limit=False)

            if not manifest_response:
                return None

            # Parse YAML
            try:
                manifest_data = yaml.safe_load(manifest_response.text)

                # Add metadata
                manifest_data['_fetched_version'] = latest_version
                manifest_data['_fetched_time'] = datetime.now().isoformat()

                return manifest_data

            except yaml.YAMLError as e:
                print(f"[GitHubFetcher] Failed to parse YAML for {package_id}: {e}")
                return None

        except (ValueError, KeyError) as e:
            print(f"[GitHubFetcher] Error processing manifest for {package_id}: {e}")
            return None

    def fetch_all_manifests_iterator(self, package_ids: list[str]) -> Iterator[Dict[str, Any]]:
        """
        Fetch all manifests for a list of package IDs.

        Args:
            package_ids: List of package IDs to fetch

        Yields:
            Parsed manifest dictionaries
        """
        total = len(package_ids)

        for i, package_id in enumerate(package_ids, 1):
            if i % 10 == 0:
                print(f"[GitHubFetcher] Progress: {i}/{total} packages ({i*100//total}%)")

            manifest = self.fetch_package_manifest(package_id)
            if manifest:
                manifest['PackageIdentifier'] = package_id
                yield manifest
            else:
                # Don't let failures stop the entire sync
                continue

    def parse_manifest_to_metadata(self, manifest: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a WinGet YAML manifest into our metadata format.

        Args:
            manifest: Parsed YAML manifest dictionary

        Returns:
            Metadata dictionary compatible with UniversalPackageMetadata
        """
        try:
            package_id = manifest.get('PackageIdentifier', '')
            name = manifest.get('PackageName', package_id)
            version = manifest.get('PackageVersion', manifest.get('_fetched_version', 'Unknown'))
            publisher = manifest.get('Publisher', '')
            description = manifest.get('ShortDescription', manifest.get('Description', ''))
            homepage = manifest.get('PackageUrl', '')
            license_info = manifest.get('License', '')

            # Extract tags if available
            tags = manifest.get('Tags', [])
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
                'tags': tags_str
            }

        except Exception as e:
            print(f"[GitHubFetcher] Error parsing manifest: {e}")
            return None
