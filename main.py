import os
import sys
import json
import logging
import paramiko
import threading
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
import customtkinter as ctk
from cryptography.fernet import Fernet
import re
import platform
import copy
import time
import socket
import pytermgui as ptg
import threading
import queue
import ctypes

class ModernSSHClient(paramiko.SSHClient):
    """A modern SSH client wrapper around paramiko.SSHClient."""
    
    def __init__(self):
        """Initialize the SSH client with auto-add policy."""
        super().__init__()
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None
        self.logger = logging.getLogger(__name__)
        self.terminal = ptg.Terminal()  # Initialize pytermgui Terminal
        
    def connect_ssh(self, host: str, username: str, password: str = None, 
                   key_filename: str = None, port: int = 22) -> bool:
        """Connect to SSH server with improved error handling."""
        try:
            self.connect(
                hostname=host,
                username=username,
                password=password,
                key_filename=key_filename,
                port=port,
                timeout=10
            )
            
            self.channel = self.invoke_shell()
            self.channel.settimeout(0.1)
            return True
            
        except Exception as e:
            self.logger.error(f"SSH connection failed: {str(e)}")
            return False

    def _process_terminal_output(self, data: str) -> str:
        """Process terminal output with improved ANSI escape sequence handling."""
        try:
            # Handle carriage returns and line feeds
            processed = data.replace('\r\n', '\n').replace('\r', '\n')
            
            # Handle backspace characters
            while '\b' in processed:
                idx = processed.find('\b')
                if idx > 0:  # Only remove previous character if it exists
                    processed = processed[:idx-1] + processed[idx+1:]
                else:
                    processed = processed[idx+1:]
            
            # Handle common terminal control sequences
            control_sequences = {
                '\x1b[K': '',     # Clear line
                '\x1b[2J': '',    # Clear screen
                '\x1b[J': '',     # Clear screen from cursor
                '\x1b[P': '',     # Delete character
                '\x1b[s': '',     # Save cursor position
                '\x1b[u': '',     # Restore cursor position
                '\x1b[?2004h': '', # Bracketed paste mode
                '\x1b[?2004l': '', # Exit bracketed paste mode
            }
            
            for seq, replacement in control_sequences.items():
                processed = processed.replace(seq, replacement)
            
            # Handle cursor movement sequences
            cursor_pattern = re.compile(r'\x1b\[(\d+)?([ABCDEFG])')
            processed = cursor_pattern.sub('', processed)
            
            self.terminal.print(processed)  # Use pytermgui to print processed data
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing terminal output: {e}")
            return data  # Return original data if processing fails

    def close(self):
        """Close SSH connection and cleanup."""
        try:
            if self.channel:
                self.channel.close()
            super().close()
        except:
            pass

class ModernSSHClientApp:
    def __init__(self, root: ctk.CTk) -> None:
        """Initialize the SSH client."""
        # Initialize logging first
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Get the directory where the script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set absolute paths for configuration files in the project directory
        self.preferences_file = os.path.join(script_dir, "preferences.json")
        self.session_file = os.path.join(script_dir, "sessions.json")
        
        self.root = root
        self.root.title("Modern SSH Client")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Initialize encryption key
        self.encryption_key = self.get_or_create_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Initialize preferences with defaults
        self.preferences = {
            "theme": "dark",
            "terminal_font_family": "Monospace",
            "terminal_font_size": 10
        }
        
        # Initialize themes
        self.themes = {
            "dark": {
                "bg": "#2B2B2B",
                "fg": "#FFFFFF",
                "button": "#404040",
                "button_hover": "#4A4A4A",
                "entry": "#404040",
                "terminal_bg": "#1E1E1E",
                "terminal_fg": "#FFFFFF"
            },
            "light": {
                "bg": "#F0F0F0",
                "fg": "#000000",
                "button": "#E0E0E0",
                "button_hover": "#D0D0D0",
                "entry": "#FFFFFF",
                "terminal_bg": "#FFFFFF",
                "terminal_fg": "#000000"
            }
        }
        
        # Load configuration first
        self.load_preferences()
        
        # Set initial theme from preferences or default
        self.current_theme = self.preferences.get('theme', 'dark')
        ctk.set_appearance_mode(self.current_theme)
        
        # Initialize all dictionaries and variables
        self.sessions = {}
        self.ssh_clients = {}
        self.terminal_frames = {}
        self.terminal_outputs = {}  # Dictionary to store terminal output widgets
        self.command_inputs = {}    # Dictionary to store command input widgets
        self.session_buttons = {}   # Dictionary to store session buttons
        self.command_history = {}
        self.history_position = {}
        self.active_channels = {}
        self.search_var = tk.StringVar()
        self.clear_buttons = {}     # Dictionary to store clear buttons
        self.command_running = {}   # Dictionary to track if command is running
        
        # Load configuration
        self.load_sessions()
        
        # Initialize UI components
        self.setup_ui()
        self.bind_shortcuts()
        
        self.logger.info("Application initialized successfully")

    def setup_logging(self) -> None:
        """Set up logging configuration."""
        try:
            # Create formatters
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                       datefmt='%Y-%m-%d %H:%M:%S')

            # Create file handlers
            file_handler = logging.FileHandler('ssh_client.log')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)

            paramiko_handler = logging.FileHandler('ssh_client_paramiko.log')
            paramiko_handler.setLevel(logging.WARNING)  # Set to WARNING to reduce noise
            paramiko_handler.setFormatter(formatter)

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            # Remove all existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            root_logger.addHandler(file_handler)

            # Configure paramiko logger
            paramiko_logger = logging.getLogger("paramiko")
            paramiko_logger.setLevel(logging.WARNING)
            # Remove any existing handlers
            for handler in paramiko_logger.handlers[:]:
                paramiko_logger.removeHandler(handler)
            paramiko_logger.addHandler(paramiko_handler)
            paramiko_logger.propagate = False  # Prevent propagation to root logger

        except Exception as e:
            # Create a file handler for the default logger to avoid console output
            try:
                default_logger = logging.getLogger("setup")
                default_logger.setLevel(logging.ERROR)
                error_handler = logging.FileHandler('ssh_client_error.log')
                error_handler.setFormatter(formatter)
                default_logger.addHandler(error_handler)
                default_logger.error(f"Error setting up logging: {e}")
            except:
                pass  # Suppress any errors during error logging

    def load_preferences(self) -> None:
        """Load preferences from file."""
        try:
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r') as f:
                    self.preferences.update(json.load(f))
                self.logger.info("Preferences loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading preferences: {e}")

    def save_preferences(self, force_update: bool = False):
        """
        Save preferences to file with optional forced update.
        
        Args:
            force_update (bool): Force update even if preferences haven't changed
        """
        try:
            # Prevent recursive calls
            if hasattr(self, '_preferences_saving'):
                return
            
            self._preferences_saving = True
            
            # Validate preferences before saving
            if not hasattr(self, 'preferences') or not isinstance(self.preferences, dict):
                self.preferences = {}
            
            # Ensure default values
            default_preferences = {
                "theme": "dark",
                "terminal_font_family": "Monospace",
                "terminal_font_size": 10
            }
            
            # Update preferences with defaults if missing
            for key, value in default_preferences.items():
                if key not in self.preferences:
                    self.preferences[key] = value
            
            # Ensure preferences directory exists
            os.makedirs(os.path.dirname(self.preferences_file), exist_ok=True)
            
            # Save preferences
            with open(self.preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=4)
            
            self.logger.info("Preferences saved successfully")
        
        except Exception as e:
            error_msg = f"Error saving preferences: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Preferences Error", error_msg)
        
        finally:
            # Always clear the saving flag
            if hasattr(self, '_preferences_saving'):
                delattr(self, '_preferences_saving')

    def load_sessions(self) -> None:
        """Load saved sessions from file."""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    self.sessions = json.load(f)
                self.logger.info("Sessions loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading sessions: {e}")

    def save_sessions(self) -> None:
        """Save sessions to file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=4)
            self.logger.info("Sessions saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving sessions: {e}")

    def setup_ui(self):
        """Set up the main UI components."""
        # Create menu and status bars
        self.create_menu_bar()
        self.create_status_bar()
        
        # Create main UI components
        self.create_main_ui()
        
        # Update session list
        self.update_session_list()

    def create_menu_bar(self) -> None:
        """Create the menu bar."""
        self.menubar = tk.Menu(self.root)
        self.root.configure(menu=self.menubar)  # Changed from config to configure
        
        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Session", command=self.new_session_dialog)
        file_menu.add_command(label="Import Sessions", command=self.import_sessions)
        file_menu.add_command(label="Export Sessions", command=self.export_sessions)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)  # Changed to on_closing

        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences", command=self.show_preferences)

        # View menu
        view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Dark Mode", command=lambda: self.apply_theme("dark"))
        theme_menu.add_command(label="Light Mode", command=lambda: self.apply_theme("light"))

        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)

    def create_status_bar(self) -> None:
        """Create the status bar."""
        self.status_frame = ctk.CTkFrame(self.root, height=25)
        self.status_frame.pack(side="bottom", fill="x")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Ready",
            anchor="w",
            font=("Helvetica", 12)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.pack(side="right", padx=5)
        self.progress_bar.set(0)

    def update_status(self, message: str) -> None:
        """Update the status bar message."""
        self.status_label.configure(text=message)
        self.root.update_idletasks()

    def create_main_ui(self) -> None:
        """Create the main user interface."""
        # Create main container
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True)

        # Create left sidebar for sessions
        self.create_session_sidebar()

        # Create right panel for terminals
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.pack(side="right", fill="both", expand=True)

        # Create tab view for terminals
        self.tab_view = ctk.CTkTabview(self.right_panel)
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)

        # Create welcome tab
        self.create_welcome_tab()

    def new_session_dialog(self) -> None:
        """Show dialog for creating a new session with SSH key selection."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("New Session")

        ctk.CTkLabel(dialog, text="Session Name:").grid(row=0, column=0, padx=10, pady=5)
        session_name_entry = ctk.CTkEntry(dialog)
        session_name_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(dialog, text="Host:").grid(row=1, column=0, padx=10, pady=5)
        host_entry = ctk.CTkEntry(dialog)
        host_entry.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(dialog, text="Port:").grid(row=2, column=0, padx=10, pady=5)
        port_entry = ctk.CTkEntry(dialog)
        port_entry.insert(0, "22")  # Default port
        port_entry.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkLabel(dialog, text="Username:").grid(row=3, column=0, padx=10, pady=5)
        username_entry = ctk.CTkEntry(dialog)
        username_entry.grid(row=3, column=1, padx=10, pady=5)

        ctk.CTkLabel(dialog, text="Password:").grid(row=4, column=0, padx=10, pady=5)
        password_entry = ctk.CTkEntry(dialog, show="*")
        password_entry.grid(row=4, column=1, padx=10, pady=5)

        ctk.CTkLabel(dialog, text="SSH Key:").grid(row=5, column=0, padx=10, pady=5)
        ssh_key_entry = ctk.CTkEntry(dialog)
        ssh_key_entry.grid(row=5, column=1, padx=10, pady=5)

        def browse_ssh_key():
            key_path = filedialog.askopenfilename(title="Select SSH Key", filetypes=[("SSH Key Files", "*.pem *.ppk *.key"), ("All Files", "*.*")])
            if key_path:
                ssh_key_entry.delete(0, tk.END)
                ssh_key_entry.insert(0, key_path)

        browse_button = ctk.CTkButton(dialog, text="Browse", command=browse_ssh_key)
        browse_button.grid(row=5, column=2, padx=10, pady=5)

        def save_session():
            session_name = session_name_entry.get()
            host = host_entry.get()
            port = port_entry.get()
            username = username_entry.get()
            password = password_entry.get()
            ssh_key_path = ssh_key_entry.get()
            # Save the session details including the SSH key path
            self.sessions[session_name] = {
                "host": host,
                "port": port,
                "username": username,
                "password": password,  # Store password securely
                "ssh_key_path": ssh_key_path
            }
            self.save_sessions()
            self.update_session_list()
            dialog.destroy()

        save_button = ctk.CTkButton(dialog, text="Save", command=save_session)
        save_button.grid(row=6, column=0, columnspan=3, pady=10)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def create_terminal_tab(self, session_name: str):
        """
        Create a new terminal tab for a specific SSH session.
        
        Args:
            session_name (str): Name of the SSH session
        """
        try:
            # Create a new tab in the tab view
            terminal_frame = self.tab_view.add(session_name)
            
            # Configure frame layout
            terminal_frame.grid_columnconfigure(0, weight=1)
            terminal_frame.grid_rowconfigure(1, weight=1)  # Row 1 is for terminal output
            
            # Create button frame at the top (row 0)
            button_frame = ctk.CTkFrame(terminal_frame)
            button_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
            
            # Create a frame for right-aligned buttons
            right_buttons = ctk.CTkFrame(button_frame)
            right_buttons.pack(side="right", fill="y")
            
            # Add Clear History button
            self._last_clear_click = 0
            def debounced_clear():
                if self.command_running.get(session_name, False):
                    return  # Don't clear if command is running
                current_time = time.time()
                if current_time - self._last_clear_click > 0.5:  # 500ms debounce
                    self._last_clear_click = current_time
                    self.clear_terminal_history(session_name)
            
            clear_btn = ctk.CTkButton(
                right_buttons,
                text="Clear History",
                command=debounced_clear,
                width=100
            )
            clear_btn.pack(side="left", padx=5)
            self.clear_buttons[session_name] = clear_btn  # Store reference to clear button
            
            # Initialize command running state
            self.command_running[session_name] = False

            # Add Disconnect button
            disconnect_btn = ctk.CTkButton(
                right_buttons,
                text="Disconnect",
                command=lambda: self.disconnect_session(session_name),
                width=100
            )
            disconnect_btn.pack(side="left", padx=5)
            
            # Create terminal output text widget (row 1)
            terminal_output = tk.Text(
                terminal_frame,
                wrap=tk.WORD,
                font=(
                    self.preferences.get("terminal_font_family", "Monospace"),
                    self.preferences.get("terminal_font_size", 10)
                ),
                bg=self.themes[self.current_theme]["terminal_bg"],
                fg=self.themes[self.current_theme]["terminal_fg"],
                insertbackground=self.themes[self.current_theme]["fg"]
            )
            terminal_output.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(
                terminal_frame,
                orient=tk.VERTICAL,
                command=terminal_output.yview
            )
            scrollbar.grid(row=1, column=1, sticky='ns')
            terminal_output.configure(yscrollcommand=scrollbar.set)
            
            # Configure tags for styling
            terminal_output.tag_configure('command', foreground='cyan', font=('Monospace', 10, 'bold'))
            terminal_output.tag_configure('error', foreground='red', font=('Monospace', 10, 'bold'))
            terminal_output.tag_configure('success', foreground='green')
            
            # Create command input widget (row 2)
            command_input = ctk.CTkEntry(
                terminal_frame,
                placeholder_text="Enter command...",
                height=30
            )
            command_input.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
            
            # Bind enter key to send command
            command_input.bind('<Return>', lambda event, name=session_name: self.send_command(name))
            
            # Bind Up and Down arrow keys for command history
            command_input.bind('<Up>', lambda event, name=session_name: self.history_up(name))
            command_input.bind('<Down>', lambda event, name=session_name: self.history_down(name))
            
            # Store references
            self.terminal_outputs[session_name] = terminal_output
            self.command_inputs[session_name] = command_input
            
            # Initialize command history
            self.command_history[session_name] = []
            self.history_position[session_name] = 0
            
            self.logger.debug(f"Terminal tab created for {session_name}")
            
        except Exception as e:
            self.logger.error(f"Error creating terminal tab for {session_name}: {str(e)}")
            messagebox.showerror("Error", f"Failed to create terminal tab: {str(e)}")

    def clear_terminal_history(self, session_name: str) -> None:
        """Clear only the terminal output display, keeping command history intact."""
        try:
            # Verify the session name is valid and a terminal output exists
            if session_name and session_name in self.terminal_outputs:
                terminal = self.terminal_outputs[session_name]
                
                # Ensure the terminal is a Text widget and can be modified
                if isinstance(terminal, tk.Text):
                    # Enable editing of the terminal
                    terminal.config(state=tk.NORMAL)
                    
                    # Clear all content
                    terminal.delete(1.0, tk.END)
                    
                    # Disable editing again
                    terminal.config(state=tk.DISABLED)
                    
                    self.logger.info(f"Terminal output cleared for session: {session_name}")
        except Exception as e:
            self.logger.error(f"Error clearing terminal output: {str(e)}")
            self.show_error(f"Failed to clear terminal output: {str(e)}")

    def create_session_sidebar(self):
        """Create the session sidebar."""
        # Create left panel with dynamic width
        self.left_panel = ctk.CTkFrame(self.main_container)
        self.left_panel.pack(side="left", fill="y", padx=5, pady=5)

        # Configure grid weights for dynamic resizing
        self.left_panel.grid_columnconfigure(0, weight=1)
        
        # Create header frame with dynamic width
        header_frame = ctk.CTkFrame(self.left_panel)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        # Configure header frame grid
        header_frame.grid_columnconfigure(0, weight=1)  # Title takes remaining space
        header_frame.grid_columnconfigure(1, weight=0)  # Add button fixed width
        
        # Add title with left alignment
        title_label = ctk.CTkLabel(
            header_frame,
            text="Sessions",
            font=("Helvetica", 16, "bold"),
            anchor="w"
        )
        title_label.grid(row=0, column=0, sticky="w", padx=5)
        
        # Add new session button
        add_button = ctk.CTkButton(
            header_frame,
            text="+",
            width=30,
            height=30,
            command=self.new_session_dialog,
            font=("Helvetica", 16, "bold")
        )
        add_button.grid(row=0, column=1, padx=5)
        
        # Create search frame
        search_frame = ctk.CTkFrame(self.left_panel)
        search_frame.pack(fill="x", padx=5, pady=5)
        
        # Configure search frame grid
        search_frame.grid_columnconfigure(0, weight=1)
        
        # Add search entry with dynamic width
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search sessions...",
            textvariable=self.search_var
        )
        self.search_entry.pack(fill="x", padx=5, pady=5)
        self.search_var.trace("w", self.filter_sessions)
        
        # Create scrollable frame for sessions with dynamic width
        self.session_frame = ctk.CTkScrollableFrame(
            self.left_panel,
            label_text="",
            width=250  # Default width
        )
        self.session_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def filter_sessions(self, *args) -> None:
        """Filter sessions based on search text."""
        try:
            search_text = self.search_var.get().lower()
            
            # Clear existing session buttons
            for button in self.session_buttons.values():
                button.destroy()
            self.session_buttons.clear()

            # Create buttons for matching sessions
            for session_name in self.sessions:
                if search_text in session_name.lower():
                    self.create_session_button(session_name)
            
            self.logger.debug(f"Filtered sessions with query: {search_text}")
            
        except Exception as e:
            self.logger.error(f"Error filtering sessions: {str(e)}")
            self.update_status("Error filtering sessions")

    def create_session_button(self, session_name: str) -> None:
        """Create a button for a session in the session list."""
        try:
            # Create frame for the session button and its controls
            session_frame = ctk.CTkFrame(
                self.session_frame,
                fg_color="transparent"
            )
            session_frame.pack(fill="x", padx=5, pady=2)
            
            # Configure grid weights for dynamic resizing
            session_frame.grid_columnconfigure(0, weight=1)  # Main button takes most space
            session_frame.grid_columnconfigure(1, weight=0)  # Edit button fixed width
            session_frame.grid_columnconfigure(2, weight=0)  # Delete button fixed width
            
            # Create the main session button
            button = ctk.CTkButton(
                session_frame,
                text=session_name,
                command=lambda sn=session_name: self.connect_to_session(sn),
                anchor="w"  # Align text to the left
            )
            button.grid(row=0, column=0, sticky="ew", padx=(0, 5))
            
            # Add edit button with fixed width
            edit_btn = ctk.CTkButton(
                session_frame,
                text="Edit",
                command=lambda sn=session_name: self.edit_session(sn),
                width=40
            )
            edit_btn.grid(row=0, column=1, padx=2)
            
            # Add delete button with fixed width and compact design
            delete_btn = ctk.CTkButton(
                session_frame,
                text="✖",
                command=lambda sn=session_name: self.delete_session(sn),
                width=30,
                height=30,
                fg_color="red",
                hover_color="darkred",
                text_color="white",
                font=("Helvetica", 12, "bold")
            )
            delete_btn.grid(row=0, column=2, padx=(2, 0))
            
            # Store button reference
            self.session_buttons[session_name] = session_frame
            
            self.logger.debug(f"Created session button for {session_name}")
            
        except Exception as e:
            self.logger.error(f"Error creating session button for {session_name}: {str(e)}")
            messagebox.showerror("Error", f"Failed to create session button: {str(e)}")

    def connect_to_session(self, session_name: str):
        """
        Initiate SSH connection for a given session with comprehensive error handling.
        
        Args:
            session_name (str): Name of the SSH session to connect to
        """
        try:
            # Retrieve session details
            session = self.sessions.get(session_name)
            if not session:
                self.show_error(f"Session {session_name} not found")
                return

            # Create terminal tab if it doesn't exist
            if session_name not in self.terminal_outputs:
                self.create_terminal_tab(session_name)
                self.logger.info(f"Terminal tab created for session: {session_name}")

            # Extract connection parameters
            host = session.get('host')
            username = session.get('username')
            password = session.get('password')
            key_file = session.get('key_file')
            port = session.get('port', 22)

            # Validate required parameters
            if not all([host, username]):
                self.show_error("Incomplete session configuration")
                return

            # Decrypt password if encrypted
            if password and isinstance(password, bytes):
                try:
                    password = self.fernet.decrypt(password).decode()
                except Exception as decrypt_error:
                    self.logger.error(f"Decryption error: {decrypt_error}")
                    password = None

            # Perform connection in main thread
            def perform_connection():
                try:
                    # Create SSH client
                    ssh_client = ModernSSHClient()
                    
                    # Attempt connection
                    if key_file:
                        ssh_client.connect(
                            hostname=host, 
                            username=username, 
                            key_filename=key_file, 
                            port=port
                        )
                    else:
                        ssh_client.connect(
                            hostname=host, 
                            username=username, 
                            password=password, 
                            port=port
                        )
                    
                    # Open channel
                    channel = ssh_client.invoke_shell()
                    channel.settimeout(0.1)
                    
                    # Store SSH client and channel
                    self.ssh_clients[session_name] = ssh_client
                    self.active_channels[session_name] = channel
                    
                    # Log successful connection
                    self.logger.info(f"Connected (version {ssh_client.get_transport().remote_version})")
                    
                    # Handle connection success
                    self._handle_connection_success(session_name)
                
                except paramiko.AuthenticationException as auth_error:
                    self._handle_connection_error(session_name, f"Authentication failed: {str(auth_error)}")
                
                except paramiko.SSHException as ssh_error:
                    self._handle_connection_error(session_name, f"SSH connection error: {str(ssh_error)}")
                
                except socket.error as socket_error:
                    self._handle_connection_error(session_name, f"Network error: {str(socket_error)}")
                
                except Exception as unexpected_error:
                    self._handle_connection_error(session_name, f"Unexpected connection error: {str(unexpected_error)}")

            # Use after method to ensure execution in main thread
            self.root.after(0, perform_connection)

        except Exception as e:
            self.logger.error(f"Error connecting to session {session_name}: {e}")
            self.show_error(f"Connection setup failed: {str(e)}")

    def _handle_connection_success(self, session_name: str) -> None:
        """
        Handle successful SSH connection with comprehensive setup.
        
        Args:
            session_name (str): Name of the SSH session
        """
        try:
            # Retrieve SSH client and channel from active sessions
            ssh_client = self.ssh_clients.get(session_name)
            channel = self.active_channels.get(session_name)
            
            # Validate SSH client and channel
            if not ssh_client or not channel:
                raise ValueError(f"No active SSH client or channel for session: {session_name}")
            
            # Create terminal tab if it doesn't exist
            if session_name not in self.terminal_outputs:
                self.create_terminal_tab(session_name)
                self.logger.info(f"Terminal tab created for session: {session_name}")

            # Update status
            self.update_status(f"Connected to {session_name}")
            
            # Start reading from the channel in a separate thread
            read_thread = threading.Thread(
                target=self._read_channel_thread,
                args=(session_name, channel),
                daemon=True
            )
            read_thread.start()
            
            # Log successful connection details
            transport = ssh_client.get_transport()
            if transport:
                self.logger.info(f"Connection details: {transport.get_remote_server_key()}")
        
        except Exception as e:
            self.logger.error(f"Error handling connection success for {session_name}: {e}")
            self.show_error(f"Connection setup failed: {str(e)}")
            
            # Cleanup in case of failure
            if session_name in self.ssh_clients:
                del self.ssh_clients[session_name]
            if session_name in self.active_channels:
                del self.active_channels[session_name]

    def _handle_connection_error(self, session_name: str, error_message: str) -> None:
        """Show connection error dialog with retry and edit options."""
        # Log the error
        self.logger.error(f"Connection error for {session_name}: {error_message}")
        
        # Show error dialog with retry and edit options
        retry = messagebox.askretrycancel(
            "Connection Failed", 
            f"{error_message}\n\nDo you want to retry?"
        )
        
        if retry:
            # Retry the connection
            self.connect_to_session(session_name)
        else:
            # Close the session tab without further action
            self.close_specific_tab(session_name)

    def close(self) -> None:
        """Close the SSH connection and channel."""
        if self.channel:
            self.channel.close()
        self.client.close()

    def _read_channel_thread(self, session_name: str, channel: paramiko.Channel) -> None:
        """Thread function to read from SSH channel with improved error handling."""
        try:
            client = self.ssh_clients.get(session_name)
            if not client:
                self.logger.error(f"No SSH client found for session: {session_name}")
                return

            while True:
                if not channel or channel.closed:
                    self.logger.error(f"Channel closed for {session_name}")
                    break

                if channel.recv_ready():
                    data = channel.recv(4096)
                    if not data:
                        break
                        
                    try:
                        decoded_data = data.decode('utf-8', errors='replace')
                        if decoded_data:
                            # Process the raw data using the client's method
                            processed_data = client._process_terminal_output(decoded_data)
                            # Update UI in main thread
                            self.root.after(0, lambda d=processed_data: self._update_terminal(session_name, d))
                    except UnicodeDecodeError as e:
                        self.logger.error(f"Unicode decode error: {e}")
                        continue
                        
                elif channel.exit_status_ready():
                    break
                    
                time.sleep(0.1)  # Prevent high CPU usage
                
        except Exception as e:
            self.logger.error(f"Error in read channel thread: {e}")
            
        finally:
            # Clean up on exit
            if channel and not channel.closed:
                channel.close()

    def _update_terminal(self, session_name: str, data: str):
        """
        Update terminal output using pytermgui with advanced formatting.
        
        Args:
            session_name (str): Name of the SSH session
            data (str): Terminal output data
        """
        try:
            # Create a terminal output queue if not exists
            if not hasattr(self, '_terminal_queues'):
                self._terminal_queues = {}
            
            if session_name not in self._terminal_queues:
                self._terminal_queues[session_name] = queue.Queue()
            
            # Put data into the queue
            self._terminal_queues[session_name].put(data)
            
            # Process terminal output in the main thread
            def process_terminal_output():
                while not self._terminal_queues[session_name].empty():
                    output = self._terminal_queues[session_name].get()
                    
                    # Remove ANSI escape codes
                    clean_output = self._strip_ansi_codes(output)
                    
                    # Get the terminal widget for this session
                    terminal_widget = self.terminal_outputs.get(session_name)
                    
                    if terminal_widget:
                        # Use pytermgui for advanced terminal output
                        try:
                            # Configure terminal styling
                            terminal_widget.config(state=tk.NORMAL)
                            
                            # Insert the output
                            terminal_widget.insert(tk.END, clean_output)
                            
                            terminal_widget.see(tk.END)
                            terminal_widget.update_idletasks()
                            terminal_widget.config(state=tk.DISABLED)
                        except Exception as e:
                            self.logger.error(f"Error processing terminal output: {e}")
            
            # Schedule terminal output processing in the main thread
            self.root.after(0, process_terminal_output)
        
        except Exception as e:
            self.logger.error(f"Error updating terminal for {session_name}: {e}")
            self.show_error(f"Terminal update error: {e}")

    def send_command(self, session_name: str) -> None:
        """
        Execute a command in the SSH session with enhanced terminal handling.
        
        Args:
            session_name (str): Name of the SSH session
        """
        try:
            if session_name in self.command_inputs and session_name in self.active_channels:
                command_input = self.command_inputs[session_name]
                command = command_input.get().strip()
                
                if not command:
                    return
                    
                channel = self.active_channels[session_name]
                
                # Set command running state and disable clear button
                self.command_running[session_name] = True
                if session_name in self.clear_buttons:
                    self.clear_buttons[session_name].configure(state="disabled")
                
                # Detailed logging for command tracking
                self.logger.info(f"Sending command: {command}")
                
                # Send command
                channel.send(command + "\n")
                
                # Add to command history
                if session_name not in self.command_history:
                    self.command_history[session_name] = []
                if not self.command_history[session_name] or command != self.command_history[session_name][-1]:
                    self.command_history[session_name].append(command)
                
                # Debug logging for command history
                self.logger.debug(f"Command History for {session_name}: {self.command_history[session_name]}")
                
                # Update history position to point to the end of history
                self.history_position[session_name] = len(self.command_history[session_name])
                
                # Clear input
                command_input.delete(0, tk.END)
                
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            self.show_error(f"Failed to send command: {str(e)}")
            
        finally:
            # Reset command running state and enable clear button after a short delay
            def enable_clear_button():
                self.command_running[session_name] = False
                if session_name in self.clear_buttons:
                    self.clear_buttons[session_name].configure(state="normal")
            
            # Schedule the button enable after 1 second
            self.root.after(1000, enable_clear_button)

    def history_up(self, session_name: str, event=None) -> str:
        """Navigate up through command history."""
        try:
            # Check if we have history for this session
            if not self.command_history.get(session_name, []):
                self.logger.debug(f"No command history for session: {session_name}")
                return "break"
            
            # Get the current command input widget
            command_input = self.command_inputs.get(session_name)
            if not command_input:
                return "break"
            
            # Get current position in history
            current_pos = self.history_position.get(session_name, len(self.command_history[session_name]))

            # Store current command if we're at the end of history
            if current_pos == len(self.command_history[session_name]):
                current_command = command_input.get().strip()
                if current_command:
                    self.command_history[session_name].append(current_command)
                    current_pos = len(self.command_history[session_name])

            # Move up in history if possible
            if current_pos > 0:
                current_pos -= 1
                self.history_position[session_name] = current_pos
                
                # Update command input with historical command
                command_input.delete(0, tk.END)
                command_input.insert(0, self.command_history[session_name][current_pos])
            
            return "break"  # Prevent default handling
            
        except Exception as e:
            self.logger.error(f"Error navigating command history up: {e}")
            return "break"

    def history_down(self, session_name: str, event=None) -> str:
        """Navigate down through command history."""
        try:
            # Check if we have history for this session
            if not self.command_history.get(session_name, []):
                self.logger.debug(f"No command history for session: {session_name}")
                return "break"
            
            # Get the current command input widget
            command_input = self.command_inputs.get(session_name)
            if not command_input:
                return "break"
            
            # Get current position in history
            current_pos = self.history_position.get(session_name, len(self.command_history[session_name]))
            
            # Move down in history if possible
            if current_pos < len(self.command_history[session_name]):
                current_pos += 1
                self.history_position[session_name] = current_pos
                
                # Update command input with historical command or clear if at end
                command_input.delete(0, tk.END)
                if current_pos < len(self.command_history[session_name]):
                    command_input.insert(0, self.command_history[session_name][current_pos])
            
            return "break"  # Prevent default handling
            
        except Exception as e:
            self.logger.error(f"Error navigating command history down: {e}")
            return "break"

    def disconnect_session(self, session_name: str) -> None:
        """Disconnect an SSH session."""
        try:
            if session_name in self.ssh_clients:
                self.ssh_clients[session_name].close()
                del self.ssh_clients[session_name]
            
            if session_name in self.active_channels:
                self.active_channels[session_name].close()
                del self.active_channels[session_name]

            # Clean up terminal resources
            if session_name in self.terminal_outputs:
                del self.terminal_outputs[session_name]
            if session_name in self.command_inputs:
                del self.command_inputs[session_name]
            if session_name in self.command_history:
                del self.command_history[session_name]
            if session_name in self.history_position:
                del self.history_position[session_name]

            # Remove the tab
            if hasattr(self.tab_view, "_name_list") and session_name in self.tab_view._name_list:
                self.tab_view.delete(session_name)
                
                # If no tabs left except welcome, switch to welcome
                remaining_tabs = [tab for tab in self.tab_view._name_list if tab != "Welcome"]
                if not remaining_tabs:
                    self.tab_view.set("Welcome")

            self.logger.info(f"Session {session_name} disconnected successfully")
            self.update_status(f"Disconnected from {session_name}")

        except Exception as e:
            self.logger.error(f"Error disconnecting session {session_name}: {str(e)}")
            self.update_status(f"Error disconnecting from {session_name}")

    def save_sessions(self):
        """Save sessions to a JSON file."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.sessions, f, indent=4)
            self.update_status("Sessions saved")
        except Exception as e:
            logging.error(f"Error saving sessions: {e}")
            self.update_status("Error saving sessions")

    def import_sessions(self) -> None:
        """Import sessions from a JSON file."""
        try:
            file_path = filedialog.askopenfilename(
                title="Import Sessions", 
                filetypes=[("JSON files", "*.json")]
            )
            
            if not file_path:
                return  # User cancelled
            
            with open(file_path, 'r') as f:
                imported_sessions = json.load(f)
            
            # Merge or replace existing sessions
            if messagebox.askyesno("Confirm", "Replace existing sessions?"):
                # Replace all existing sessions
                self.sessions = imported_sessions
            else:
                # Merge imported sessions, overwriting existing with the same name
                self.sessions.update(imported_sessions)
            
            # Save the updated sessions
            self.save_sessions()
            
            # Update the sessions list
            self.update_session_list()
            
            # Show success message
            self.update_status(f"Imported {len(imported_sessions)} sessions")
            
        except json.JSONDecodeError:
            logging.error("Invalid JSON file")
            messagebox.showerror("Error", "Invalid JSON file")
        except Exception as e:
            logging.error(f"Import failed: {e}")
            messagebox.showerror("Error", f"Failed to import sessions: {e}")

    def export_sessions(self) -> None:
        """Export sessions to a JSON file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Export Sessions"
            )
            
            if not file_path:
                return  # User cancelled
            
            with open(file_path, 'w') as f:
                json.dump(self.sessions, f, indent=4)
            
            self.update_status(f"Exported {len(self.sessions)} sessions")
            
        except Exception as e:
            logging.error(f"Export failed: {e}")
            messagebox.showerror("Error", f"Failed to export sessions: {e}")

    def update_session_list(self) -> None:
        """Update the session list in the UI."""
        try:
            # Clear existing session buttons
            for button in self.session_buttons.values():
                button.destroy()
            self.session_buttons.clear()

            # Filter sessions based on search
            search_term = self.search_var.get().lower()
            filtered_sessions = {
                name: session for name, session in self.sessions.items()
                if search_term in name.lower() or
                search_term in session.get("host", "").lower() or
                search_term in session.get("username", "").lower()
            }

            # Create new session buttons
            for name in filtered_sessions:
                self.create_session_button(name)

            self.logger.debug(f"Session list updated with {len(filtered_sessions)} sessions")
            
        except Exception as e:
            self.logger.error(f"Error updating session list: {e}")

    def bind_shortcuts(self) -> None:
        """Bind keyboard shortcuts."""
        try:
            # Debug logging for command inputs
            self.logger.debug(f"Command Inputs: {list(self.command_inputs.keys())}")
            
            shortcuts = self.preferences.get("shortcuts", {})
            
            # Session navigation shortcuts
            self.root.bind('<Control-Tab>', self.next_tab)
            self.root.bind('<Control-Shift-Tab>', self.prev_tab)
            self.root.bind('<Control-w>', lambda e: self.close_current_tab())
            
            # New session and search shortcuts
            self.root.bind('<Control-n>', lambda e: self.new_session_dialog())
            self.root.bind('<Control-f>', self.focus_search)
            
            # Fullscreen shortcut
            self.root.bind('<F11>', self.toggle_fullscreen)
            
            # Terminal command history shortcuts
            for session_name, command_input in list(self.command_inputs.items()):
                try:
                    # Unbind existing bindings first to prevent multiple bindings
                    command_input.unbind('<Up>')
                    command_input.unbind('<Down>')
                except Exception as unbind_error:
                    self.logger.warning(f"Error unbinding keys for {session_name}: {unbind_error}")
                
                # Bind with lambda to capture current session_name
                # Use event-driven binding with explicit event parameter
                command_input.bind('<Up>', lambda event, s=session_name: self.history_up(s, event))
                command_input.bind('<Down>', lambda event, s=session_name: self.history_down(s, event))
                
                # Additional logging to verify binding
                self.logger.debug(f"Bound history navigation for session: {session_name}")
                self.logger.debug(f"Command input for {session_name}: {command_input}")
            
            self.logger.info("Shortcuts bound successfully")
            
        except Exception as e:
            self.logger.error(f"Error binding shortcuts: {str(e)}")
            self.show_error("Failed to bind shortcuts")

    def next_tab(self, event=None) -> None:
        """Switch to next tab."""
        if not hasattr(self, 'tab_view'):
            return
        tabs = self.tab_view.tabs()
        if not tabs:
            return
        current = self.tab_view.select()
        idx = tabs.index(current)
        next_idx = (idx + 1) % len(tabs)
        self.tab_view.select(tabs[next_idx])

    def prev_tab(self, event=None) -> None:
        """Switch to previous tab."""
        if not hasattr(self, 'tab_view'):
            return
        tabs = self.tab_view.tabs()
        if not tabs:
            return
        current = self.tab_view.select()
        idx = tabs.index(current)
        prev_idx = (idx - 1) % len(tabs)
        self.tab_view.select(tabs[prev_idx])

    def focus_search(self, event=None) -> None:
        """Focus the search entry."""
        self.search_var.set("")  # Clear existing search
        self.search_entry.focus_set()

    def toggle_fullscreen(self, event=None) -> None:
        """Toggle fullscreen mode."""
        try:
            # Check current fullscreen state
            is_fullscreen = self.root.attributes('-fullscreen')
            
            # Toggle fullscreen
            self.root.attributes('-fullscreen', not is_fullscreen)
            
            # Update status bar
            status_msg = "Fullscreen Enabled" if not is_fullscreen else "Fullscreen Disabled"
            self.update_status(status_msg)
            
            # Log the action
            self.logger.info(status_msg)
        except Exception as e:
            # Log any errors that occur during fullscreen toggle
            self.logger.error(f"Error toggling fullscreen: {e}")
            self.update_status("Failed to toggle fullscreen")

    def auto_save(self) -> None:
        """Auto-save sessions periodically."""
        self.save_sessions()
        self.root.after(300000, self.auto_save)  # Schedule next auto-save

    def duplicate_session(self, session_name: str) -> None:
        """Duplicate an existing session."""
        if session_name in self.sessions:
            new_name = f"{session_name} (copy)"
            i = 1
            while new_name in self.sessions:
                new_name = f"{session_name} (copy {i})"
                i += 1
            self.sessions[new_name] = copy.deepcopy(self.sessions[session_name])
            self.update_session_tree()

    def export_session(self, session_name: str) -> None:
        """Export session configuration."""
        if session_name in self.sessions:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=f"{session_name}.json"
            )
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(self.sessions[session_name], f, indent=4)

    def import_session(self) -> None:
        """Import session configuration."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            with open(file_path, 'r') as f:
                session_data = json.load(f)
                session_name = os.path.splitext(os.path.basename(file_path))[0]
                if session_name in self.sessions:
                    i = 1
                    while f"{session_name}_{i}" in self.sessions:
                        i += 1
                    session_name = f"{session_name}_{i}"
                self.sessions[session_name] = session_data
                self.update_session_tree()

    def create_welcome_tab(self):
        """Create the welcome tab."""
        try:
            # Create welcome tab
            welcome_frame = self.tab_view.add("Welcome")
            
            # Welcome message
            welcome_label = ctk.CTkLabel(
                welcome_frame,
                text="Welcome to Modern SSH Client",
                font=("Helvetica", 24, "bold")
            )
            welcome_label.pack(pady=20)
            
            # Quick start guide
            guide_text = """
            Quick Start Guide:
            
            1. Create a new session using the '+' button or Ctrl+N
            2. Enter your connection details
            3. Click 'Save' to store the session
            4. Click on the session name to connect
            
            Use the search bar above to quickly find your sessions.
            """
            
            guide_label = ctk.CTkLabel(
                welcome_frame,
                text=guide_text,
                justify="left",
                font=("Helvetica", 12)
            )
            guide_label.pack(pady=10, padx=20)
            
            # Recent sessions section
            recent_frame = ctk.CTkFrame(welcome_frame)
            recent_frame.pack(fill="x", padx=20, pady=10)
            
            recent_label = ctk.CTkLabel(
                recent_frame,
                text="Recent Sessions:",
                font=("Helvetica", 16, "bold")
            )
            recent_label.pack(anchor="w", pady=5)
            
            # Display recent sessions (if any)
            recent_sessions = list(self.sessions.keys())[-5:]  # Get last 5 sessions
            if recent_sessions:
                for session in recent_sessions:
                    session_btn = ctk.CTkButton(
                        recent_frame,
                        text=session,
                        command=lambda s=session: self.connect_to_session(s)
                    )
                    session_btn.pack(fill="x", pady=2)
            else:
                no_sessions_label = ctk.CTkLabel(
                    recent_frame,
                    text="No recent sessions",
                    font=("Helvetica", 12)
                )
                no_sessions_label.pack(pady=5)

            self.logger.debug("Welcome tab created successfully")
        except Exception as e:
            self.logger.error(f"Error creating welcome tab: {str(e)}")
            messagebox.showerror("Error", f"Failed to create welcome tab: {str(e)}")

    def on_closing(self):
        """Handle application closing."""
        try:
            # Save sessions before closing
            self.save_sessions()
            
            # Save configuration
            self.save_preferences()
            
            # Close all SSH connections
            for session_name in list(self.ssh_clients.keys()):
                self.disconnect_session(session_name)
            
            # Destroy the window
            self.root.destroy()
            
        except Exception as e:
            logging.error(f"Error during closing: {e}")
            self.root.destroy()  # Ensure window closes even if there's an error

    def clear_history(self) -> None:
        """Clear the command history for all sessions."""
        self.command_history.clear()
        self.history_position.clear()
        messagebox.showinfo("Info", "Command history has been cleared.")

    def update_terminal_font(self, font_size: int) -> None:
        """
        Safely update the font size for terminal and text-based widgets.
        
        Args:
            font_size (int): Font size to set, must be between 8 and 24
        """
        try:
            # Validate font size
            if not 8 <= font_size <= 24:
                raise ValueError("Font size must be between 8 and 24")
            
            # Prevent recursive calls and ensure initialization
            if (hasattr(self, '_font_update_in_progress') or 
                not hasattr(self, 'terminal_outputs') or 
                not hasattr(self, 'tab_view')):
                return
            
            self._font_update_in_progress = True
            
            # Determine font family
            font_family = self.preferences.get("terminal_font_family", "Monospace")
            
            # Prepare font configuration
            font_config = (font_family, font_size)
            
            # Update terminal outputs with minimal recursion risk
            for session_name, terminal_widget in list(self.terminal_outputs.items()):
                try:
                    # Use direct configuration to minimize event triggers
                    if hasattr(terminal_widget, 'configure'):
                        terminal_widget.configure(font=font_config)
                except Exception as e:
                    self.logger.warning(f"Could not update font for terminal {session_name}: {e}")
            
            # Update text widgets in tab view with careful traversal
            if hasattr(self, 'tab_view'):
                try:
                    for tab in self.tab_view.winfo_children():
                        for child in tab.winfo_children():
                            if isinstance(child, (tk.Text, ctk.CTkTextbox, ctk.CTkEntry)):
                                try:
                                    child.configure(font=font_config)
                                except Exception as inner_e:
                                    self.logger.warning(f"Could not update font for {child}: {inner_e}")
                except Exception as e:
                    self.logger.warning(f"Error traversing tab view for font update: {e}")
            
            # Update preferences
            self.preferences["terminal_font_size"] = font_size
            
            # Save preferences without triggering recursive updates
            try:
                with open(self.preferences_file, 'w') as f:
                    json.dump(self.preferences, f, indent=4)
                self.logger.info(f"Updated terminal font to {font_size}")
            except Exception as e:
                self.logger.error(f"Could not save font preferences: {e}")
        
        except Exception as e:
            error_msg = f"Font update failed: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Font Update Error", error_msg)
        
        finally:
            # Always clear the update flag
            if hasattr(self, '_font_update_in_progress'):
                delattr(self, '_font_update_in_progress')

    def manage_shortcuts(self) -> None:
        """Show keyboard shortcuts management dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for shortcuts
        columns = ("Action", "Shortcut")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Configure columns
        tree.heading("Action", text="Action")
        tree.heading("Shortcut", text="Shortcut")
        tree.column("Action", width=200)
        tree.column("Shortcut", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure grid weights
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Default shortcuts
        default_shortcuts = {
            "New Session": "<Control-t>",
            "Focus Search": "<Control-f>",
            "Toggle Fullscreen": "F11",
            "Connect Session": "<Return>",
            "Disconnect Session": "<Control-d>",
            "Clear Terminal": "<Control-l>"
        }
        
        # Load custom shortcuts from config
        shortcuts = self.config.get("shortcuts", default_shortcuts)
        
        # Populate treeview
        for action, shortcut in shortcuts.items():
            tree.insert("", tk.END, values=(action, shortcut))
        
        def edit_shortcut():
            """Edit the selected shortcut."""
            selected = tree.selection()
            if not selected:
                return
                
            item = selected[0]
            action = tree.item(item)["values"][0]
            
            # Create edit dialog
            edit_dialog = tk.Toplevel(dialog)
            edit_dialog.title(f"Edit Shortcut - {action}")
            edit_dialog.geometry("300x150")
            edit_dialog.transient(dialog)
            edit_dialog.grab_set()
            
            # Create and pack widgets
            ctk.CTkLabel(edit_dialog, text="Press new shortcut:").pack(pady=10)
            shortcut_var = tk.StringVar(value=shortcuts[action])
            shortcut_entry = ctk.CTkEntry(edit_dialog, textvariable=shortcut_var, state="readonly")
            shortcut_entry.pack(pady=5, padx=10, fill=tk.X)
            
            def on_key(event):
                """Handle key press event."""
                if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"):
                    return
                    
                modifiers = []
                if event.state & 0x4:
                    modifiers.append("Control")
                if event.state & 0x1:
                    modifiers.append("Shift")
                if event.state & 0x8:
                    modifiers.append("Alt")
                    
                key = event.keysym
                if key == "plus":
                    key = "plus"
                elif key == "minus":
                    key = "minus"
                elif len(key) == 1:
                    key = key.lower()
                    
                shortcut = "<" + "-".join(modifiers + [key]) + ">" if modifiers else key
                shortcut_var.set(shortcut)
                
            shortcut_entry.bind("<KeyPress>", on_key)
            
            def save_shortcut():
                """Save the new shortcut."""
                new_shortcut = shortcut_var.get()
                shortcuts[action] = new_shortcut
                tree.item(item, values=(action, new_shortcut))
                edit_dialog.destroy()
                
            # Buttons
            button_frame = ctk.CTkFrame(edit_dialog)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
            ctk.CTkButton(button_frame, text="Save", command=save_shortcut).pack(side=tk.RIGHT, padx=5)
            ctk.CTkButton(button_frame, text="Cancel", command=edit_dialog.destroy).pack(side=tk.RIGHT, padx=5)
            
            shortcut_entry.focus_set()
            
        def reset_defaults():
            """Reset shortcuts to defaults."""
            if messagebox.askyesno("Reset Shortcuts", "Reset all shortcuts to default values?"):
                # Replace all existing shortcuts
                tree.delete(*tree.get_children())
                shortcuts.clear()
                shortcuts.update(default_shortcuts)
                for action, shortcut in default_shortcuts.items():
                    tree.insert("", tk.END, values=(action, shortcut))
        
        # Buttons
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="Edit",
            command=edit_shortcut
        ).pack(side=tk.LEFT, padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Reset to Defaults",
            command=reset_defaults
        ).pack(side=tk.LEFT, padx=5)
        
        def save_shortcuts():
            """Save shortcuts to config."""
            try:
                self.config["shortcuts"] = shortcuts
                self.save_config()
                self.create_shortcuts()  # Recreate shortcuts with new bindings
                dialog.destroy()
                self.update_status("Shortcuts saved")
            except Exception as e:
                messagebox.showerror("Error", f"Error saving shortcuts: {str(e)}")
        
        ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_shortcuts
        ).pack(side=tk.RIGHT, padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def on_entry_focus(self, entry_widget, focused):
        """Handle focus events for entry widgets."""
        if focused:
            entry_widget.configure(border_color=("gray75", "gray30"))
        else:
            entry_widget.configure(border_color=("gray70", "gray25"))

    def cycle_history(self, session_name: str, direction: str) -> None:
        """Cycle through command history."""
        try:
            if not self.command_history.get(session_name, []):
                self.logger.debug(f"No command history for session: {session_name}")
                return

            history = self.command_history[session_name]
            if not history:
                return

            command_input = self.command_inputs.get(session_name)
            current_position = self.history_position.get(session_name, len(self.command_history[session_name]))

            # Store current command if we're at the end of history
            if current_position == len(history):
                current_command = command_input.get().strip()
                if current_command:
                    self.command_history[session_name].append(current_command)
                    current_position = len(history)

            # Update position based on direction
            if direction == "up":
                current_position = max(0, current_position - 1)
            elif direction == "down":
                current_position = min(len(history), current_position + 1)

            # Update the input field
            command_input.delete(0, tk.END)
            if current_position < len(history):
                command_input.insert(0, history[current_position])

            # Store the new position
            self.history_position[session_name] = current_position

        except Exception as e:
            self.logger.error(f"Error cycling history: {e}")
            # Reset position on error
            self.history_position[session_name] = len(self.command_history.get(session_name, []))

    def edit_session(self, session_name):
        """Edit the selected SSH session."""
        if session_name not in self.sessions:
            messagebox.showerror("Error", "Session not found")
            return

        session = self.sessions[session_name]
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Edit Session: {session_name}")
        dialog.geometry("450x350")  # Set a fixed size for better layout

        # Create a main frame with padding
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Session Name
        ctk.CTkLabel(main_frame, text="Session Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        session_name_entry = ctk.CTkEntry(main_frame, width=200)
        session_name_entry.insert(0, session_name)
        session_name_entry.grid(row=0, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Host
        ctk.CTkLabel(main_frame, text="Host:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        host_entry = ctk.CTkEntry(main_frame, width=200)
        host_entry.insert(0, session.get("host", ""))
        host_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Port
        ctk.CTkLabel(main_frame, text="Port:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        port_entry = ctk.CTkEntry(main_frame, width=200)
        port_entry.insert(0, str(session.get("port", 22)))
        port_entry.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Username
        ctk.CTkLabel(main_frame, text="Username:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        username_entry = ctk.CTkEntry(main_frame, width=200)
        username_entry.insert(0, session.get("username", ""))
        username_entry.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # Password
        ctk.CTkLabel(main_frame, text="Password:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        password_entry = ctk.CTkEntry(main_frame, show="*", width=200)
        if session.get("password"):
            try:
                decrypted_password = self.decrypt_data(session["password"])
                password_entry.insert(0, decrypted_password)
            except Exception as e:
                self.logger.error(f"Failed to decrypt password: {e}")
        password_entry.grid(row=4, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        # SSH Key
        ctk.CTkLabel(main_frame, text="SSH Key:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        ssh_key_entry = ctk.CTkEntry(main_frame, width=200)
        if session.get("key_file"):
            ssh_key_entry.insert(0, session["key_file"])
        ssh_key_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        def browse_ssh_key():
            key_path = filedialog.askopenfilename(
                title="Select SSH Key",
                filetypes=[("All Files", "*.*")]
            )
            if key_path:
                ssh_key_entry.delete(0, tk.END)
                ssh_key_entry.insert(0, key_path)

        browse_button = ctk.CTkButton(main_frame, text="Browse", command=browse_ssh_key, width=70)
        browse_button.grid(row=5, column=2, padx=5, pady=5)

        def save_session():
            try:
                # Validate inputs
                new_session_name = session_name_entry.get()
                host = host_entry.get()
                port = port_entry.get()
                username = username_entry.get()
                password = password_entry.get()
                ssh_key_path = ssh_key_entry.get()
                # Save the session details including the SSH key path
                self.sessions[new_session_name] = {
                    "host": host,
                    "port": port,
                    "username": username,
                    "password": password,  # Store password securely
                    "ssh_key_path": ssh_key_path
                }
                self.save_sessions()
                self.update_session_list()
                dialog.destroy()

            except Exception as e:
                self.logger.error(f"Error saving session: {e}")
                messagebox.showerror("Error", f"Failed to save session: {str(e)}")

        save_button = ctk.CTkButton(main_frame, text="Save", command=save_session)
        save_button.grid(row=6, column=0, columnspan=3, pady=10)

        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def delete_session(self, session_name: str) -> None:
        """
        Delete a session completely, including its connection, credentials, and UI elements.
        
        Args:
            session_name (str): Name of the session to delete
        """
        try:
            # First, disconnect the session if it's active
            if session_name in self.ssh_clients:
                try:
                    self.disconnect_session(session_name)
                except Exception as disconnect_error:
                    self.logger.warning(f"Error disconnecting session {session_name}: {disconnect_error}")
            
            # Remove SSH client if exists
            if session_name in self.ssh_clients:
                del self.ssh_clients[session_name]
            
            # Remove terminal frame and output if exists
            if session_name in self.terminal_frames:
                try:
                    self.terminal_frames[session_name].destroy()
                    del self.terminal_frames[session_name]
                except Exception as frame_error:
                    self.logger.warning(f"Error removing terminal frame for {session_name}: {frame_error}")
            
            # Remove terminal output widget
            if session_name in self.terminal_outputs:
                del self.terminal_outputs[session_name]
            
            # Remove command input widget
            if session_name in self.command_inputs:
                del self.command_inputs[session_name]
            
            # Remove session button
            if session_name in self.session_buttons:
                try:
                    self.session_buttons[session_name].destroy()
                    del self.session_buttons[session_name]
                except Exception as button_error:
                    self.logger.warning(f"Error removing session button for {session_name}: {button_error}")
            
            # Remove session from sessions dictionary
            if session_name in self.sessions:
                del self.sessions[session_name]
            
            # Remove command history for this session
            if session_name in self.command_history:
                del self.command_history[session_name]
            
            # Remove active channel if exists
            if session_name in self.active_channels:
                del self.active_channels[session_name]

            # Save updated sessions
            self.save_sessions()
            
            # Update session list in UI
            self.update_session_list()
            
            # Log the deletion
            self.logger.info(f"Session {session_name} deleted successfully")
            
            # Show a notification to the user
            self.update_status(f"Session '{session_name}' deleted successfully")
        
        except Exception as e:
            self.logger.error(f"Error deleting session {session_name}: {e}")
            self.show_error(f"Failed to delete session '{session_name}'. Please check the logs.")

    def close_specific_tab(self, tab_name: str) -> None:
        """Close a specific tab by name."""
        try:
            # Try to remove the tab using CustomTkinter method
            self.tab_view.delete(tab_name)
        except Exception:
            # Fallback: try to find and remove the tab
            try:
                # Get the list of tab names from the segmented button
                tab_names = self.tab_view._segmented_button._buttons.keys()
                
                # Find and remove the matching tab
                for name in tab_names:
                    if name.lower() == tab_name.lower():
                        self.tab_view.delete(name)
                        break
            except Exception as e:
                self.logger.error(f"Error closing tab {tab_name}: {e}")
        
        # Clean up associated resources
        if tab_name in self.ssh_clients:
            self.disconnect_session(tab_name)
        
        # Remove other associated resources
        self.ssh_clients.pop(tab_name, None)
        self.active_channels.pop(tab_name, None)
        self.terminal_frames.pop(tab_name, None)
        self.terminal_outputs.pop(tab_name, None)
        self.command_inputs.pop(tab_name, None)
        
        # Try to remove from segmented button if possible
        try:
            self.tab_view._segmented_button.delete(tab_name)
        except Exception:
            pass

    def create_menu_bar(self):
        """Create the menu bar."""
        self.menu_bar = tk.Menu(self.root)
        self.root.configure(menu=self.menu_bar)  # Changed from config to configure
        
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Session", command=self.new_session_dialog)
        file_menu.add_command(label="Import Sessions", command=self.import_sessions)
        file_menu.add_command(label="Export Sessions", command=self.export_sessions)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)  # Changed to on_closing

        # Edit menu
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences", command=self.show_preferences)

        # View menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        theme_menu.add_command(label="Dark Mode", command=lambda: self.apply_theme("dark"))
        theme_menu.add_command(label="Light Mode", command=lambda: self.apply_theme("light"))

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)

    def connect_ssh(self, session_name, host, username, password=None, key_filename=None, port=22):
        """
        Connect to SSH server with improved error handling and logging.
        
        Args:
            session_name (str): Name of the session for tracking
            host (str): SSH server hostname or IP address
            username (str): Username for authentication
            password (str, optional): Password for authentication
            key_filename (str, optional): Path to private key file
            port (int, optional): SSH server port. Defaults to 22.
        
        Returns:
            paramiko.SSHClient: Connected SSH client or None if connection fails
        """
        try:
            # Validate input parameters
            if not host or not username:
                raise ValueError("Host and username are required")

            client = self.ssh_clients.get(session_name)
            if not client:
                raise ValueError("SSH client not initialized")
            
            # Connect to the server
            client.connect_ssh(
                host=host, 
                username=username, 
                password=password, 
                key_filename=key_filename, 
                port=port
            )

            # Update UI in main thread
            self.root.after(0, lambda: self._handle_connection_success(session_name))

        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            messagebox.showerror("Connection Error", str(e))
            raise

    def read_channel(self, session_name, channel):
        """Read from the SSH channel."""
        while channel.active:
            try:
                if channel.recv_ready():
                    output = channel.recv(1024)
                    self.root.after(0, lambda d=output: self.terminal_outputs[session_name].insert("end", d))
            except Exception as e:
                logging.error(f"Error reading from channel: {e}")
                break

    def show_log(self) -> None:
        """Show the application's log file in a new window."""
        try:
            with open('ssh_client.log', 'r') as log_file:
                log_content = log_file.read()

            dialog = tk.Toplevel(self.root)
            dialog.title("Log Viewer")
            dialog.geometry("600x400")

            text_widget = tk.Text(dialog, wrap=tk.WORD)
            text_widget.insert("1.0", log_content)
            text_widget.config(state="disabled")
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        except FileNotFoundError:
            messagebox.showerror("Error", "Log file not found.")
        except Exception as e:
            logging.error(f"Failed to show log: {e}")
            messagebox.showerror("Error", f"Failed to show log: {e}")

    def show_documentation(self):
        """Show documentation window in an organized manner."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Documentation")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title Section
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="Documentation", 
            font=("Helvetica", 24, "bold")
        )
        title_label.pack(pady=10)
        
        # Content Section
        content_frame = ctk.CTkScrollableFrame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Add mouse wheel event bindings
        content_frame.bind("<MouseWheel>", lambda event: self._on_mousewheel(event, content_frame))
        content_frame.bind("<Button-4>", lambda event: self._on_mousewheel(event, content_frame))
        content_frame.bind("<Button-5>", lambda event: self._on_mousewheel(event, content_frame))
        
        sections = {
            "Managing Sessions": [
                "Create new sessions via File > New Session or Ctrl+N",
                "Double-click a session to connect",
                "Use the search bar to filter sessions (Ctrl+F)",
                "Import/Export sessions for backup or sharing"
            ],
            "Terminal Features": [
                "Multi-tab interface for multiple sessions",
                "Command history navigation (Up/Down arrows)",
                "Clear terminal output (Ctrl+L)",
                "Copy/Paste support (Ctrl+C/Ctrl+V)",
                "Customizable font size and family",
                "Session-specific command history"
            ],
            "Security Features": [
                "Encrypted password storage",
                "SSH key authentication support",
                "Auto-disconnect on timeout",
                "Secure connection handling",
                "Host key verification"
            ],
            "Interface Customization": [
                "Dark/Light theme support",
                "Adjustable terminal font size",
                "Customizable keyboard shortcuts",
                "Resizable interface",
                "Session sidebar with search"
            ],
            "Additional Features": [
                "Session import/export",
                "Auto-save functionality",
                "Connection status monitoring",
                "Error logging and reporting",
                "Cross-platform compatibility",
                "ANSI escape sequence support"
            ]
        }
        
        for section, items in sections.items():
            # Section header
            ctk.CTkLabel(content_frame, text=section, font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(10, 5))
            
            # Items
            for item in items:
                frame = ctk.CTkFrame(content_frame)
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=item, font=("Helvetica", 12)).pack(anchor="w", padx=20)
        
        # Close button
        ctk.CTkButton(main_frame, text="Close", command=dialog.destroy).pack(pady=(20, 0))

    def open_github(self):
        """Open the GitHub repository in default browser."""
        import webbrowser
        webbrowser.open("https://github.com/OwaisSafa/SSH-Client")

    def show_about(self):
        """Show about dialog with organized information."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("About SSH Client")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title Section
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="SSH Client", 
            font=("Helvetica", 24, "bold")
        )
        title_label.pack(pady=10)
        
        version_label = ctk.CTkLabel(
            title_frame,
            text="Version 1.0.0",
            font=("Helvetica", 12)
        )
        version_label.pack()
        
        # Description Section
        desc_frame = ctk.CTkFrame(main_frame)
        desc_frame.pack(fill="x", pady=(0, 20))
        
        desc_label = ctk.CTkLabel(
            desc_frame,
            text="A modern, feature-rich SSH client built with\nPython and CustomTkinter.",
            font=("Helvetica", 12),
            justify="center"
        )
        desc_label.pack(pady=10)
        
        # Features Section
        features_frame = ctk.CTkFrame(main_frame)
        features_frame.pack(fill="x", pady=(0, 20))
        
        features_title = ctk.CTkLabel(
            features_frame,
            text="Key Features",
            font=("Helvetica", 14, "bold")
        )
        features_title.pack(pady=5)
        
        features = [
            "🔐 Secure Password Storage",
            "🖥️ Multiple SSH Sessions",
            "📝 Session Management",
            "🔄 Command History",
            "🎨 Dark/Light Themes",
            "🔑 SSH Key Support",
            "⌨️ Keyboard Shortcuts",
            "🔍 Session Search"
        ]
        
        for feature in features:
            feature_label = ctk.CTkLabel(
                features_frame,
                text=feature,
                font=("Helvetica", 12)
            )
            feature_label.pack(pady=2)
        
        # Developer Section
        dev_frame = ctk.CTkFrame(main_frame)
        dev_frame.pack(fill="x", pady=(0, 20))
        
        dev_label = ctk.CTkLabel(
            dev_frame,
            text="Developed by Owais Safa",
            font=("Helvetica", 12, "bold")
        )
        dev_label.pack(pady=5)
        
        # Links Section
        links_frame = ctk.CTkFrame(main_frame)
        links_frame.pack(fill="x")
        
        github_label = ctk.CTkLabel(
            links_frame,
            text="GitHub Repository",
            font=("Helvetica", 12, "underline"),
            text_color="blue",
            cursor="hand2"
        )
        github_label.pack(pady=5)
        github_label.bind("<Button-1>", lambda e: self.open_github())
        
        # Close button
        # close_button = ctk.CTkButton(
        #     main_frame,
        #     text="Close",
        #     command=dialog.destroy
        # )
        # close_button.pack(pady=(20, 0))
        
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Keyboard Shortcuts")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main container
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title Section
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="Keyboard Shortcuts", 
            font=("Helvetica", 24, "bold")
        )
        title_label.pack(pady=10)
        
        # Content Section
        content_frame = ctk.CTkScrollableFrame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Add mouse wheel event bindings
        content_frame.bind("<MouseWheel>", lambda event: self._on_mousewheel(event, content_frame))
        content_frame.bind("<Button-4>", lambda event: self._on_mousewheel(event, content_frame))
        content_frame.bind("<Button-5>", lambda event: self._on_mousewheel(event, content_frame))
        
        categories = {
            "Session Management": [
                ("New Session", "<CTRL-N>"),
                # ("Close Session", "<Control-w>"),
                # ("Next Session", "<Control-Tab>"),
                # ("Previous Session", "<Control-Shift-Tab>")
            ],
            "Navigation": [
                ("Focus Search", "<CTRL-F>"),
                ("Toggle Fullscreen", "F11"),
                # ("Show Preferences", "<Control-comma>"),
                # ("Show Documentation", "F1")
            ],
            "Terminal Controls": [
                ("Clear Terminal", "<CTRL-L>"),
                ("Copy Selection", "<CTRL-C>"),
                ("Paste", "<Control-v>")
            ],
            "History": [
                ("Previous Command", "Up"),
                ("Next Command", "Down")
            ]
        }
        
        for category, shortcuts in categories.items():
            # Category header
            ctk.CTkLabel(content_frame, text=category, font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(10, 5))
            
            # Shortcuts
            for action, shortcut in shortcuts:
                frame = ctk.CTkFrame(content_frame)
                frame.pack(fill="x", pady=2)
                ctk.CTkLabel(frame, text=action, font=("Helvetica", 12)).pack(side="left", padx=20)
                ctk.CTkLabel(frame, text=shortcut, font=("Helvetica", 12, "bold")).pack(side="right", padx=20)
        
        # Close button
        # ctk.CTkButton(main_frame, text="Close", command=dialog.destroy).pack(pady=(20, 0))

    def _on_mousewheel(self, event, scrollable_frame):
        """Handle mouse wheel scrolling for touchpads and mice."""
        # Linux uses event.num, Windows/Mac use event.delta
        if event.num == 5 or event.delta < 0:  # Scroll down
            scrollable_frame.yview_scroll(3, "units")
        if event.num == 4 or event.delta > 0:  # Scroll up
            scrollable_frame.yview_scroll(-3, "units")
        return "break"

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data using Fernet encryption."""
        try:
            if not data:
                return ""
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            self.logger.error(f"Encryption error: {e}")
            return ""

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data using Fernet decryption."""
        try:
            if not encrypted_data:
                return ""
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            self.logger.error(f"Decryption error: {e}")
            return ""

    def save_sessions(self):
        """Save sessions to a JSON file with encryption."""
        try:
            # Create a copy of sessions with encrypted sensitive data
            encrypted_sessions = {}
            for name, session in self.sessions.items():
                encrypted_sessions[name] = {
                    "host": session["host"],
                    "port": session["port"],
                    "username": session["username"],
                    "password": self.encrypt_data(session.get("password", "")),
                    "ssh_key_path": session.get("ssh_key_path", "")
                }
            
            with open(self.session_file, 'w') as f:
                json.dump(encrypted_sessions, f, indent=4)
            self.update_status("Sessions saved")
        except Exception as e:
            self.logger.error(f"Error saving sessions: {e}")
            self.update_status("Error saving sessions")

    def load_sessions(self):
        """Load sessions from JSON file with decryption."""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    encrypted_sessions = json.load(f)
                
                # Decrypt sensitive data
                self.sessions = {}
                for name, session in encrypted_sessions.items():
                    self.sessions[name] = {
                        "host": session["host"],
                        "port": session["port"],
                        "username": session["username"],
                        "password": self.decrypt_data(session.get("password", "")),
                        "ssh_key_path": session.get("ssh_key_path", "")
                    }
            else:
                self.sessions = {}
        except Exception as e:
            self.logger.error(f"Error loading sessions: {e}")
            self.sessions = {}

    def get_or_create_key(self) -> bytes:
        """
        Get or create an encryption key for secure data storage.
        
        Returns:
            bytes: Encryption key for Fernet encryption
        """
        try:
            key_file = os.path.join(os.path.dirname(__file__), "encryption.key")
            
            # Check if key file exists
            if os.path.exists(key_file):
                with open(key_file, "rb") as f:
                    return f.read()
            
            # Generate a new key if no existing key is found
            key = Fernet.generate_key()
            
            # Write the key to file
            with open(key_file, "wb") as f:
                f.write(key)
            
            # Set secure permissions if possible
            try:
                import stat
                os.chmod(key_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as perm_error:
                self.logger.warning(f"Could not set secure permissions on key file: {perm_error}")
            
            return key
        
        except Exception as e:
            self.logger.error(f"Failed to get/create encryption key: {e}")
            # Fallback to generating a new key if all else fails
            return Fernet.generate_key()

    def show_preferences(self):
        """Show preferences dialog with improved styling and options."""
        try:
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Preferences")
            dialog.geometry("400x500")
            
            # Store original settings for cancellation
            original_settings = {
                "theme": self.preferences.get("theme", "dark"),
                "terminal_font_size": self.preferences.get("terminal_font_size", 10),
                "terminal_font_family": self.preferences.get("terminal_font_family", "Monospace")
            }
            
            # Create main container with padding
            container = ctk.CTkFrame(dialog)
            container.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Theme selection
            theme_frame = ctk.CTkFrame(container)
            theme_frame.pack(fill="x", pady=(0, 15))
            
            ctk.CTkLabel(theme_frame, text="Theme:").pack(side="left", padx=5)
            theme_var = tk.StringVar(value=self.current_theme)
            
            def on_theme_change(*args):
                new_theme = theme_var.get()
                # Only apply theme temporarily without saving to preferences
                if new_theme != self.current_theme:
                    ctk.set_appearance_mode(new_theme)
                    self.current_theme = new_theme
                    # Update UI without saving to preferences
                    theme_colors = self.themes[new_theme]
                    if hasattr(self, 'terminal_outputs'):
                        for terminal in self.terminal_outputs.values():
                            if terminal:
                                terminal.configure(
                                    bg=theme_colors['terminal_bg'],
                                    fg=theme_colors['terminal_fg'],
                                    insertbackground=theme_colors['fg']
                                )
            
            theme_var.trace_add("write", on_theme_change)
            
            theme_menu = ctk.CTkOptionMenu(
                theme_frame,
                values=["light", "dark"],
                variable=theme_var
            )
            theme_menu.pack(side="left", padx=5)
            
            # Terminal Font Settings
            font_frame = ctk.CTkFrame(container)
            font_frame.pack(fill="x", pady=10)
            
            ctk.CTkLabel(font_frame, text="Terminal Font Size:").pack(anchor="w", padx=5, pady=2)
            font_size_var = tk.IntVar(value=self.preferences.get("terminal_font_size", 10))
            font_size_slider = ctk.CTkSlider(
                font_frame, 
                from_=8, 
                to=24, 
                number_of_steps=16,
                variable=font_size_var
            )
            font_size_slider.pack(fill="x", padx=20, pady=(0, 10))
            
            # Font size label
            size_label = ctk.CTkLabel(font_frame, text=f"Size: {font_size_var.get()}")
            size_label.pack(anchor="w", padx=20)
            
            def update_size_label(*args):
                size_label.configure(text=f"Size: {font_size_var.get()}")
            
            font_size_var.trace_add("write", update_size_label)
            
            ctk.CTkLabel(font_frame, text="Terminal Font Family:").pack(anchor="w", padx=5, pady=(10, 2))
            font_family_var = tk.StringVar(value=self.preferences.get("terminal_font_family", "Monospace"))
            
            # Common monospace fonts
            monospace_fonts = [
                "Monospace",
                "Courier",
                "DejaVu Sans Mono",
                "Liberation Mono",
                "Ubuntu Mono",
                "Consolas"
            ]
            
            font_family_menu = ctk.CTkOptionMenu(
                font_frame,
                values=monospace_fonts,
                variable=font_family_var
            )
            font_family_menu.pack(fill="x", padx=20, pady=2)
            
            # Preview
            preview_frame = ctk.CTkFrame(container)
            preview_frame.pack(fill="x", pady=15)
            
            ctk.CTkLabel(preview_frame, text="Preview:").pack(anchor="w", padx=5, pady=2)
            preview_text = ctk.CTkTextbox(
                preview_frame,
                height=100,
                wrap="word"
            )
            preview_text.pack(fill="x", padx=5, pady=5)
            preview_text.insert("1.0", "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n1234567890\n\nNote: Font changes will take effect in newly opened terminal tabs.")
            preview_text.configure(state="disabled")
            
            def update_preview(*args):
                try:
                    size = font_size_var.get()
                    family = font_family_var.get()
                    preview_text.configure(font=(family, size))
                except Exception as e:
                    self.logger.error(f"Error updating preview: {e}")
            
            font_size_var.trace_add("write", update_preview)
            font_family_var.trace_add("write", update_preview)
            update_preview()
            
            # Buttons
            button_frame = ctk.CTkFrame(container)
            button_frame.pack(side="bottom", fill="x", pady=(20, 0))
            
            def save():
                try:
                    # Validate font size
                    font_size = font_size_var.get()
                    if not 8 <= font_size <= 24:
                        messagebox.showerror("Error", "Font size must be between 8 and 24")
                        return
                    
                    # Save preferences
                    self.preferences.update({
                        "theme": theme_var.get(),
                        "terminal_font_size": font_size,
                        "terminal_font_family": font_family_var.get()
                    })
                    self.save_preferences()
                    
                    # Now apply theme permanently
                    self.apply_theme(theme_var.get())
                    
                    # Update all terminal outputs with new font
                    if hasattr(self, 'terminal_outputs'):
                        for terminal in self.terminal_outputs.values():
                            if terminal:
                                terminal.configure(font=(font_family_var.get(), font_size))
                    
                    messagebox.showinfo("Success", "Preferences saved successfully")
                    dialog.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to save preferences: {str(e)}")
            
            def cancel():
                # Restore all original settings
                self.apply_theme(original_settings["theme"])
                font_size_var.set(original_settings["terminal_font_size"])
                font_family_var.set(original_settings["terminal_font_family"])
                
                # Update preview
                update_preview()
                
                dialog.destroy()
            
            save_button = ctk.CTkButton(
                button_frame,
                text="Save",
                command=save,
                width=100
            )
            save_button.pack(side="right", padx=5)
            
            cancel_button = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=cancel,
                width=100
            )
            cancel_button.pack(side="right", padx=5)
            
            # Center the dialog
            dialog.update_idletasks()
            width = dialog.winfo_width()
            height = dialog.winfo_height()
            x = (dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (dialog.winfo_screenheight() // 2) - (height // 2)
            dialog.geometry(f"{width}x{height}+{x}+{y}")
            
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.focus_set()
            
        except Exception as e:
            self.logger.error(f"Error showing preferences: {e}")
            messagebox.showerror("Error", f"Could not show preferences: {str(e)}")

    def _strip_ansi_codes(self, text: str) -> str:
        """Remove ANSI escape sequences from text.
        
        Args:
            text (str): Text containing ANSI escape sequences
            
        Returns:
            str: Clean text without ANSI escape sequences
        """
        # Pattern matches all ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def _configure_scrollable_frame(self, content_frame, dialog):
        """Configure advanced scrolling for touchpad and mouse wheel support."""
        def _scroll_handler(event):
            """Advanced scroll handler for multiple input methods."""
            # Determine scroll direction and amount
            if event.type == '4':  # ButtonPress (Linux)
                if event.num == 4:  # Scroll up
                    content_frame.yview_scroll(-3, "units")
                elif event.num == 5:  # Scroll down
                    content_frame.yview_scroll(3, "units")
            elif event.type == '5':  # ButtonRelease (Linux)
                return
            elif event.type == '38':  # MouseWheel (Windows/Mac)
                # Normalize scroll amount
                amount = int(-1 * (event.delta / 40))
                content_frame.yview_scroll(amount, "units")
            
            return "break"

        # Bind multiple event types for cross-platform compatibility
        content_frame.bind('<Button-4>', _scroll_handler)  # Linux scroll up
        content_frame.bind('<Button-5>', _scroll_handler)  # Linux scroll down
        content_frame.bind('<MouseWheel>', _scroll_handler)  # Windows/Mac
        
        # Ensure focus can be set to enable scrolling
        content_frame.bind('<Enter>', lambda e: content_frame.focus_set())
        
        # Optional: Add trackpad-like smooth scrolling
        dialog.bind('<2>', lambda e: content_frame.yview_moveto(0))  # Middle click reset
        
        return content_frame

    def apply_theme(self, theme_name: str):
        """
        Apply the specified theme to the entire application with comprehensive updates.
        
        Args:
            theme_name (str): Name of the theme to apply ('light' or 'dark')
        """
        try:
            # Prevent multiple simultaneous theme updates
            if hasattr(self, '_theme_update_in_progress'):
                return
            
            # Set theme update flag
            self._theme_update_in_progress = True
            
            # Validate theme
            if theme_name not in ["light", "dark"]:
                self.logger.warning(f"Invalid theme: {theme_name}")
                return
            
            # Update theme in preferences and global CustomTkinter setting
            self.preferences['theme'] = theme_name
            self.current_theme = theme_name
            ctk.set_appearance_mode(theme_name)
            
            theme_colors = self.themes[theme_name]
            
            # Update sidebar components
            if hasattr(self, 'sidebar_frame'):
                self.sidebar_frame.configure(fg_color=theme_colors['bg'])
                
                # Update search frame and its children
                for child in self.sidebar_frame.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        child.configure(fg_color=theme_colors['bg'])
                        for subchild in child.winfo_children():
                            if isinstance(subchild, ctk.CTkEntry):
                                subchild.configure(
                                    fg_color=theme_colors['entry'],
                                    text_color=theme_colors['fg']
                                )
                            elif isinstance(subchild, ctk.CTkButton):
                                subchild.configure(
                                    fg_color=theme_colors['button'],
                                    hover_color=theme_colors['button_hover'],
                                    text_color=theme_colors['fg']
                                )
            
            # Update session container and buttons
            if hasattr(self, 'session_container'):
                self.session_container.configure(fg_color=theme_colors['bg'])
                for child in self.session_container.winfo_children():
                    if isinstance(child, ctk.CTkFrame):
                        child.configure(fg_color=theme_colors['bg'])
                        for button in child.winfo_children():
                            if isinstance(button, ctk.CTkButton):
                                button.configure(
                                    fg_color=theme_colors['button'],
                                    hover_color=theme_colors['button_hover'],
                                    text_color=theme_colors['fg']
                                )
            
            # Update terminal outputs with proper attribute check
            if hasattr(self, 'terminal_outputs') and self.terminal_outputs:
                for session_name, terminal in self.terminal_outputs.items():
                    try:
                        if terminal and hasattr(terminal, 'configure'):
                            terminal.configure(
                                bg=theme_colors['terminal_bg'],
                                fg=theme_colors['terminal_fg'],
                                insertbackground=theme_colors['fg']
                            )
                    except Exception as e:
                        self.logger.error(f"Error updating terminal for {session_name}: {e}")
            
            # Update command inputs with proper attribute check
            if hasattr(self, 'command_inputs') and self.command_inputs:
                for command_input in self.command_inputs.values():
                    try:
                        if command_input and hasattr(command_input, 'configure'):
                            command_input.configure(
                                fg_color=theme_colors['entry'],
                                text_color=theme_colors['fg']
                            )
                    except Exception as e:
                        self.logger.error(f"Error updating command input: {e}")
            
            # Force UI refresh
            self.root.update_idletasks()
            
            # Save preferences
            self.save_preferences()
            
            self.logger.info(f"Theme switched to {theme_name}")
        
        except Exception as e:
            error_msg = f"Comprehensive theme update failed: {e}"
            self.logger.error(error_msg)
            messagebox.showerror("Theme Update Error", error_msg)
        
        finally:
            # Always clear the theme update flag
            if hasattr(self, '_theme_update_in_progress'):
                delattr(self, '_theme_update_in_progress')

def suppress_system_messages():
    """
    Suppress system messages and login information from being displayed.
    This method uses ctypes to modify the file descriptors.
    """
    try:
        # Redirect stdout and stderr to /dev/null
        libc = ctypes.CDLL('libc.so.6')
        
        # Open /dev/null
        dev_null = os.open('/dev/null', os.O_WRONLY)
        
        # Redirect stdout and stderr
        libc.dup2(dev_null, 1)  # stdout
        libc.dup2(dev_null, 2)  # stderr
        
        # Close the original file descriptor
        os.close(dev_null)
    except Exception as e:
        print(f"Could not suppress system messages: {e}")

def main():
    # Suppress system messages before creating the application
    suppress_system_messages()
    
    root = ctk.CTk()
    
    # Add CustomTkinter theme settings
    ctk.set_appearance_mode("dark")  # Options: "dark", "light", or "system"
    ctk.set_default_color_theme("blue")  # Built-in themes: "blue", "dark-blue", "green"
    
    app = ModernSSHClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()