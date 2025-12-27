# Sync-to-SQL Hybrid Architecture

## Overview

Build an optimized local SQLite index by periodically syncing package metadata from various sources. This provides instant search performance while maintaining up-to-date package information.

## Core Principles

1. **Local-First**: All searches hit SQLite cache (sub-10ms performance)
2. **Background Sync**: Periodic updates from upstream sources (configurable intervals)
3. **Incremental Updates**: Only sync changes when possible
4. **Provider Abstraction**: Each package manager has its own sync strategy

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   User Interface                         │
│              (Search bar, Package list)                  │
└────────────────────┬────────────────────────────────────┘
                     │ Query (instant)
                     ▼
┌─────────────────────────────────────────────────────────┐
│           MetadataCacheService (SQLite + FTS5)          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Unified Package Cache (all managers combined)   │   │
│  │  • Full-text search index                        │   │
│  │  • Normalized schema                             │   │
│  │  • Last sync timestamps                          │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │ Background Sync (periodic)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              MetadataProvider (Abstract)                 │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   WinGet     │  │  Chocolatey  │  │     Pip      │  │
│  │   Provider   │  │   Provider   │  │   Provider   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                  │          │
└─────────┼─────────────────┼──────────────────┼──────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│ GitHub Manifests │ │ Choco API    │ │  PyPI JSON API  │
│ (winget-pkgs)    │ │              │ │                 │
└──────────────────┘ └──────────────┘ └─────────────────┘
```

## Sync Strategies by Provider

### WinGet Provider

**Source**: GitHub repository (microsoft/winget-pkgs)
**Package Count**: ~10,000
**Update Frequency**: Daily (repository gets ~100-200 updates/day)

**Sync Strategy**:
```python
# Option 1: GitHub REST API (rate limited: 60 req/hour unauthenticated)
# - Fetch latest commit SHA
# - If changed, download updated manifests
# - Parse YAML manifests

# Option 2: Clone/Pull repository (recommended)
# - Git sparse-checkout for manifest directories only
# - Parse local YAML files
# - Track last sync SHA in database

# Option 3: Use winget.run API (fallback)
# - Fetch package list
# - Download metadata
```

**Implementation Priority**: HIGH (Phase 1.5)

### Chocolatey Provider

**Source**: Chocolatey Community Repository API
**Package Count**: ~9,500
**Update Frequency**: Multiple times daily

**Sync Strategy**:
```python
# Option 1: OData API (recommended)
# - Query: https://community.chocolatey.org/api/v2/Packages()
# - Supports $filter, $orderby, $skip for pagination
# - Download XML/JSON package metadata

# Option 2: Local cache (if Chocolatey installed)
# - Parse: %ProgramData%\chocolatey\lib
```

**Implementation Priority**: MEDIUM (Phase 2)

### Pip Provider

**Source**: PyPI (Python Package Index)
**Package Count**: ~500,000+ (TOO LARGE for full sync)
**Update Frequency**: Constantly

**Sync Strategy**:
```python
# Option 1: Lazy/On-Demand (recommended)
# - Only cache packages user searches for
# - Use PyPI JSON API: https://pypi.org/pypi/{package}/json
# - Cache for 7 days

# Option 2: Popular packages only
# - Sync top 5,000 most downloaded packages
# - Use PyPI Stats API or hugovk/top-pypi-packages

# Option 3: Simple API (browse all, but expensive)
# - https://pypi.org/simple/ lists all packages
# - Would take hours to sync fully
```

**Implementation Priority**: LOW (Phase 3 - lazy loading)

### NPM Provider

**Source**: NPM registry
**Package Count**: ~2,000,000+ (TOO LARGE for full sync)
**Update Frequency**: Constantly

**Sync Strategy**:
```python
# Option 1: Lazy/On-Demand (recommended)
# - Same as Pip strategy
# - Use registry API: https://registry.npmjs.org/{package}

# Option 2: Global installed packages only
# - Parse: npm list -g --json
```

**Implementation Priority**: LOW (Phase 3 - lazy loading)

## Database Schema Enhancements

### Add Sync Tracking Table

```sql
CREATE TABLE sync_metadata (
    provider TEXT PRIMARY KEY,
    last_sync_time DATETIME,
    last_sync_sha TEXT,          -- For git-based sources
    package_count INTEGER,
    sync_status TEXT,             -- 'success', 'partial', 'failed'
    error_message TEXT,
    next_sync_time DATETIME
);
```

### Update Package Table

```sql
ALTER TABLE packages ADD COLUMN last_updated DATETIME;
ALTER TABLE packages ADD COLUMN sync_source TEXT; -- 'api', 'github', 'local'
```

## Sync Implementation

### BackgroundSyncService Class

```python
class BackgroundSyncService:
    """Manages periodic syncing of package metadata."""

    def __init__(self, cache_service, config_manager):
        self.cache = cache_service
        self.config = config_manager
        self.providers = {}
        self.sync_thread = None

    def register_provider(self, provider):
        """Register a provider for syncing."""
        manager_name = provider.get_manager_name()
        self.providers[manager_name] = provider

    def start_background_sync(self):
        """Start background sync thread."""
        # Check if sync is due
        # Run sync for each provider
        # Update cache
        # Schedule next sync

    def sync_provider(self, manager_name):
        """Sync a specific provider."""
        provider = self.providers.get(manager_name)
        if provider and provider.needs_sync():
            packages = provider.fetch_all_packages()
            self.cache.bulk_update(manager_name, packages)

    def get_sync_status(self):
        """Get sync status for all providers."""
        return {
            name: {
                'last_sync': provider.last_sync_time,
                'package_count': provider.package_count,
                'status': provider.sync_status
            }
            for name, provider in self.providers.items()
        }
```

## Configuration

### User Settings (config.json)

```json
{
  "metadata_sync": {
    "enabled": true,
    "auto_sync_on_startup": false,
    "sync_intervals": {
      "winget": "daily",
      "chocolatey": "weekly",
      "pip": "on_demand",
      "npm": "on_demand"
    },
    "sync_time": "03:00",  // 3 AM local time
    "max_age_days": {
      "winget": 1,
      "chocolatey": 7,
      "pip": 30,
      "npm": 30
    }
  }
}
```

## Performance Targets

| Operation | Target | Expected Result |
|-----------|--------|-----------------|
| Initial WinGet Sync | < 5 minutes | ~10,000 packages |
| Daily WinGet Refresh | < 30 seconds | ~100-200 updates |
| Search (10k packages) | < 10ms | Instant results |
| Cache Size (WinGet) | < 50MB | Compressed SQLite |
| Memory Usage | < 100MB | During sync operation |

## Phase 1.5 Implementation Plan

1. **Enhance WinGetProvider** (this week)
   - Add `fetch_all_packages()` method
   - Implement GitHub manifest parser
   - Add sync tracking

2. **Create BackgroundSyncService** (this week)
   - Basic sync orchestration
   - Manual sync trigger from UI
   - Sync status reporting

3. **UI Integration** (next week)
   - Add "Sync Repository" button
   - Show sync progress bar
   - Display last sync time

4. **Testing & Optimization** (next week)
   - Benchmark full sync
   - Optimize bulk insert performance
   - Test with full WinGet repository

## Future Enhancements (Post-Phase 1.5)

- **Delta Sync**: Only download changed manifests
- **Compression**: Use SQLite compression for package descriptions
- **CDN Caching**: Cache GitHub raw content locally
- **Parallel Sync**: Sync multiple providers simultaneously
- **Smart Scheduling**: Sync during idle time
- **Backup/Restore**: Export/import cache for offline use

## References

- [WinGet Manifests Repository](https://github.com/microsoft/winget-pkgs)
- [Chocolatey OData API](https://docs.chocolatey.org/en-us/community-repository/api)
- [PyPI JSON API](https://warehouse.pypa.io/api-reference/json.html)
- [NPM Registry API](https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md)
