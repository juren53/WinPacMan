# WinPacMan Metadata Cache Architecture

## Overview

Unified metadata caching system for cross-repository package search, inspired by APT's architecture but adapted for Windows package managers.

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│           UI Layer (PyQt6)                          │
│  - Search bar with live results                    │
│  - Package details dialog                          │
│  - Multi-manager filter                            │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│      Service Layer (MetadataCache)                  │
│  - Unified search API                               │
│  - Cache management                                 │
│  - Background sync workers                          │
└─────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   WinGet    │ │  Chocolatey │ │     Pip     │
│  Provider   │ │   Provider  │ │  Provider   │
└─────────────┘ └─────────────┘ └─────────────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ SQLite DB   │ │  OData API  │ │  PyPI API   │
│ (index.db)  │ │  + .nuspec  │ │   (JSON)    │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Core Components

### 1. Abstract Base Provider

```python
# cache/providers/base.py

from abc import ABC, abstractmethod
from typing import List, Iterator, Optional
from core.metadata_models import UniversalPackageMetadata

class MetadataProvider(ABC):
    """Base class for all package manager metadata providers"""

    @abstractmethod
    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """Yield all available packages from this manager's repository"""
        pass

    @abstractmethod
    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """Get detailed metadata for a specific package"""
        pass

    @abstractmethod
    def is_cache_stale(self) -> bool:
        """Check if local cache needs refreshing"""
        pass

    @abstractmethod
    def get_manager_name(self) -> str:
        """Return the manager identifier (e.g., 'winget')"""
        pass
```

### 2. WinGet Provider (Fast - Local SQLite)

```python
# cache/providers/winget_provider.py

import sqlite3
import os
from typing import Iterator
from .base import MetadataProvider
from core.metadata_models import UniversalPackageMetadata, PackageManager

class WinGetProvider(MetadataProvider):
    """Provider for WinGet using local index.db"""

    DB_PATH = os.path.expandvars(
        r'%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\index.db'
    )

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """Read from local WinGet SQLite database"""

        if not os.path.exists(self.DB_PATH):
            return

        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()

        # WinGet schema: tables like 'manifest', 'names', 'versions'
        query = """
        SELECT DISTINCT
            m.id as package_id,
            n.name,
            v.version,
            m.publisher,
            m.description
        FROM manifest m
        JOIN names n ON m.id = n.manifest_id
        JOIN versions v ON m.id = v.manifest_id
        ORDER BY m.id, v.version DESC
        """

        cursor.execute(query)

        for row in cursor.fetchall():
            yield UniversalPackageMetadata(
                package_id=row[0],
                name=row[1],
                version=row[2],
                manager=PackageManager.WINGET,
                author=row[3],
                description=row[4],
                search_tokens=self._generate_tokens(row[0], row[1], row[4])
            )

        conn.close()

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """Get detailed info via 'winget show' command"""
        import subprocess

        result = subprocess.run(
            ['winget', 'show', '--id', package_id, '--accept-source-agreements'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return self._parse_winget_show(result.stdout, package_id)

        return None

    def is_cache_stale(self) -> bool:
        """Check if index.db has been modified"""
        # Compare file modification time with our cache timestamp
        pass

    def _generate_tokens(self, *fields) -> List[str]:
        """Generate searchable tokens from text fields"""
        tokens = []
        for field in fields:
            if field:
                tokens.extend(field.lower().split())
        return list(set(tokens))
```

### 3. Chocolatey Provider (Hybrid - OData API + Local)

```python
# cache/providers/chocolatey_provider.py

import requests
import xml.etree.ElementTree as ET
from typing import Iterator

class ChocolateyProvider(MetadataProvider):
    """Provider for Chocolatey using OData API"""

    ODATA_URL = "https://community.chocolatey.org/api/v2/Packages"

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """Fetch from OData API (paginated)"""

        skip = 0
        batch_size = 100

        while True:
            params = {
                '$skip': skip,
                '$top': batch_size,
                '$orderby': 'Id'
            }

            response = requests.get(self.ODATA_URL, params=params, timeout=30)

            if response.status_code != 200:
                break

            root = ET.fromstring(response.text)
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')

            if not entries:
                break

            for entry in entries:
                props = entry.find('.//{http://schemas.microsoft.com/ado/2007/08/dataservices/metadata}properties')

                yield UniversalPackageMetadata(
                    package_id=props.find('.//d:Id', namespaces={'d': '...'}).text,
                    name=props.find('.//d:Title', namespaces={'d': '...'}).text,
                    version=props.find('.//d:Version', namespaces={'d': '...'}).text,
                    manager=PackageManager.CHOCOLATEY,
                    description=props.find('.//d:Description', namespaces={'d': '...'}).text,
                    author=props.find('.//d:Authors', namespaces={'d': '...'}).text
                )

            skip += batch_size
```

### 4. Pip Provider (API-based)

```python
# cache/providers/pip_provider.py

import requests
from typing import Iterator

class PipProvider(MetadataProvider):
    """Provider for Pip using PyPI JSON API"""

    PYPI_API = "https://pypi.org/pypi/{package}/json"
    PYPI_SEARCH = "https://pypi.org/search/?q={query}"

    def get_available_packages(self) -> Iterator[UniversalPackageMetadata]:
        """
        WARNING: PyPI has 500k+ packages. Don't fetch all!
        Only fetch on-demand during search.
        """
        # Return empty iterator - we'll populate on search
        return iter([])

    def search_packages(self, query: str) -> Iterator[UniversalPackageMetadata]:
        """Search PyPI and return results"""
        # Use PyPI search API
        pass

    def get_package_details(self, package_id: str) -> Optional[UniversalPackageMetadata]:
        """Fetch specific package from PyPI"""
        url = self.PYPI_API.format(package=package_id)

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            info = data['info']

            return UniversalPackageMetadata(
                package_id=info['name'],
                name=info['name'],
                version=info['version'],
                manager=PackageManager.PIP,
                description=info['summary'],
                author=info['author'],
                homepage=info['home_page'],
                license=info['license']
            )

        return None
```

### 5. Metadata Cache Service

```python
# cache/metadata_cache.py

import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta
from .providers.base import MetadataProvider

class MetadataCacheService:
    """Central service for managing unified package metadata cache"""

    def __init__(self, cache_db_path: str):
        self.cache_db_path = cache_db_path
        self.providers: List[MetadataProvider] = []
        self._init_database()

    def register_provider(self, provider: MetadataProvider):
        """Register a package manager provider"""
        self.providers.append(provider)

    def refresh_cache(self, manager: Optional[str] = None, force: bool = False):
        """Refresh metadata cache from providers"""

        for provider in self.providers:
            # Skip if not specified or cache is fresh
            if manager and provider.get_manager_name() != manager:
                continue

            if not force and not provider.is_cache_stale():
                continue

            print(f"Refreshing cache for {provider.get_manager_name()}...")

            # Clear existing cache for this manager
            self._clear_manager_cache(provider.get_manager_name())

            # Insert new metadata
            for package in provider.get_available_packages():
                self._insert_package(package)

        # Rebuild FTS index
        self._rebuild_fts_index()

    def search(self, query: str, managers: Optional[List[str]] = None) -> List[UniversalPackageMetadata]:
        """
        Search across all managers using FTS.

        Args:
            query: Search query
            managers: List of managers to search (None = all)

        Returns:
            List of matching packages
        """
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        # Build WHERE clause for manager filter
        manager_filter = ""
        if managers:
            placeholders = ','.join(['?' for _ in managers])
            manager_filter = f"AND manager IN ({placeholders})"

        # FTS search query
        sql = f"""
        SELECT p.* FROM packages p
        JOIN packages_fts fts ON p.rowid = fts.rowid
        WHERE packages_fts MATCH ?
        {manager_filter}
        ORDER BY rank
        LIMIT 100
        """

        params = [query]
        if managers:
            params.extend(managers)

        cursor.execute(sql, params)

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_package(row))

        conn.close()
        return results

    def get_package_details(self, package_id: str, manager: str) -> Optional[UniversalPackageMetadata]:
        """Get detailed package info (from cache or provider)"""

        # Try cache first
        package = self._get_from_cache(package_id, manager)

        if package:
            return package

        # Fall back to provider
        provider = self._get_provider(manager)
        if provider:
            return provider.get_package_details(package_id)

        return None
```

## Implementation Strategy

### Phase 1: WinGet Only (Week 1)
1. Implement `WinGetProvider` to read from `index.db`
2. Create basic `MetadataCacheService` with SQLite cache
3. Add search functionality with FTS
4. UI: Add search bar to main window

### Phase 2: Add Chocolatey (Week 2)
1. Implement `ChocolateyProvider` with OData API
2. Add background sync worker (QThread)
3. Cache expiration logic (refresh every 24 hours)

### Phase 3: Add Pip/NPM (Week 3)
1. Implement on-demand search (don't cache all 500k packages)
2. Add "Search in external repos" checkbox
3. Merge results from local cache + external APIs

### Phase 4: Scoop, Cargo, PowerShell (Week 4)
1. Implement remaining providers
2. Add provider priority/ordering
3. Performance optimization (index tuning)

## Key Design Decisions

1. **SQLite FTS5** for fast full-text search (like apt-cache)
2. **Lazy loading** for massive repos (Pip, NPM)
3. **Provider pattern** for extensibility
4. **Background sync** to avoid UI freezing
5. **Unified data model** like APT's Deb822

## Performance Targets

- Search response: <100ms for local cache
- Cache refresh: <30 seconds for WinGet (~10k packages)
- UI responsiveness: No blocking on main thread

## Files to Create

```
cache/
  __init__.py
  metadata_cache.py         # Main service
  providers/
    __init__.py
    base.py                 # Abstract provider
    winget_provider.py
    chocolatey_provider.py
    pip_provider.py
    npm_provider.py
    scoop_provider.py
    cargo_provider.py
    powershell_provider.py
```
