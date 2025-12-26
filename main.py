"""
Main entry point for WinPacMan Application.

Currently provides a console interface for testing core functionality.
GUI components will be added once PyQt6 installation is resolved.
"""

import sys
import argparse
from typing import List
from core.config import config_manager
from core.models import Package, PackageManager, PackageStatus
from utils.system_utils import SystemUtils
from services.package_service import PackageManagerService, PackageOperationWorker
from services.settings_service import SettingsService


class WinPacManConsole:
    """Console interface for WinPacMan"""
    
    def __init__(self):
        self.config = config_manager.load_config()
        self.settings_service = SettingsService()
        self.system_utils = SystemUtils()
        self.package_service = PackageManagerService()
        
    def display_welcome(self):
        """Display welcome message"""
        print("=" * 60)
        print("Welcome to WinPacMan - Windows Package Manager")
        print("=" * 60)
        print()
    
    def display_system_info(self):
        """Display system information"""
        info = self.system_utils.get_system_info()
        print("System Information:")
        print(f"  Platform: {info['platform']} {info['platform_release']}")
        print(f"  Architecture: {info['architecture']}")
        print(f"  Python: {info['python_version']}")
        print(f"  Admin privileges: {info['is_admin']}")
        print()
    
    def check_package_managers(self):
        """Check available package managers"""
        print("Package Manager Status:")
        
        managers = {
            "WinGet": "winget",
            "Chocolatey": "choco",
            "Pip": "pip",
            "NPM": "npm"
        }
        
        available_managers = []
        for name, command in managers.items():
            available, version = self.system_utils.validate_package_manager(name.lower(), command)
            status = "[OK] Available" if available else "[X] Not Available"
            version_info = f" ({version})" if version else ""
            print(f"  {name:12} {status}{version_info}")
            
            if available:
                available_managers.append(name.lower())
        
        print()
        return available_managers
    
    def test_basic_functionality(self):
        """Test basic functionality of available package managers"""
        print("Testing Basic Functionality:")
        print("-" * 30)
        
        # Test WinGet if available
        if self.system_utils.is_command_available("winget"):
            print("\nTesting WinGet...")
            stdout, stderr, exit_code = self.system_utils.run_command(["winget", "list"], timeout=30)
            if exit_code == 0:
                lines = stdout.splitlines()
                # Count packages (skip header lines)
                package_lines = [line for line in lines[3:] if line.strip() and len(line.split()) >= 3]
                print(f"  Found {len(package_lines)} installed packages")
                
                # Show first few packages as example
                if package_lines:
                    print("  Sample packages:")
                    for i, line in enumerate(package_lines[:5]):
                        parts = line.split()
                        if len(parts) >= 3:
                            print(f"    - {parts[0]} ({parts[2]})")
            else:
                print(f"  Error: {stderr}")
        
        # Test Chocolatey if available
        if self.system_utils.is_command_available("choco"):
            print("\nTesting Chocolatey...")
            stdout, stderr, exit_code = self.system_utils.run_command(["choco", "list", "--local-only"], timeout=30)
            if exit_code == 0:
                lines = stdout.splitlines()
                # Count packages (skip header and summary lines)
                package_lines = [line for line in lines[1:] if line.strip() and not line.startswith("packages installed")]
                print(f"  Found {len(package_lines)} installed packages")
                
                # Show first few packages
                if package_lines:
                    print("  Sample packages:")
                    for i, line in enumerate(package_lines[:5]):
                        parts = line.split()
                        if len(parts) >= 2:
                            print(f"    - {parts[0]} ({parts[1]})")
            else:
                print(f"  Error: {stderr}")
    
    def display_config(self):
        """Display current configuration"""
        print("Current Configuration:")
        print(f"  Auto-refresh: {self.config['advanced']['auto_refresh']}")
        print(f"  Cache duration: {self.config['advanced']['cache_duration']} seconds")
        print(f"  Max concurrent operations: {self.config['advanced']['max_concurrent_operations']}")
        print(f"  Log level: {self.config['advanced']['log_level']}")
        print()
        
        print("Package Managers:")
        for name, settings in self.config['package_managers'].items():
            status = "Enabled" if settings['enabled'] else "Disabled"
            print(f"  {name:12} {status:8} (command: {settings['path']})")
        print()
    
    def interactive_mode(self):
        """Run in interactive mode"""
        self.display_welcome()
        self.display_system_info()
        
        available_managers = self.check_package_managers()
        
        if available_managers:
            self.test_basic_functionality()
        else:
            print("No package managers are available. Please install WinGet or Chocolatey.")
        
        self.display_config()
        
        print("Interactive mode is not yet implemented.")
        print("Use command-line options to test specific functionality.")
    
    def run_command(self, command: str, args: List[str]):
        """Run specific command"""
        if command == "list":
            self.list_packages(args)
        elif command == "search":
            self.search_packages(args)
        elif command == "config":
            self.show_config()
        elif command == "info":
            self.show_system_info()
        elif command == "test-threading":
            self.test_threading()
        else:
            print(f"Unknown command: {command}")
            self.show_help()
    
    def list_packages(self, args: List[str]):
        """List installed packages"""
        manager_name = args[0] if args else "winget"
        
        try:
            manager_map = {
                "winget": PackageManager.WINGET,
                "choco": PackageManager.CHOCOLATEY,
                "pip": PackageManager.PIP,
                "npm": PackageManager.NPM
            }
            
            if manager_name not in manager_map:
                print(f"Unknown package manager: {manager_name}")
                print("Available managers: winget, choco, pip, npm")
                return
            
            manager = manager_map[manager_name]
            
            print(f"Listing packages from {manager_name}...")
            
            def progress_callback(current, total, message):
                if current == 0:
                    print(f"  {message}")
                elif current == total:
                    print(f"  {message}")
            
            packages = self.package_service.get_installed_packages(manager, progress_callback)
            
            print(f"\nFound {len(packages)} packages:")
            print("-" * 80)
            for pkg in packages[:20]:  # Show first 20 packages
                print(f"{pkg.name:30} {pkg.version:15} {pkg.manager.value}")
            
            if len(packages) > 20:
                print(f"... and {len(packages) - 20} more packages")
                
        except Exception as e:
            print(f"Error: {e}")
    
    def search_packages(self, args: List[str]):
        """Search for packages"""
        if len(args) < 2:
            print("Usage: search <manager> <query>")
            return
        
        manager = args[0]
        query = args[1]
        
        if not self.system_utils.is_command_available(manager):
            print(f"Package manager '{manager}' is not available")
            return
        
        print(f"Searching for '{query}' using {manager}...")
        
        # Basic search commands (will be enhanced later)
        search_commands = {
            "winget": ["winget", "search", query],
            "choco": ["choco", "search", query]
        }
        
        if manager in search_commands:
            stdout, stderr, exit_code = self.system_utils.run_command(
                search_commands[manager], timeout=60
            )
            
            if exit_code == 0:
                print(stdout)
            else:
                print(f"Error: {stderr}")
        else:
            print(f"Search not yet implemented for {manager}")
    
    def show_config(self):
        """Show configuration"""
        self.display_config()
    
    def show_system_info(self):
        """Show system information"""
        self.display_welcome()
        self.display_system_info()
        self.check_package_managers()
    
    def test_threading(self):
        """Test threading functionality"""
        print("Testing Threading Functionality:")
        print("-" * 40)
        
        try:
            # Test concurrent package listing
            print("Starting concurrent package listing...")
            
            workers = []
            for manager in [PackageManager.WINGET, PackageManager.CHOCOLATEY]:
                worker = PackageOperationWorker(
                    self.package_service.get_installed_packages,
                    manager,
                    lambda current, total, msg: print(f"  {manager.value}: {msg}")
                )
                worker.start()
                workers.append(worker)
            
            # Wait for all workers to complete
            for worker in workers:
                worker.join(timeout=60)
                if worker.error:
                    print(f"Error: {worker.error}")
                elif worker.result:
                    print(f"  {len(worker.result)} packages found")
            
            print("Threading test completed successfully!")
            
        except Exception as e:
            print(f"Threading test failed: {e}")
    
    def show_help(self):
        """Show help information"""
        print("WinPacMan - Windows Package Manager")
        print()
        print("Usage:")
        print("  python main.py                    # Interactive mode")
        print("  python main.py <command> [args]   # Run specific command")
        print()
        print("Commands:")
        print("  list <manager>     List installed packages")
        print("  search <manager> <query>    Search for packages")
        print("  config              Show configuration")
        print("  info                Show system information")
        print("  test-threading     Test threading functionality")
        print("  help                Show this help message")
        print()
        print("Supported managers: winget, choco, pip, npm")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WinPacMan - Windows Package Manager")
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    
    args = parser.parse_args()
    
    app = WinPacManConsole()
    
    if args.command:
        app.run_command(args.command, args.args)
    else:
        app.interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)