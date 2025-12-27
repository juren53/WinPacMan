#!/usr/bin/env python3
"""
Test script for full repository sync functionality.
Tests syncing the complete WinGet repository (~10,000 packages) into SQLite cache.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService, WinGetProvider
from metadata.sync import BackgroundSyncService
from core.config import config_manager


def test_full_repository_sync():
    """Test syncing the full WinGet repository."""
    print("=" * 70)
    print("WinPacMan - Full Repository Sync Test")
    print("=" * 70)

    # Use production cache database
    cache_db = config_manager.get_data_file_path("metadata_cache.db")
    print(f"\nCache DB: {cache_db}")

    # Initialize services
    print("\n[1/5] Initializing cache service...")
    cache = MetadataCacheService(cache_db)

    print("[2/5] Initializing WinGet provider...")
    winget_provider = WinGetProvider()
    cache.register_provider(winget_provider)

    print("[3/5] Initializing background sync service...")
    sync_service = BackgroundSyncService(cache)
    sync_service.register_provider(winget_provider)

    # Check current status
    print("\n" + "-" * 70)
    print("Current Cache Status:")
    print("-" * 70)

    count = cache.get_package_count('winget')
    sync_status = sync_service.get_sync_status('winget')

    print(f"Packages in cache: {count}")
    print(f"Last sync: {sync_status.get('last_sync_time', 'Never')}")
    print(f"Sync status: {sync_status.get('sync_status', 'unknown')}")

    # Ask user to proceed
    print("\n" + "=" * 70)
    print("WARNING: This will sync the FULL WinGet repository")
    print("Expected: ~10,000 packages, ~50-100MB cache size")
    print("Time: ~2-5 minutes (depending on network speed)")
    print("=" * 70)

    proceed = input("\nProceed with full sync? (yes/no): ").strip().lower()

    if proceed != 'yes':
        print("\nSync cancelled.")
        return 0

    # Start sync
    print("\n[4/5] Starting full repository sync...")
    print("-" * 70)

    start_time = time.time()
    last_progress_time = start_time

    def progress_callback(current, total, message):
        nonlocal last_progress_time
        now = time.time()

        # Print progress every 2 seconds
        if now - last_progress_time >= 2.0:
            elapsed = now - start_time
            rate = current / elapsed if elapsed > 0 else 0
            eta = (total - current) / rate if rate > 0 else 0

            print(f"  Progress: {current}/{total} ({current*100//total}%) "
                  f"- {rate:.1f} pkg/sec - ETA: {eta:.0f}s")

            last_progress_time = now

    result = sync_service.sync_provider('winget', progress_callback)

    elapsed = time.time() - start_time

    # Display results
    print("\n" + "=" * 70)
    print("Sync Results:")
    print("=" * 70)

    print(f"Status: {result.get('status', 'unknown').upper()}")
    print(f"Packages synced: {result.get('package_count', 0)}")
    print(f"Time elapsed: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")

    if result.get('status') == 'error':
        print(f"Error: {result.get('error', 'Unknown error')}")
        return 1

    # Verify cache
    print("\n[5/5] Verifying cache...")
    final_count = cache.get_package_count('winget')
    print(f"Total packages in cache: {final_count}")

    # Get cache size
    if cache_db.exists():
        cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
        print(f"Cache size: {cache_size_mb:.2f} MB")

    # Test search performance
    print("\n" + "-" * 70)
    print("Testing search performance...")
    print("-" * 70)

    test_queries = [
        "python",
        "visual studio code",
        "chrome",
        "microsoft",
        "notepad"
    ]

    total_search_time = 0

    for query in test_queries:
        search_start = time.time()
        results = cache.search(query, managers=['winget'], limit=10)
        search_time = time.time() - search_start
        total_search_time += search_time

        print(f"  '{query}': {len(results)} results in {search_time*1000:.2f}ms")

    avg_search_time = total_search_time / len(test_queries)
    print(f"\nAverage search time: {avg_search_time*1000:.2f}ms")

    # Performance targets
    print("\n" + "=" * 70)
    print("Performance Targets:")
    print("=" * 70)
    print(f"  Package count: {final_count} / ~10,000 (target)")
    print(f"  Cache size: {cache_size_mb:.2f} MB / <100 MB (target)")
    print(f"  Avg search: {avg_search_time*1000:.2f}ms / <10ms (target)")

    if avg_search_time < 0.01:
        print("\n[PASS] Search performance EXCELLENT!")
    elif avg_search_time < 0.05:
        print("\n[PASS] Search performance GOOD")
    else:
        print("\n[WARN] Search performance slower than target")

    print("\n" + "=" * 70)
    print("SUCCESS: Full repository sync completed!")
    print("=" * 70)

    return 0


def main():
    """Run the test."""
    try:
        return test_full_repository_sync()
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
