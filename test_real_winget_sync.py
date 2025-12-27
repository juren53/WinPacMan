#!/usr/bin/env python3
"""
Real WinGet repository sync test.
Parses the complete microsoft/winget-pkgs repository and syncs to cache.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService
from metadata.sync.local_manifest_parser import LocalManifestParser
from core.models import UniversalPackageMetadata, PackageManager
from core.config import config_manager
from datetime import datetime


def test_real_winget_sync():
    """Sync real WinGet repository to cache."""
    print("=" * 70)
    print("WinPacMan - Real WinGet Repository Sync")
    print("=" * 70)

    # Path to cloned repository
    repo_path = Path("C:/Users/jimur/Projects/winget-pkgs")

    if not repo_path.exists():
        print(f"\n[ERROR] Repository not found at: {repo_path}")
        print("Please clone the repository first:")
        print("  git clone --depth 1 --filter=blob:none --sparse https://github.com/microsoft/winget-pkgs.git")
        print("  cd winget-pkgs && git sparse-checkout set manifests")
        return 1

    # Use production cache
    cache_db = config_manager.get_data_file_path("metadata_cache.db")
    print(f"\nCache DB: {cache_db}")

    # Initialize services
    print("\n[1/5] Initializing cache service...")
    cache = MetadataCacheService(cache_db)

    print("[2/5] Initializing local manifest parser...")
    parser = LocalManifestParser(str(repo_path))

    # Check current cache status
    print("\n" + "-" * 70)
    print("Current Cache Status:")
    print("-" * 70)
    current_count = cache.get_package_count('winget')
    print(f"Packages in cache: {current_count}")

    if cache_db.exists():
        cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
        print(f"Current cache size: {cache_size_mb:.2f} MB")

    # Ask to proceed
    print("\n" + "=" * 70)
    print("This will sync the COMPLETE WinGet repository")
    print("Expected: ~10,000-15,000 packages from local manifests")
    print("Time: ~2-5 minutes")
    print("=" * 70)

    proceed = input("\nProceed with sync? (yes/no): ").strip().lower()

    if proceed != 'yes':
        print("\nSync cancelled.")
        return 0

    # Parse and sync
    print("\n[3/5] Parsing manifests and syncing to cache...")
    print("-" * 70)

    start_time = time.time()
    last_progress_time = start_time
    packages_synced = 0

    def progress_callback(current, total, message):
        nonlocal last_progress_time
        now = time.time()

        # Print progress every 3 seconds
        if now - last_progress_time >= 3.0:
            elapsed = now - start_time
            rate = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / rate if rate > 0 else 0

            print(f"  Progress: {current:,}/{total:,} ({current*100//total}%) "
                  f"- {rate:.0f} pkg/sec - ETA: {eta:.0f}s")

            last_progress_time = now

    # Parse manifests into UniversalPackageMetadata
    print("  Parsing YAML manifests...")
    all_packages = []
    parse_errors = 0

    for pkg_data in parser.parse_all_packages(progress_callback):
        try:
            # Convert to UniversalPackageMetadata
            tags = pkg_data.get('tags', [])
            if isinstance(tags, list):
                tags_str = ','.join(str(t) for t in tags)  # Convert each tag to string
            else:
                tags_str = str(tags) if tags else ''

            metadata = UniversalPackageMetadata(
                package_id=pkg_data['package_id'],
                name=pkg_data['name'],
                version=pkg_data['version'],
                manager=PackageManager.WINGET,
                description=pkg_data.get('description'),
                publisher=pkg_data.get('publisher'),
                homepage=pkg_data.get('homepage'),
                license=pkg_data.get('license'),
                tags=tags_str,
                search_tokens=f"{pkg_data['package_id'].lower()} {pkg_data['name'].lower()} {pkg_data.get('publisher', '').lower()}",
                cache_timestamp=datetime.now()
            )

            all_packages.append(metadata)

            # Show progress every 100 packages
            if len(all_packages) % 100 == 0:
                print(f"    Processed: {len(all_packages):,} packages (errors: {parse_errors})")

        except Exception as e:
            parse_errors += 1
            if parse_errors <= 5:  # Only show first 5 errors
                print(f"    [WARNING] Error processing package: {e}")

    packages_synced = len(all_packages)
    print(f"\n  Total processed: {packages_synced:,} packages ({parse_errors} errors skipped)")

    # Single bulk insert of all packages
    print(f"\n  Caching {packages_synced:,} packages to database...")
    cache.refresh_cache('winget', all_packages)

    elapsed = time.time() - start_time

    # Display results
    print("\n" + "=" * 70)
    print("Sync Results:")
    print("=" * 70)

    print(f"Status: SUCCESS")
    print(f"Packages synced: {packages_synced:,}")
    print(f"Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"Rate: {packages_synced/elapsed:.0f} packages/second")

    # Verify cache
    print("\n[4/5] Verifying cache...")
    final_count = cache.get_package_count('winget')
    print(f"Total packages in cache: {final_count:,}")

    # Get cache size
    if cache_db.exists():
        cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
        print(f"Cache size: {cache_size_mb:.2f} MB")

    # Test search performance
    print("\n[5/5] Testing search with real packages...")
    print("-" * 70)

    test_queries = [
        "Visual Studio Code",
        "Chrome",
        "Python",
        "Microsoft",
        "Notepad++",
        "Firefox",
        "VLC",
        "Git"
    ]

    total_search_time = 0

    for query in test_queries:
        search_start = time.time()
        results = cache.search(query, managers=['winget'], limit=10)
        search_time = time.time() - search_start
        total_search_time += search_time

        if results:
            print(f"  '{query}': {len(results)} results in {search_time*1000:.2f}ms")
            print(f"    - {results[0].name} ({results[0].package_id})")
        else:
            print(f"  '{query}': No results in {search_time*1000:.2f}ms")

    avg_search_time = total_search_time / len(test_queries)

    # Final summary
    print("\n" + "=" * 70)
    print("Performance Summary:")
    print("=" * 70)
    print(f"  Total packages: {final_count:,}")
    print(f"  Cache size: {cache_size_mb:.2f} MB")
    print(f"  Sync time: {elapsed/60:.2f} minutes")
    print(f"  Avg search: {avg_search_time*1000:.2f}ms")

    if avg_search_time < 0.01 and cache_size_mb < 100:
        print("\n[SUCCESS] Real WinGet repository synced and validated!")
        print("Architecture proven with production data!")
    else:
        print("\n[COMPLETE] Sync finished with warnings")

    print("=" * 70)

    return 0


def main():
    """Run the test."""
    try:
        return test_real_winget_sync()
    except KeyboardInterrupt:
        print("\n\nSync interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
