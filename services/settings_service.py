from typing import Dict, Any, Optional
from core.config import config_manager


class SettingsService:
    """Service for managing application settings"""
    
    def __init__(self):
        self.config_manager = config_manager
        self._config = None
    
    def _get_config(self) -> Dict[str, Any]:
        """Get current configuration with caching"""
        if self._config is None:
            self._config = self.config_manager.load_config()
        return self._config
    
    def _save_config(self):
        """Save configuration to file"""
        if self._config is not None:
            self.config_manager.save_config(self._config)
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """Get a setting value using dot notation"""
        return self.config_manager.get_config_value(key_path, default)
    
    def set_setting(self, key_path: str, value: Any):
        """Set a setting value using dot notation"""
        self.config_manager.set_config_value(key_path, value)
        self._config = None  # Clear cache
    
    def is_package_manager_enabled(self, manager: str) -> bool:
        """Check if a package manager is enabled"""
        return self.get_setting(f"package_managers.{manager}.enabled", True)
    
    def enable_package_manager(self, manager: str, enabled: bool = True):
        """Enable or disable a package manager"""
        self.set_setting(f"package_managers.{manager}.enabled", enabled)
    
    def get_package_manager_path(self, manager: str) -> str:
        """Get the command path for a package manager"""
        return self.get_setting(f"package_managers.{manager}.path", manager)
    
    def set_package_manager_path(self, manager: str, path: str):
        """Set the command path for a package manager"""
        self.set_setting(f"package_managers.{manager}.path", path)
    
    def get_ui_setting(self, setting: str, default: Any = None) -> Any:
        """Get UI setting"""
        return self.get_setting(f"ui.{setting}", default)
    
    def set_ui_setting(self, setting: str, value: Any):
        """Set UI setting"""
        self.set_setting(f"ui.{setting}", value)
    
    def get_advanced_setting(self, setting: str, default: Any = None) -> Any:
        """Get advanced setting"""
        return self.get_setting(f"advanced.{setting}", default)
    
    def set_advanced_setting(self, setting: str, value: Any):
        """Set advanced setting"""
        self.set_setting(f"advanced.{setting}", value)
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.config_manager.reset_config()
        self._config = None
    
    def export_settings(self) -> Dict[str, Any]:
        """Export current settings"""
        return self._get_config()
    
    def import_settings(self, settings: Dict[str, Any]):
        """Import settings"""
        self._config = settings
        self._save_config()
    
    def get_window_state(self) -> Dict[str, Any]:
        """Get window state settings"""
        return self.get_ui_setting("window_state", {})
    
    def set_window_state(self, state: Dict[str, Any]):
        """Set window state settings"""
        self.set_ui_setting("window_state", state)
    
    def get_theme(self) -> str:
        """Get current theme"""
        return self.get_ui_setting("theme", "default")
    
    def set_theme(self, theme: str):
        """Set current theme"""
        self.set_ui_setting("theme", theme)
    
    def get_auto_refresh(self) -> bool:
        """Get auto refresh setting"""
        return self.get_advanced_setting("auto_refresh", True)
    
    def set_auto_refresh(self, auto_refresh: bool):
        """Set auto refresh setting"""
        self.set_advanced_setting("auto_refresh", auto_refresh)
    
    def get_cache_duration(self) -> int:
        """Get cache duration in seconds"""
        return self.get_advanced_setting("cache_duration", 3600)
    
    def set_cache_duration(self, duration: int):
        """Set cache duration in seconds"""
        self.set_advanced_setting("cache_duration", duration)
    
    def get_max_concurrent_operations(self) -> int:
        """Get maximum concurrent operations"""
        return self.get_advanced_setting("max_concurrent_operations", 3)
    
    def set_max_concurrent_operations(self, max_ops: int):
        """Set maximum concurrent operations"""
        self.set_advanced_setting("max_concurrent_operations", max_ops)
    
    def get_log_level(self) -> str:
        """Get log level"""
        return self.get_advanced_setting("log_level", "INFO")
    
    def set_log_level(self, level: str):
        """Set log level"""
        self.set_advanced_setting("log_level", level)