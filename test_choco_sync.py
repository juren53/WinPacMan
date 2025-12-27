#!/usr/bin/env python3
"""
Chocolatey Community Repository sync test.
Fetches packages from Chocolatey Community Repository API and syncs to cache.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService
from metadata.providers.chocolatey_provider import ChocolateyProvider
from core.models import UniversalPackageMetadata, PackageManager
from core.config import config_manager
from datetime import datetime


def test_choco_sync():
    """Sync Chocolatey Community Repository to cache."""
    print("=" * 70)
    print("WinPacMan - Chocolatey Community Repository Sync")
    print("=" * 70)

    # Use production cache
    cache_db = config_manager.get_data_file_path("metadata_cache.db")
    print(f"\nCache DB: {cache_db}")

    # Initialize services
    print("\n[1/5] Initializing cache service...")
    cache = MetadataCacheService(cache_db)

    print("[2/5] Initializing Chocolatey provider...")
    provider = ChocolateyProvider()

    # Check current cache status
    print("\n" + "-" * 70)
    print("Current Cache Status:")
    print("-" * 70)
    current_count = cache.get_package_count('chocolatey')
    print(f"Chocolatey packages in cache: {current_count}")

    winget_count = cache.get_package_count('winget')
    print(f"WinGet packages in cache: {winget_count}")

    if cache_db.exists():
        cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
        print(f"Current cache size: {cache_size_mb:.2f} MB")

    # Ask to proceed
    print("\n" + "=" * 70)
    print("This will sync from Chocolatey Community Repository API")
    print("Expected: ~9,500 packages (CCR API limit: 10,000)")
    print("Time: ~5-10 minutes (depends on network speed)")
    print("=" * 70)

    proceed = input("\nProceed with sync? (yes/no): ").strip().lower()

    if proceed != 'yes':
        print("\nSync cancelled.")
        return 0

    # Fetch and sync
    print("\n[3/5] Fetching packages from Chocolatey API and syncing to cache...")
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

            print(f"  Progress: {current:,}/{total:,} ({current*100//total if total > 0 else 0}%) "
                  f"- {rate:.0f} pkg/sec - ETA: {eta:.0f}s")

            last_progress_time = now

    # Fetch packages into list
    print("  Fetching packages from API...")
    all_packages = []
    fetch_errors = 0

    for metadata in provider.fetch_all_packages(progress_callback):
        try:
            all_packages.append(metadata)

            # Show progress every 100 packages
            if len(all_packages) % 100 == 0:
                print(f"    Fetched: {len(all_packages):,} packages (errors: {fetch_errors})")

        except Exception as e:
            fetch_errors += 1
            if fetch_errors <= 5:  # Only show first 5 errors
                print(f"    [WARNING] Error processing package: {e}")

    packages_synced = len(all_packages)
    print(f"\n  Total fetched: {packages_synced:,} packages ({fetch_errors} errors skipped)")

    # Single bulk insert of all packages
    print(f"\n  Caching {packages_synced:,} packages to database...")
    cache.refresh_cache('chocolatey', all_packages)

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
    choco_count = cache.get_package_count('chocolatey')
    winget_count = cache.get_package_count('winget')
    total_count = choco_count + winget_count

    print(f"Chocolatey packages in cache: {choco_count:,}")
    print(f"WinGet packages in cache: {winget_count:,}")
    print(f"Total packages in cache: {total_count:,}")

    # Get cache size
    if cache_db.exists():
        cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
        print(f"Cache size: {cache_size_mb:.2f} MB")

    # Test search performance
    print("\n[5/5] Testing search with real packages...")
    print("-" * 70)

    test_queries = [
        ("chrome", "chocolatey"),
        ("python", "chocolatey"),
        ("git", "chocolatey"),
        ("vscode", "chocolatey"),
        ("notepad++", "chocolatey"),
        ("firefox", "chocolatey"),
        ("vlc", "chocolatey"),
        ("7zip", "chocolatey"),
        # Cross-repo searches
        ("chrome", None),  # Both WinGet and Chocolatey
        ("python", None),  # Both repos
    ]

    total_search_time = 0

    for query, manager_filter in test_queries:
        search_start = time.time()
        managers = [manager_filter] if manager_filter else None
        results = cache.search(query, managers=managers, limit=10)
        search_time = time.time() - search_start
        total_search_time += search_time

        manager_label = manager_filter if manager_filter else "ALL"

        if results:
            print(f"  '{query}' [{manager_label}]: {len(results)} results in {search_time*1000:.2f}ms")
            print(f"    - {results[0].name} ({results[0].package_id}) from {results[0].manager.value}")
        else:
            print(f"  '{query}' [{manager_label}]: No results in {search_time*1000:.2f}ms")

    avg_search_time = total_search_time / len(test_queries)

    # Final summary
    print("\n" + "=" * 70)
    print("Performance Summary:")
    print("=" * 70)
    print(f"  Chocolatey packages: {choco_count:,}")
    print(f"  WinGet packages: {winget_count:,}")
    print(f"  Total packages: {total_count:,}")
    print(f"  Cache size: {cache_size_mb:.2f} MB")
    print(f"  Sync time: {elapsed/60:.2f} minutes")
    print(f"  Avg search: {avg_search_time*1000:.2f}ms")

    if avg_search_time < 0.01 and cache_size_mb < 100:
        print("\n[SUCCESS] Chocolatey repository synced and validated!")
        print("Cross-repository search architecture proven!")
    else:
        print("\n[COMPLETE] Sync finished with warnings")

    print("=" * 70)

    return 0


def main():
    """Run the test."""
    try:
        return test_choco_sync()
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
