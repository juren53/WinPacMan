"""Package metadata providers."""

from .base import MetadataProvider
from .winget_provider import WinGetProvider
from .chocolatey_provider import ChocolateyProvider
from .scoop_provider import ScoopProvider
from .installed_registry_provider import InstalledRegistryProvider, ScoopInstalledProvider

__all__ = [
    'MetadataProvider',
    'WinGetProvider',
    'ChocolateyProvider',
    'ScoopProvider',
    'InstalledRegistryProvider',
    'ScoopInstalledProvider'
]
