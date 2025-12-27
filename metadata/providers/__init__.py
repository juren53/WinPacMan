"""Package metadata providers."""

from .base import MetadataProvider
from .winget_provider import WinGetProvider

__all__ = ['MetadataProvider', 'WinGetProvider']
