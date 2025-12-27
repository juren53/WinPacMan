#!/usr/bin/env python3
"""
Test cross-repository search functionality.
Validates that search works across WinGet and Chocolatey repositories.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import MetadataCacheService
from core.config import config_manager


def test_cross_repo_search():
    """Test cross-repository search with different filters."""
    print("=" * 70)
    print("Cross-Repository Search Test")
    print("=" * 70)

    # Initialize cache
    cache_db = config_manager.get_data_file_path("metadata_cache.db")
    cache = MetadataCacheService(cache_db)

    # Check package counts
    winget_count = cache.get_package_count('winget')
    choco_count = cache.get_package_count('chocolatey')
    total = winget_count + choco_count

    print(f"\nCache Status:")
    print(f"  WinGet: {winget_count:,} packages")
    print(f"  Chocolatey: {choco_count:,} packages")
    print(f"  Total: {total:,} packages")

    if total == 0:
        print("\n[ERROR] Cache is empty. Run test_real_winget_sync.py and test_choco_sync.py first.")
        return 1

    # Test queries
    test_cases = [
        ("python", None, "Cross-repo (both WinGet and Chocolatey)"),
        ("python", ['winget'], "WinGet only"),
        ("python", ['chocolatey'], "Chocolatey only"),
        ("chrome", None, "Cross-repo"),
        ("git", None, "Cross-repo"),
        ("vscode", ['winget'], "WinGet only"),
        ("7zip", ['chocolatey'], "Chocolatey only"),
    ]

    print("\n" + "=" * 70)
    print("Search Tests:")
    print("=" * 70)

    all_passed = True

    for query, managers, description in test_cases:
        print(f"\nTest: '{query}' - {description}")

        results = cache.search(query, managers=managers, limit=10)

        if results:
            print(f"  Results: {len(results)} packages found")

            # Show sources
            sources = {}
            for r in results:
                manager = r.manager.value
                sources[manager] = sources.get(manager, 0) + 1

            for manager, count in sources.items():
                print(f"    - {manager}: {count} packages")

            # Show top 3 results
            print(f"  Top results:")
            for r in results[:3]:
                print(f"    - {r.name} ({r.package_id}) from {r.manager.value}")
        else:
            print(f"  Results: No packages found")
            # This might be expected for some queries
            if managers is None:
                print(f"  [WARNING] Cross-repo search returned no results")
                all_passed = False

    # Cross-repo validation
    print("\n" + "=" * 70)
    print("Cross-Repository Validation:")
    print("=" * 70)

    # Search for "python" in all repos
    cross_results = cache.search("python", managers=None, limit=20)
    winget_results = cache.search("python", managers=['winget'], limit=20)
    choco_results = cache.search("python", managers=['chocolatey'], limit=20)

    print(f"\nSearch for 'python':")
    print(f"  Cross-repo results: {len(cross_results)}")
    print(f"  WinGet-only results: {len(winget_results)}")
    print(f"  Chocolatey-only results: {len(choco_results)}")

    # Verify cross-repo includes results from both
    cross_sources = set(r.manager.value for r in cross_results)

    if 'winget' in cross_sources and 'chocolatey' in cross_sources:
        print(f"\n  [PASS] Cross-repo search includes both WinGet and Chocolatey results")
    elif 'winget' in cross_sources:
        print(f"\n  [WARNING] Cross-repo search only returned WinGet results")
        all_passed = False
    elif 'chocolatey' in cross_sources:
        print(f"\n  [WARNING] Cross-repo search only returned Chocolatey results")
        all_passed = False
    else:
        print(f"\n  [FAIL] Cross-repo search returned no results")
        all_passed = False

    # Final result
    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] All cross-repository search tests passed!")
    else:
        print("[WARNING] Some tests had issues - see warnings above")
    print("=" * 70)

    return 0 if all_passed else 1


def main():
    """Run the test."""
    try:
        return test_cross_repo_search()
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
