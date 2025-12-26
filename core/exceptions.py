"""
Custom exceptions for WinPacMan package management operations.

This module defines specific exception types used throughout the application
to handle different types of errors that can occur during package management.
"""


class PackageManagerError(Exception):
    """Base exception for all package manager operations"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(PackageManagerError):
    """Raised when there are configuration-related errors"""
    
    def __init__(self, message: str, config_key: str = None):
        super().__init__(message, "CONFIG_ERROR")
        self.config_key = config_key


class PackageNotFoundError(PackageManagerError):
    """Raised when a specific package cannot be found"""
    
    def __init__(self, package_id: str, manager: str = None):
        message = f"Package '{package_id}' not found"
        if manager:
            message += f" in {manager}"
        super().__init__(message, "PACKAGE_NOT_FOUND")
        self.package_id = package_id
        self.manager = manager


class OperationFailedError(PackageManagerError):
    """Raised when a package operation fails"""
    
    def __init__(self, operation: str, package: str, message: str, exit_code: int = None):
        full_message = f"{operation} failed for {package}: {message}"
        super().__init__(full_message, "OPERATION_FAILED")
        self.operation = operation
        self.package = package
        self.original_message = message
        self.exit_code = exit_code


class PackageManagerNotAvailableError(PackageManagerError):
    """Raised when a required package manager is not available"""
    
    def __init__(self, manager: str, suggestion: str = None):
        message = f"Package manager '{manager}' is not available"
        if suggestion:
            message += f". {suggestion}"
        super().__init__(message, "MANAGER_NOT_AVAILABLE")
        self.manager = manager
        self.suggestion = suggestion


class NetworkError(PackageManagerError):
    """Raised when network operations fail"""
    
    def __init__(self, operation: str, url: str = None, message: str = None):
        msg = f"Network error during {operation}"
        if message:
            msg += f": {message}"
        super().__init__(msg, "NETWORK_ERROR")
        self.operation = operation
        self.url = url
        self.original_message = message


class PermissionError(PackageManagerError):
    """Raised when insufficient permissions for operation"""
    
    def __init__(self, operation: str, resource: str = None):
        message = f"Insufficient permissions for {operation}"
        if resource:
            message += f" on {resource}"
        super().__init__(message, "PERMISSION_ERROR")
        self.operation = operation
        self.resource = resource


class ValidationError(PackageManagerError):
    """Raised when data validation fails"""
    
    def __init__(self, field: str, value: str, reason: str = None):
        message = f"Validation failed for field '{field}' with value '{value}'"
        if reason:
            message += f": {reason}"
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field
        self.value = value
        self.reason = reason


class CancellationError(PackageManagerError):
    """Raised when an operation is cancelled"""
    
    def __init__(self, operation: str, package: str = None):
        message = f"Operation cancelled"
        if operation:
            message += f" during {operation}"
        if package:
            message += f" for {package}"
        super().__init__(message, "OPERATION_CANCELLED")
        self.operation = operation
        self.package = package


class TimeoutError(PackageManagerError):
    """Raised when an operation times out"""
    
    def __init__(self, operation: str, timeout_seconds: int, package: str = None):
        message = f"Operation {operation} timed out after {timeout_seconds} seconds"
        if package:
            message += f" for {package}"
        super().__init__(message, "OPERATION_TIMEOUT")
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        self.package = package


class DependencyError(PackageManagerError):
    """Raised when package dependencies cannot be resolved"""
    
    def __init__(self, package: str, missing_deps: list = None):
        message = f"Dependency error for package '{package}'"
        if missing_deps:
            deps_str = ", ".join(missing_deps)
            message += f": missing dependencies [{deps_str}]"
        super().__init__(message, "DEPENDENCY_ERROR")
        self.package = package
        self.missing_deps = missing_deps or []


class CacheError(PackageManagerError):
    """Raised when cache operations fail"""
    
    def __init__(self, operation: str, cache_file: str = None, message: str = None):
        msg = f"Cache error during {operation}"
        if cache_file:
            msg += f" for file {cache_file}"
        if message:
            msg += f": {message}"
        super().__init__(msg, "CACHE_ERROR")
        self.operation = operation
        self.cache_file = cache_file
        self.original_message = message