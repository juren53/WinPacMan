"""
Scoop metadata provider.
"""

import os
import json
import subprocess
from typing import Iterator, Optional
from datetime import datetime, timedelta

from core.models import UniversalPackageMetadata, PackageManager
from .base import MetadataProvider


class ScoopProvider(MetadataProvider):
    """
    Metadata provider for Scoop.
    """

    def __init__(self, cache_duration_hours: int = 24):
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.last_sync_time = None

    def get_manager_name(self) -> str:
        return 'scoop'

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        Get available packages from Scoop by reading the manifests from the buckets.
        """
        print("[ScoopProvider] Fetching all packages from Scoop buckets...")
        scoop_buckets_path = os.path.expandvars(r"%USERPROFILE%\scoop\buckets")

        if not os.path.exists(scoop_buckets_path):
            print("[ScoopProvider] Scoop buckets path not found. Is Scoop installed?")
            return iter([])

        for bucket_name in os.listdir(scoop_buckets_path):
            bucket_path = os.path.join(scoop_buckets_path, bucket_name)
            bucket_manifests_path = os.path.join(bucket_path, 'bucket')

            if not os.path.isdir(bucket_manifests_path):
                bucket_manifests_path = bucket_path

            if os.path.isdir(bucket_manifests_path):
                for filename in os.listdir(bucket_manifests_path):
                    if filename.endswith('.json'):
                        manifest_path = os.path.join(bucket_manifests_path, filename)
                        try:
                            with open(manifest_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                package_id = os.path.splitext(filename)[0]
                                
                                license_data = data.get("license")
                                if isinstance(license_data, dict):
                                    license_str = license_data.get("identifier")
                                else:
                                    license_str = license_data

                                yield UniversalPackageMetadata(
                                    package_id=package_id,
                                    name=package_id,
                                    version=data.get("version", "Unknown"),
                                    manager=PackageManager.SCOOP,
                                    description=data.get("description"),
                                    homepage=data.get("homepage"),
                                    license=license_str,
                                    is_installed=False,
                                    cache_timestamp=datetime.now()
                                )
                        except (json.JSONDecodeError, IOError) as e:
                            print(f"[ScoopProvider] Error reading manifest {manifest_path}: {e}")
                            continue

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """
        Get detailed metadata for a specific package using `scoop info`.
        """
        print(f"[ScoopProvider] Getting details for {package_id}...")
        try:
            result = subprocess.run(
                ['scoop', 'info', package_id],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode == 0:
                return self._parse_scoop_info(result.stdout)
            else:
                print(f"[ScoopProvider] Error running `scoop info {package_id}`: {result.stderr}")

        except FileNotFoundError:
            print("[ScoopProvider] `scoop` command not found.")
        except subprocess.TimeoutExpired:
            print(f"[ScoopProvider] `scoop info {package_id}` timed out.")
        except Exception as e:
            print(f"[ScoopProvider] An error occurred: {e}")

        return None

    def is_cache_stale(self) -> bool:
        if self.last_sync_time is None:
            return True
        return datetime.now() - self.last_sync_time > self.cache_duration

    def _parse_scoop_info(self, output: str) -> Optional[UniversalPackageMetadata]:
        """
        Parse the output of `scoop info`.
        """
        metadata = {}
        for line in output.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip().lower()] = value.strip()

        if 'name' not in metadata:
            return None

        package_id = metadata.get('name')
        name = metadata.get('name')
        version = metadata.get('version')
        description = metadata.get('description')
        homepage = metadata.get('website')
        license = metadata.get('license')

        return UniversalPackageMetadata(
            package_id=package_id,
            name=name,
            version=version,
            manager=PackageManager.SCOOP,
            description=description,
            homepage=homepage,
            license=license,
            is_installed=False, # This method is for available packages
            cache_timestamp=datetime.now()
        )