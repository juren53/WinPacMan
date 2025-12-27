from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class PackageManager(Enum):
    """Supported package managers"""
    WINGET = "winget"
    CHOCOLATEY = "chocolatey"
    PIP = "pip"
    NPM = "npm"
    SCOOP = "scoop"
    MSSTORE = "msstore"
    UNKNOWN = "unknown"  # For manually installed packages with unknown source


class PackageStatus(Enum):
    """Package installation status"""
    INSTALLED = "installed"
    AVAILABLE = "available"
    OUTDATED = "outdated"
    INSTALLING = "installing"
    UNINSTALLING = "uninstalling"
    UPDATING = "updating"
    FAILED = "failed"


class OperationType(Enum):
    """Types of operations on packages"""
    INSTALL = "install"
    UNINSTALL = "uninstall"
    UPDATE = "update"
    SEARCH = "search"
    LIST = "list"


class OperationStage(Enum):
    """Stages of package operations"""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Package:
    """Represents a software package"""
    name: str
    id: str
    version: str
    manager: PackageManager
    status: PackageStatus = PackageStatus.AVAILABLE
    description: Optional[str] = None
    size: Optional[str] = None
    publisher: Optional[str] = None
    homepage: Optional[str] = None
    install_date: Optional[datetime] = None
    update_available: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert package to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "id": self.id,
            "version": self.version,
            "manager": self.manager.value,
            "status": self.status.value,
            "description": self.description,
            "size": self.size,
            "publisher": self.publisher,
            "homepage": self.homepage,
            "install_date": self.install_date.isoformat() if self.install_date else None,
            "update_available": self.update_available,
            "tags": self.tags,
            "dependencies": self.dependencies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Package':
        """Create package from dictionary"""
        return cls(
            name=data["name"],
            id=data["id"],
            version=data["version"],
            manager=PackageManager(data["manager"]),
            status=PackageStatus(data.get("status", "available")),
            description=data.get("description"),
            size=data.get("size"),
            publisher=data.get("publisher"),
            homepage=data.get("homepage"),
            install_date=datetime.fromisoformat(data["install_date"]) if data.get("install_date") else None,
            update_available=data.get("update_available"),
            tags=data.get("tags", []),
            dependencies=data.get("dependencies", [])
        )


@dataclass
class OperationProgress:
    """Progress information for package operations"""
    operation: str
    package: str
    stage: str
    current: int = 0
    total: int = 100
    message: str = ""
    speed: Optional[float] = None
    eta: Optional[int] = None
    error: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total > 0:
            return (self.current / self.total) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation": self.operation,
            "package": self.package,
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "message": self.message,
            "speed": self.speed,
            "eta": self.eta,
            "error": self.error
        }


@dataclass
class OperationResult:
    """Result of a package operation"""
    operation: str
    package: str
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "operation": self.operation,
            "package": self.package,
            "success": self.success,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SearchQuery:
    """Search query for package discovery"""
    query: str
    manager: Optional[PackageManager] = None
    category: Optional[str] = None
    include_installed: bool = True
    include_available: bool = True
    exact_match: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "manager": self.manager.value if self.manager else None,
            "category": self.category,
            "include_installed": self.include_installed,
            "include_available": self.include_available,
            "exact_match": self.exact_match
        }


@dataclass
class PackageListResult:
    """Result of package listing operation"""
    packages: List[Package]
    total_count: int
    query: Optional[SearchQuery] = None
    source: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "packages": [pkg.to_dict() for pkg in self.packages],
            "total_count": self.total_count,
            "query": self.query.to_dict() if self.query else None,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class UniversalPackageMetadata:
    """
    Unified metadata structure for package cache system.

    This model is used by the metadata cache to store package information
    from all package managers in a normalized format for fast searching.
    """
    package_id: str           # Unique ID (e.g., "Microsoft.VisualStudioCode")
    name: str                 # Display name
    version: str              # Current/latest version
    manager: PackageManager   # Source manager

    # Optional common fields
    description: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    homepage: Optional[str] = None
    license: Optional[str] = None

    # Manager-specific metadata (stored as JSON string)
    extra_metadata: Optional[str] = None

    # Search/indexing fields
    search_tokens: Optional[str] = None  # Space-separated tokens for FTS
    tags: Optional[str] = None            # Comma-separated tags

    # Cache metadata
    cache_timestamp: Optional[datetime] = None
    is_installed: bool = False

    # Installed package metadata (from registry scan)
    installed_version: Optional[str] = None
    install_date: Optional[str] = None
    install_source: Optional[str] = None  # "winget", "chocolatey", "scoop", "msstore", "unknown"
    install_location: Optional[str] = None

    def to_package(self, cache_service=None) -> Package:
        """
        Convert to standard Package object.

        Args:
            cache_service: Optional MetadataCacheService for manager resolution.
                          When provided, UNKNOWN managers are resolved by querying
                          available packages cache.

        Returns:
            Package object with resolved manager
        """
        manager = self.manager

        # Smart manager resolution for UNKNOWN packages
        # If registry fingerprinting failed, check if package exists in available repos
        if manager == PackageManager.UNKNOWN and cache_service and self.is_installed:
            repo_manager = cache_service.get_manager_for_package(
                package_id=self.package_id,
                package_name=self.name
            )
            if repo_manager:
                manager = PackageManager(repo_manager)
                print(f"[SmartManager] Resolved {self.name}: unknown -> {repo_manager}")

        return Package(
            name=self.name,
            id=self.package_id,
            version=self.version,
            manager=manager,
            status=PackageStatus.INSTALLED if self.is_installed else PackageStatus.AVAILABLE,
            description=self.description,
            publisher=self.publisher or self.author,
            homepage=self.homepage,
            tags=self.tags.split(',') if self.tags else []
        )


# Custom exceptions for package management
class PackageManagerError(Exception):
    """Base exception for package manager operations"""
    pass


class PackageNotFoundError(PackageManagerError):
    """Exception raised when a package is not found"""
    def __init__(self, package_id: str, manager: str):
        super().__init__(f"Package '{package_id}' not found in {manager}")
        self.package_id = package_id
        self.manager = manager


class OperationFailedError(PackageManagerError):
    """Exception raised when an operation fails"""
    def __init__(self, operation: str, package: str, message: str):
        super().__init__(f"{operation} failed for {package}: {message}")
        self.operation = operation
        self.package = package
        self.message = message


class PackageManagerNotAvailableError(PackageManagerError):
    """Exception raised when a package manager is not available"""
    def __init__(self, manager: str):
        super().__init__(f"Package manager '{manager}' is not available")
        self.manager = manager