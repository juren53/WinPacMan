"""Package metadata providers."""

from .base import MetadataProvider
from .winget_provider import WinGetProvider
from .chocolatey_provider import ChocolateyProvider

__all__ = ['MetadataProvider', 'WinGetProvider', 'ChocolateyProvider']
