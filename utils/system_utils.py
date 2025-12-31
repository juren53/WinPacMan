import subprocess
import shutil
import os
import platform
from typing import Optional, List, Tuple
from core.exceptions import PackageManagerNotAvailableError
from contextlib import contextmanager


class SystemUtils:
    """System utility functions for package manager operations"""
    
    @staticmethod
    def is_command_available(command: str) -> bool:
        """Check if a command is available in system PATH"""
        return shutil.which(command) is not None
    
    @staticmethod
    def get_command_version(command: str, version_arg: str = "--version") -> Optional[str]:
        """Get version of a command-line tool"""
        try:
            result = subprocess.run(
                [command, version_arg],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            output = result.stdout.strip() or result.stderr.strip()
            return output if output else None
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    @staticmethod
    def run_command(command: List[str], timeout: int = 60, shell: bool = False) -> Tuple[str, str, int]:
        """Run a command and return stdout, stderr, and exit code"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=shell
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as e:
            return "", f"Command timed out after {timeout} seconds", 1
        except Exception as e:
            return "", str(e), 1
    
    @staticmethod
    def check_admin_privileges() -> bool:
        """Check if the current process has administrator privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    @staticmethod
    def get_system_info() -> dict:
        """Get basic system information"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "is_admin": SystemUtils.check_admin_privileges()
        }
    
    @staticmethod
    def validate_package_manager(manager_name: str, command: str) -> Tuple[bool, str]:
        """Validate that a package manager is available and working"""
        # Check if command exists
        if not SystemUtils.is_command_available(command):
            return False, f"Command '{command}' not found in PATH"
        
        # Try to get version
        version = SystemUtils.get_command_version(command)
        if not version:
            return False, f"Could not get version for '{command}'"
        
        return True, version
    
    @staticmethod
    def elevate_privileges(command: List[str]) -> bool:
        """Attempt to run command with elevated privileges (Windows only)"""
        if platform.system() == "Windows":
            try:
                import ctypes
                return ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", command[0], " ".join(command[1:]), None, 1
                ) > 32
            except Exception:
                return False
        else:
            # On Unix-like systems, the user should use sudo manually
            return False


class PathManager:
    """Manage paths for WinPacMan application"""
    
    def __init__(self):
        self.app_data_dir = os.path.expanduser("~/.winpacman")
        self.temp_dir = os.path.join(self.app_data_dir, "temp")
        self.logs_dir = os.path.join(self.app_data_dir, "logs")
        
        # Ensure directories exist
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
    
    def get_temp_file(self, filename: str) -> str:
        """Get path to a temporary file"""
        return os.path.join(self.temp_dir, filename)
    
    def get_log_file(self, filename: str) -> str:
        """Get path to a log file"""
        return os.path.join(self.logs_dir, filename)
    
    def cleanup_temp(self) -> int:
        """Clean up temporary files"""
        removed = 0
        try:
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    removed += 1
        except Exception:
            pass
        return removed


class WindowsPowerManager:
    """
    Manage Windows power settings to prevent sleep during long operations.

    Uses SetThreadExecutionState Windows API to temporarily prevent the system
    from going to sleep or turning off the display during cache refreshes and
    package installations.
    """

    # Windows API constants for SetThreadExecutionState
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_AWAYMODE_REQUIRED = 0x00000040

    @staticmethod
    @contextmanager
    def prevent_sleep(prevent_display_sleep: bool = False):
        """
        Context manager to prevent Windows from sleeping during an operation.

        Usage:
            with WindowsPowerManager.prevent_sleep():
                # Long-running operation here
                download_packages()

        Args:
            prevent_display_sleep: If True, also prevents display from turning off

        Yields:
            None
        """
        if platform.system() != "Windows":
            # Non-Windows systems - just yield without doing anything
            yield
            return

        try:
            import ctypes

            # Set flags to prevent sleep
            flags = WindowsPowerManager.ES_CONTINUOUS | WindowsPowerManager.ES_SYSTEM_REQUIRED

            if prevent_display_sleep:
                flags |= WindowsPowerManager.ES_DISPLAY_REQUIRED

            # Prevent system sleep
            previous_state = ctypes.windll.kernel32.SetThreadExecutionState(flags)

            print(f"[PowerManager] System sleep prevention enabled (flags: 0x{flags:X})")

            try:
                yield
            finally:
                # Restore previous power state
                ctypes.windll.kernel32.SetThreadExecutionState(WindowsPowerManager.ES_CONTINUOUS)
                print("[PowerManager] System sleep prevention disabled")

        except Exception as e:
            # If power management fails, just log and continue
            print(f"[PowerManager] Failed to set power state: {e}")
            yield