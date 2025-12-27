#!/usr/bin/env python3
"""
Test script for metadata caching and search functionality.
Tests WinGet provider, cache service, and FTS5 search.
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService, WinGetProvider
from core.config import config_manager


def test_winget_provider():
    """Test WinGet provider initialization and package reading."""
    print("\n=== Testing WinGet Provider ===")
    provider = WinGetProvider()

    print(f"Manager name: {provider.get_manager_name()}")
    print(f"Cache stale: {provider.is_cache_stale()}")

    # Try to read a few packages
    print("\nReading first 5 packages from WinGet index.db:")
    count = 0
    for pkg in provider.get_available_packages():
        if count >= 5:
            break
        print(f"  {count+1}. {pkg.name} ({pkg.package_id}) - v{pkg.version}")
        count += 1

    if count == 0:
        print("  WARNING: No packages found in WinGet index.db")
        print(f"  DB Path: {provider.db_path}")
        return False

    return True


def test_metadata_cache():
    """Test metadata cache service initialization and search."""
    print("\n=== Testing Metadata Cache Service ===")

    # Use a test database
    cache_db = config_manager.get_data_file_path("test_metadata_cache.db")
    print(f"Cache DB: {cache_db}")

    # Remove existing test cache
    if cache_db.exists():
        cache_db.unlink()
        print("Removed existing test cache")

    # Initialize service
    cache = MetadataCacheService(cache_db)

    # Register WinGet provider
    winget_provider = WinGetProvider()
    cache.register_provider(winget_provider)
    print("Registered WinGet provider")

    # Check initial count
    count = cache.get_package_count('winget')
    print(f"Initial package count: {count}")

    if count == 0:
        print("\nInitializing cache (this may take 20-30 seconds)...")
        start = time.time()
        cache.refresh_cache('winget')
        elapsed = time.time() - start

        count = cache.get_package_count('winget')
        print(f"Cache initialized in {elapsed:.2f} seconds")
        print(f"Total packages cached: {count}")

    return cache, count > 0


def test_search(cache):
    """Test search functionality with various queries."""
    print("\n=== Testing Search Functionality ===")

    test_queries = [
        ("notepad", "Common app search"),
        ("Microsoft.VisualStudioCode", "Exact ID search"),
        ("python", "General keyword search"),
        ("browser", "Category search"),
    ]

    for query, description in test_queries:
        print(f"\nQuery: '{query}' ({description})")

        start = time.time()
        results = cache.search(query, managers=['winget'], limit=5)
        elapsed = time.time() - start

        print(f"  Found {len(results)} results in {elapsed*1000:.2f}ms")

        for i, pkg in enumerate(results[:3], 1):
            print(f"    {i}. {pkg.name} ({pkg.package_id})")
            if pkg.description:
                desc = pkg.description[:60] + "..." if len(pkg.description) > 60 else pkg.description
                print(f"       {desc}")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("WinPacMan Metadata Cache and Search Test")
    print("=" * 60)

    # Test 1: WinGet Provider
    if not test_winget_provider():
        print("\n[FAIL] WinGet provider test failed")
        return 1

    print("\n[PASS] WinGet provider test passed")

    # Test 2: Metadata Cache
    cache, success = test_metadata_cache()
    if not success:
        print("\n[FAIL] Metadata cache test failed")
        return 1

    print("\n[PASS] Metadata cache test passed")

    # Test 3: Search
    if not test_search(cache):
        print("\n[FAIL] Search test failed")
        return 1

    print("\n[PASS] Search test passed")

    print("\n" + "=" * 60)
    print("SUCCESS: All tests passed!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
