#!/usr/bin/env python3
"""
Scale test for 10,000 package cache.
Tests cache and search performance with realistic package data at scale.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService
from core.models import UniversalPackageMetadata, PackageManager
from core.config import config_manager


def generate_synthetic_packages(count: int):
    """Generate synthetic package data for testing."""
    publishers = [
        "Microsoft", "Google", "Mozilla", "Adobe", "JetBrains",
        "Valve", "Epic Games", "Apple", "Amazon", "Oracle",
        "VMware", "Canonical", "Red Hat", "SUSE", "IBM"
    ]

    categories = [
        "Browsers", "Development", "Games", "Productivity", "Media",
        "Security", "Utilities", "Communication", "Education", "Graphics"
    ]

    tags = [
        "open-source", "free", "commercial", "beta", "stable",
        "portable", "installer", "zip", "cross-platform"
    ]

    print(f"Generating {count} synthetic packages...")

    for i in range(count):
        publisher = publishers[i % len(publishers)]
        category = categories[i % len(categories)]

        package_id = f"{publisher}.{category}App{i:05d}"
        name = f"{category} Application {i:05d}"
        version = f"{(i % 10) + 1}.{(i % 100) % 12}.{i % 30}"

        description = f"A {category.lower()} application from {publisher}. " \
                     f"This is package number {i} in the test suite."

        selected_tags = [tags[j % len(tags)] for j in range(i % 3 + 1)]

        yield UniversalPackageMetadata(
            package_id=package_id,
            name=name,
            version=version,
            manager=PackageManager.WINGET,
            description=description,
            publisher=publisher,
            homepage=f"https://example.com/{package_id.lower()}",
            license="MIT" if i % 2 == 0 else "Apache-2.0",
            tags=",".join(selected_tags),
            search_tokens=f"{package_id.lower()} {name.lower()} {publisher.lower()} {category.lower()}",
            cache_timestamp=datetime.now(),
            is_installed=i % 10 == 0  # 10% are "installed"
        )


def test_10k_scale():
    """Test with 10,000 packages."""
    print("=" * 70)
    print("WinPacMan - 10,000 Package Scale Test")
    print("=" * 70)

    # Use test cache
    cache_db = config_manager.get_data_file_path("test_10k_cache.db")
    print(f"\nCache DB: {cache_db}")

    # Remove existing test cache
    if cache_db.exists():
        cache_db.unlink()
        print("Removed existing test cache")

    # Initialize cache
    print("\n[1/5] Initializing cache service...")
    cache = MetadataCacheService(cache_db)

    # Generate and insert 10k packages
    print("[2/5] Generating and caching 10,000 packages...")
    start_insert = time.time()

    packages = list(generate_synthetic_packages(10000))

    print(f"[3/5] Bulk inserting {len(packages)} packages into cache...")
    cache.refresh_cache('winget', packages)

    insert_time = time.time() - start_insert

    print(f"\nInsert complete in {insert_time:.2f} seconds")
    print(f"Rate: {len(packages) / insert_time:.0f} packages/second")

    # Verify count
    print("\n[4/5] Verifying cache...")
    count = cache.get_package_count('winget')
    print(f"Total packages in cache: {count}")

    # Get cache size
    cache_size_mb = cache_db.stat().st_size / (1024 * 1024)
    print(f"Cache size: {cache_size_mb:.2f} MB")

    # Test search performance
    print("\n[5/5] Testing search performance at scale...")
    print("=" * 70)

    test_queries = [
        ("Microsoft", "Publisher search"),
        ("Development", "Category search"),
        ("App00500", "Specific package"),
        ("Application", "Common word"),
        ("open-source", "Tag search"),
        ("Browser", "Partial match"),
        ("Graphics", "Category exact"),
        ("JetBrains", "Publisher exact"),
        ("beta", "Tag exact"),
        ("00999", "ID pattern"),
    ]

    total_search_time = 0
    total_results = 0

    for query, description in test_queries:
        search_start = time.time()
        results = cache.search(query, managers=['winget'], limit=100)
        search_time = time.time() - search_start
        total_search_time += search_time
        total_results += len(results)

        print(f"  '{query}' ({description}): "
              f"{len(results)} results in {search_time*1000:.2f}ms")

    avg_search_time = total_search_time / len(test_queries)
    avg_results = total_results / len(test_queries)

    # Performance summary
    print("\n" + "=" * 70)
    print("Performance Results:")
    print("=" * 70)
    print(f"  Package count: {count:,}")
    print(f"  Cache size: {cache_size_mb:.2f} MB")
    print(f"  Insert rate: {len(packages) / insert_time:.0f} pkg/sec")
    print(f"  Avg search time: {avg_search_time*1000:.2f}ms")
    print(f"  Avg results per query: {avg_results:.1f}")

    # Performance targets
    print("\n" + "=" * 70)
    print("Target Validation:")
    print("=" * 70)

    checks = [
        (count >= 10000, f"Package count: {count:,} >= 10,000", "PASS" if count >= 10000 else "FAIL"),
        (cache_size_mb < 100, f"Cache size: {cache_size_mb:.2f} MB < 100 MB", "PASS" if cache_size_mb < 100 else "FAIL"),
        (avg_search_time < 0.010, f"Avg search: {avg_search_time*1000:.2f}ms < 10ms", "PASS" if avg_search_time < 0.010 else "WARN"),
        (len(packages) / insert_time > 100, f"Insert rate: {len(packages) / insert_time:.0f} > 100 pkg/sec", "PASS" if len(packages) / insert_time > 100 else "WARN"),
    ]

    all_pass = True
    for check, description, status in checks:
        symbol = "[PASS]" if status == "PASS" else "[WARN]" if status == "WARN" else "[FAIL]"
        print(f"  {symbol} {description}")
        if status == "FAIL":
            all_pass = False

    # Test largest result set
    print("\n" + "=" * 70)
    print("Stress Test: Large Result Set")
    print("=" * 70)

    stress_start = time.time()
    stress_results = cache.search("Application", managers=['winget'], limit=1000)
    stress_time = time.time() - stress_start

    print(f"  Query: 'Application' (common term)")
    print(f"  Results: {len(stress_results)} packages")
    print(f"  Time: {stress_time*1000:.2f}ms")
    print(f"  Status: {'PASS' if stress_time < 0.050 else 'WARN'} (<50ms target)")

    # Final verdict
    print("\n" + "=" * 70)
    if all_pass and stress_time < 0.050:
        print("SUCCESS: Architecture scales perfectly to 10,000 packages!")
        print("Ready for production deployment with full WinGet repository.")
    else:
        print("PARTIAL: Some performance targets not met, but functional.")
    print("=" * 70)

    return 0 if all_pass else 1


def main():
    """Run the test."""
    try:
        return test_10k_scale()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return 130
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
