"""
Simple Tkinter-based UI for WinPacMan.

This provides a basic GUI while we resolve PyQt6 installation issues.
Can be replaced with PyQt6 implementation later.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from typing import List, Optional
from services.package_service import PackageManagerService, PackageOperationWorker
from services.settings_service import SettingsService
from core.models import PackageManager, Package, PackageStatus
from core.config import config_manager


class WinPacManGUI:
    """Simple Tkinter GUI for WinPacMan"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.package_service = PackageManagerService()
        self.settings_service = SettingsService()
        
        self.setup_window()
        self.setup_ui()
        self.setup_variables()
        
    def setup_window(self):
        """Setup main window properties"""
        self.root.title("WinPacMan - Windows Package Manager")
        self.root.geometry("1000x700")
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap("resources/icon.ico")
        except:
            pass  # No icon available
    
    def setup_variables(self):
        """Setup UI variables"""
        self.current_packages = []
        self.operation_in_progress = False
        self.selected_manager = tk.StringVar(value="winget")
        
    def setup_ui(self):
        """Setup main UI components"""
        # Create main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="WinPacMan - Windows Package Manager", 
            font=('Arial', 16, 'bold')
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Control panel
        self.setup_control_panel(main_frame)
        
        # Package list
        self.setup_package_list(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
        
    def setup_control_panel(self, parent):
        """Setup control panel"""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Package manager selection
        ttk.Label(control_frame, text="Package Manager:").grid(row=0, column=0, sticky=tk.W)
        manager_combo = ttk.Combobox(
            control_frame, 
            textvariable=self.selected_manager,
            values=["winget", "choco", "pip", "npm"],
            state="readonly"
        )
        manager_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        # Buttons
        self.refresh_btn = ttk.Button(
            control_frame, 
            text="Refresh Packages", 
            command=self.refresh_packages
        )
        self.refresh_btn.grid(row=0, column=2, padx=(20, 10))
        
        self.search_btn = ttk.Button(
            control_frame, 
            text="Search", 
            command=self.search_packages
        )
        self.search_btn.grid(row=0, column=3, padx=5)
        
        self.install_btn = ttk.Button(
            control_frame, 
            text="Install", 
            command=self.install_package
        )
        self.install_btn.grid(row=0, column=4, padx=5)
        
        self.uninstall_btn = ttk.Button(
            control_frame, 
            text="Uninstall", 
            command=self.uninstall_package
        )
        self.uninstall_btn.grid(row=0, column=5, padx=5)
        
        # Configure column weights
        control_frame.columnconfigure(1, weight=1)
    
    def setup_package_list(self, parent):
        """Setup package list display"""
        list_frame = ttk.LabelFrame(parent, text="Installed Packages", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create Treeview for package list
        columns = ('Name', 'Version', 'Manager', 'Description')
        self.package_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Define headings
        self.package_tree.heading('Name', text='Package Name')
        self.package_tree.heading('Version', text='Version')
        self.package_tree.heading('Manager', text='Manager')
        self.package_tree.heading('Description', text='Description')
        
        # Configure column widths
        self.package_tree.column('Name', width=300)
        self.package_tree.column('Version', width=100)
        self.package_tree.column('Manager', width=100)
        self.package_tree.column('Description', width=400)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.package_tree.yview)
        self.package_tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.package_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Bind double-click for package details
        self.package_tree.bind('<Double-Button-1>', self.on_package_double_click)
    
    def setup_status_bar(self, parent):
        """Setup status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame, 
            mode='determinate',
            variable=self.progress_var,
            length=200
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_bar.pack_forget()  # Hide initially
    
    def refresh_packages(self):
        """Refresh package list from selected manager"""
        if self.operation_in_progress:
            messagebox.showwarning("Busy", "Another operation is in progress. Please wait.")
            return
        
        manager_name = self.selected_manager.get()
        manager_map = {
            "winget": PackageManager.WINGET,
            "choco": PackageManager.CHOCOLATEY,
            "pip": PackageManager.PIP,
            "npm": PackageManager.NPM
        }
        
        if manager_name not in manager_map:
            messagebox.showerror("Error", "Invalid package manager selected.")
            return
        
        manager = manager_map[manager_name]
        
        # Start operation in background thread
        self.start_operation(f"Refreshing packages from {manager_name}...")
        
        worker = PackageOperationWorker(
            self.package_service.get_installed_packages,
            manager,
            self.update_progress
        )
        worker.start()
        
        # Schedule completion check
        self.root.after(100, lambda: self.check_operation_completion(worker))
    
    def update_progress(self, current, total, message):
        """Update progress bar and status"""
        self.root.after(0, lambda: self._update_progress_ui(current, total, message))
    
    def _update_progress_ui(self, current, total, message):
        """Update progress UI (called from main thread)"""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
            self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.status_label.config(text=message)
    
    def start_operation(self, message):
        """Start an operation"""
        self.operation_in_progress = True
        self.disable_buttons()
        self.status_label.config(text=message)
        self.progress_var.set(0)
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
    
    def end_operation(self):
        """End an operation"""
        self.operation_in_progress = False
        self.enable_buttons()
        self.status_label.config(text="Ready")
        self.progress_var.set(0)
        self.progress_bar.pack_forget()
    
    def disable_buttons(self):
        """Disable all control buttons"""
        self.refresh_btn.config(state='disabled')
        self.search_btn.config(state='disabled')
        self.install_btn.config(state='disabled')
        self.uninstall_btn.config(state='disabled')
    
    def enable_buttons(self):
        """Enable all control buttons"""
        self.refresh_btn.config(state='normal')
        self.search_btn.config(state='normal')
        self.install_btn.config(state='normal')
        self.uninstall_btn.config(state='normal')
    
    def check_operation_completion(self, worker):
        """Check if background operation is complete"""
        if worker.is_alive():
            # Still running, check again later
            self.root.after(100, lambda: self.check_operation_completion(worker))
        else:
            # Operation completed
            self.root.after(0, lambda: self.handle_operation_completion(worker))
    
    def handle_operation_completion(self, worker):
        """Handle completed operation"""
        if worker.error:
            messagebox.showerror("Error", f"Operation failed: {worker.error}")
        elif worker.result:
            self.current_packages = worker.result
            self.update_package_list()
            messagebox.showinfo("Success", f"Found {len(worker.result)} packages")
        
        self.end_operation()
    
    def update_package_list(self):
        """Update the package list in the UI"""
        # Clear existing items
        for item in self.package_tree.get_children():
            self.package_tree.delete(item)
        
        # Add packages
        for package in self.current_packages:
            self.package_tree.insert(
                '', 
                'end', 
                values=(
                    package.name, 
                    package.version, 
                    package.manager.value,
                    package.description or ""
                ),
                tags=(package.manager.value,)
            )
        
        # Configure tags for different package managers
        self.package_tree.tag_configure('winget', background='#E8F5E8')
        self.package_tree.tag_configure('chocolatey', background='#FFF4E6')
        self.package_tree.tag_configure('pip', background='#E6F3FF')
        self.package_tree.tag_configure('npm', background='#FCE6F3')
    
    def on_package_double_click(self, event):
        """Handle double-click on package"""
        selection = self.package_tree.selection()
        if selection:
            item = self.package_tree.item(selection[0])
            values = item['values']
            if values:
                messagebox.showinfo(
                    "Package Details",
                    f"Name: {values[0]}\nVersion: {values[1]}\nManager: {values[2]}"
                )
    
    def search_packages(self):
        """Search for packages (placeholder)"""
        messagebox.showinfo("Search", "Search functionality not yet implemented in GUI")
    
    def install_package(self):
        """Install a package (placeholder)"""
        messagebox.showinfo("Install", "Install functionality not yet implemented in GUI")
    
    def uninstall_package(self):
        """Uninstall a package (placeholder)"""
        messagebox.showinfo("Uninstall", "Uninstall functionality not yet implemented in GUI")
    
    def run(self):
        """Start the GUI application"""
        # Initial package list refresh
        self.root.after(1000, self.refresh_packages)
        
        # Start the main loop
        self.root.mainloop()


def main():
    """Main entry point for GUI application"""
    try:
        app = WinPacManGUI()
        app.run()
    except KeyboardInterrupt:
        print("Application interrupted by user")
    except Exception as e:
        messagebox.showerror("Fatal Error", f"An error occurred: {e}")


if __name__ == "__main__":
    main()