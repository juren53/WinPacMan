import json
import os
from pathlib import Path

try:
    from xdg_base_dirs import xdg_config_home, xdg_data_home, xdg_cache_home
except ImportError:
    # Fallback to default paths if xdg-base-dirs is not available
    import platform
    home = Path.home()
    
    def xdg_config_home():
        return os.environ.get('XDG_CONFIG_HOME') or (home / '.config')
    
    def xdg_data_home():
        return os.environ.get('XDG_DATA_HOME') or (home / '.local' / 'share')
    
    def xdg_cache_home():
        return os.environ.get('XDG_CACHE_HOME') or (home / '.cache')


class ConfigManager:
    """XDG-compliant configuration management for WinPacMan"""
    
    def __init__(self):
        self.app_name = "winpacman"
        self.config_dir = Path(xdg_config_home()) / self.app_name
        self.data_dir = Path(xdg_data_home()) / self.app_name
        self.cache_dir = Path(xdg_cache_home()) / self.app_name
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / "config.json"
        self.default_config = {
            "ui": {
                "theme": "default",
                "window_state": {
                    "maximized": False,
                    "geometry": None,
                    "width": 1000,
                    "height": 700
                }
            },
            "package_managers": {
                "winget": {
                    "enabled": True,
                    "path": "winget",
                    "auto_update": False
                },
                "chocolatey": {
                    "enabled": True,
                    "path": "choco",
                    "auto_update": False
                },
                "pip": {
                    "enabled": True,
                    "path": "pip",
                    "auto_update": False
                },
                "npm": {
                    "enabled": True,
                    "path": "npm",
                    "auto_update": False
                }
            },
            "advanced": {
                "auto_refresh": True,
                "cache_duration": 3600,
                "max_concurrent_operations": 3,
                "log_level": "INFO"
            }
        }
    
    def load_config(self) -> dict:
        """Load configuration from file, merging with defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with defaults to handle new settings
                return self._merge_configs(self.default_config, config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                return self.default_config.copy()
        else:
            self.save_config(self.default_config)
            return self.default_config.copy()
    
    def save_config(self, config: dict):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")
    
    def _merge_configs(self, default: dict, user: dict) -> dict:
        """Deep merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get_config_value(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'ui.theme')"""
        config = self.load_config()
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_config_value(self, key_path: str, value):
        """Set configuration value using dot notation"""
        config = self.load_config()
        keys = key_path.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the final value
        current[keys[-1]] = value
        self.save_config(config)
    
    def get_data_file_path(self, filename: str) -> Path:
        """Get path to a data file"""
        return self.data_dir / filename
    
    def get_cache_file_path(self, filename: str) -> Path:
        """Get path to a cache file"""
        return self.cache_dir / filename
    
    def clear_cache(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob('*'):
            if cache_file.is_file():
                cache_file.unlink()
    
    def reset_config(self):
        """Reset configuration to defaults"""
        self.save_config(self.default_config.copy())


# Global configuration instance
config_manager = ConfigManager()