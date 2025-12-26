import subprocess
import re
import json
import threading
import time
from typing import List, Optional, Callable, Dict, Any
from core.models import Package, PackageManager, PackageStatus, OperationProgress, OperationResult
from core.exceptions import (
    PackageManagerNotAvailableError, 
    OperationFailedError, 
    TimeoutError,
    PackageNotFoundError
)
from utils.system_utils import SystemUtils


class PackageManagerService:
    """Service for managing package operations with multiple package managers"""
    
    def __init__(self):
        self.system_utils = SystemUtils()
        self.operations = {}  # Track ongoing operations
        self.progress_callbacks = {}  # Progress callbacks for operations
        
    def get_installed_packages(self, manager: PackageManager, progress_callback: Optional[Callable] = None) -> List[Package]:
        """Get installed packages from specified manager"""
        if manager == PackageManager.WINGET:
            return self._get_winget_installed(progress_callback)
        elif manager == PackageManager.CHOCOLATEY:
            return self._get_chocolatey_installed(progress_callback)
        elif manager == PackageManager.PIP:
            return self._get_pip_installed(progress_callback)
        elif manager == PackageManager.NPM:
            return self._get_npm_installed(progress_callback)
        else:
            raise PackageManagerNotAvailableError(manager.value)
    
    def _get_winget_installed(self, progress_callback: Optional[Callable] = None) -> List[Package]:
        """Get installed packages from WinGet with improved parsing"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Getting package list from WinGet...")
            
            # Use --accept-source-agreements to avoid prompts
            result = subprocess.run(
                ['winget', 'list', '--accept-source-agreements'], 
                capture_output=True, 
                text=True, 
                timeout=60,
                encoding='utf-8',
                errors='ignore'
            )
            
            if progress_callback:
                progress_callback(50, 100, "Parsing package list...")
            
            packages = []
            lines = result.stdout.splitlines()
            
            # Skip header lines - WinGet typically has 2-3 header lines
            data_start = 0
            for i, line in enumerate(lines):
                if line.strip() and 'Name' in line and 'Id' in line:
                    data_start = i + 1
                    break
            
            for line in lines[data_start:]:
                if line.strip():
                    package = self._parse_winget_line(line)
                    if package:
                        packages.append(package)
            
            if progress_callback:
                progress_callback(100, 100, f"Found {len(packages)} packages")
            
            return packages
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("list", 60, "WinGet")
        except FileNotFoundError:
            raise PackageManagerNotAvailableError(
                "WinGet",
                "WinGet is built into Windows 11. For Windows 10, install from Microsoft Store"
            )
        except subprocess.CalledProcessError as e:
            raise OperationFailedError("list", "WinGet", str(e))
    
    def _parse_winget_line(self, line: str) -> Optional[Package]:
        """Parse a single line from WinGet output"""
        try:
            # Handle encoding issues by replacing problematic characters
            clean_line = line.strip()
            if not clean_line:
                return None
            
            # WinGet output format: Name | Id | Version | Available | Source
            # Use regex to split on multiple spaces while preserving package names with spaces
            parts = re.split(r'\s{2,}', clean_line)
            
            if len(parts) >= 3:
                name = parts[0].strip()
                package_id = parts[1].strip() if len(parts) > 1 else name
                version = parts[2].strip() if len(parts) > 2 else "Unknown"
                
                # Skip if name or version are missing or contain control characters
                if not name or not version or any(c in name for c in ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05']):
                    return None
                
                return Package(
                    name=name,
                    id=package_id,
                    version=version,
                    manager=PackageManager.WINGET,
                    status=PackageStatus.INSTALLED
                )
        except Exception:
            # Skip lines that can't be parsed
            pass
        
        return None
    
    def _get_chocolatey_installed(self, progress_callback: Optional[Callable] = None) -> List[Package]:
        """Get installed packages from Chocolatey"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Getting package list from Chocolatey...")
            
            result = subprocess.run(
                ['choco', 'list'], 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if progress_callback:
                progress_callback(50, 100, "Parsing package list...")
            
            packages = []
            lines = result.stdout.splitlines()
            
            for line in lines[1:]:  # Skip header line
                clean_line = line.strip()
                if clean_line and 'packages installed' not in clean_line.lower():
                    # Parse chocolatey output: package_name version
                    parts = clean_line.split()
                    if len(parts) >= 2 and len(parts[0]) > 1:
                        name = parts[0]
                        version = parts[1]
                        
                        packages.append(Package(
                            name=name,
                            id=name,
                            version=version,
                            manager=PackageManager.CHOCOLATEY,
                            status=PackageStatus.INSTALLED
                        ))
            
            if progress_callback:
                progress_callback(100, 100, f"Found {len(packages)} packages")
            
            return packages
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("list", 60, "Chocolatey")
        except FileNotFoundError:
            raise PackageManagerNotAvailableError(
                "Chocolatey",
                "Install from https://chocolatey.org/install"
            )
        except subprocess.CalledProcessError as e:
            raise OperationFailedError("list", "Chocolatey", str(e))
    
    def _get_pip_installed(self, progress_callback: Optional[Callable] = None) -> List[Package]:
        """Get installed packages from Pip"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Getting package list from Pip...")
            
            result = subprocess.run(
                ['pip', 'list', '--format=json'], 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if progress_callback:
                progress_callback(50, 100, "Parsing package list...")

            packages_data = json.loads(result.stdout)
            packages = []
            
            for pkg in packages_data:
                packages.append(Package(
                    name=pkg['name'],
                    id=pkg['name'],
                    version=pkg['version'],
                    manager=PackageManager.PIP,
                    status=PackageStatus.INSTALLED
                ))
            
            if progress_callback:
                progress_callback(100, 100, f"Found {len(packages)} packages")
            
            return packages
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("list", 60, "Pip")
        except FileNotFoundError:
            raise PackageManagerNotAvailableError(
                "Pip",
                "Pip should be included with Python. Try 'python -m ensurepip' to install it"
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise OperationFailedError("list", "Pip", str(e))
    
    def _get_npm_installed(self, progress_callback: Optional[Callable] = None) -> List[Package]:
        """Get installed packages from NPM"""
        try:
            if progress_callback:
                progress_callback(0, 100, "Getting package list from NPM...")
            
            result = subprocess.run(
                ['npm', 'list', '-g', '--json', '--depth=0'], 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            if progress_callback:
                progress_callback(50, 100, "Parsing package list...")

            packages_data = json.loads(result.stdout)
            packages = []
            
            if 'dependencies' in packages_data:
                for name, info in packages_data['dependencies'].items():
                    packages.append(Package(
                        name=name,
                        id=name,
                        version=info.get('version', 'Unknown'),
                        manager=PackageManager.NPM,
                        status=PackageStatus.INSTALLED
                    ))
            
            if progress_callback:
                progress_callback(100, 100, f"Found {len(packages)} packages")
            
            return packages
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("list", 60, "NPM")
        except FileNotFoundError:
            raise PackageManagerNotAvailableError(
                "NPM",
                "Please install Node.js from https://nodejs.org to use NPM"
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            raise OperationFailedError("list", "NPM", str(e))
    
    def install_package(self, manager: PackageManager, package_id: str, 
                      progress_callback: Optional[Callable] = None) -> OperationResult:
        """Install a package using specified manager"""
        try:
            commands = {
                PackageManager.WINGET: ['winget', 'install', package_id, '--accept-package-agreements', '--accept-source-agreements'],
                PackageManager.CHOCOLATEY: ['choco', 'install', package_id, '-y'],
                PackageManager.PIP: ['pip', 'install', package_id],
                PackageManager.NPM: ['npm', 'install', '-g', package_id]
            }
            
            if manager not in commands:
                raise PackageManagerNotAvailableError(manager.value)
            
            if progress_callback:
                progress_callback(0, 100, f"Installing {package_id}...")
            
            result = subprocess.run(
                commands[manager],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            success = result.returncode == 0
            message = f"Successfully installed {package_id}" if success else f"Failed to install {package_id}: {result.stderr}"
            
            if progress_callback:
                progress_callback(100, 100, message)
            
            return OperationResult(
                operation="install",
                package=package_id,
                success=success,
                message=message,
                details={"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
            )
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("install", 300, package_id)
        except Exception as e:
            raise OperationFailedError("install", package_id, str(e))
    
    def uninstall_package(self, manager: PackageManager, package_id: str,
                        progress_callback: Optional[Callable] = None) -> OperationResult:
        """Uninstall a package using specified manager"""
        try:
            commands = {
                PackageManager.WINGET: ['winget', 'uninstall', package_id],
                PackageManager.CHOCOLATEY: ['choco', 'uninstall', package_id, '-y'],
                PackageManager.PIP: ['pip', 'uninstall', package_id, '-y'],
                PackageManager.NPM: ['npm', 'uninstall', '-g', package_id]
            }
            
            if manager not in commands:
                raise PackageManagerNotAvailableError(manager.value)
            
            if progress_callback:
                progress_callback(0, 100, f"Uninstalling {package_id}...")
            
            result = subprocess.run(
                commands[manager],
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            success = result.returncode == 0
            message = f"Successfully uninstalled {package_id}" if success else f"Failed to uninstall {package_id}: {result.stderr}"
            
            if progress_callback:
                progress_callback(100, 100, message)
            
            return OperationResult(
                operation="uninstall",
                package=package_id,
                success=success,
                message=message,
                details={"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
            )
            
        except subprocess.TimeoutExpired:
            raise TimeoutError("uninstall", 180, package_id)
        except Exception as e:
            raise OperationFailedError("uninstall", package_id, str(e))


class PackageOperationWorker:
    """Worker for running package operations in background threads"""
    
    def __init__(self, operation_func, *args, **kwargs):
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self.result = None
        self.error = None
        self.thread = None
        
    def start(self):
        """Start the operation in a background thread"""
        self.thread = threading.Thread(target=self._run)
        self.thread.start()
    
    def _run(self):
        """Run the operation"""
        try:
            self.result = self.operation_func(*self.args, **self.kwargs)
        except Exception as e:
            self.error = e
    
    def join(self, timeout=None):
        """Wait for the operation to complete"""
        if self.thread:
            return self.thread.join(timeout)
        return True
    
    def is_alive(self):
        """Check if the operation is still running"""
        return self.thread and self.thread.is_alive()