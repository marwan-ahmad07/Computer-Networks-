# Email Client GUI - Refactored with Queue-Based Threading
# Computer Networks Lab 2 - Professional Engineering Edition
# Alexandria University

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import sys
import subprocess
import platform
import queue
from datetime import datetime

# Try to import plyer for notifications
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("WARNING: plyer not installed. Using system notifications instead.")

from send_email import send_email, get_smtp_server
from receive_email import receive_latest_email, get_imap_server


class QueuedStreamCapture:
    """Captures stdout/stderr and sends to a queue for thread-safe GUI updates"""
    
    def __init__(self, original_stream, message_queue, stream_type='stdout'):
        self.original_stream = original_stream
        self.message_queue = message_queue
        self.stream_type = stream_type
    
    def write(self, data):
        # Write to original stream (terminal)
        self.original_stream.write(data)
        self.original_stream.flush()
        
        # Send to queue for GUI update (non-blocking)
        if data.strip():  # Only queue non-empty strings
            try:
                self.message_queue.put_nowait(('log', data))
            except queue.Full:
                pass  # Queue full, skip this update
    
    def flush(self):
        self.original_stream.flush()


class EmailClientGUI:
    """Professional Email Client GUI with thread-safe queue-based communication"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Email Client - Computer Networks Lab 2 ")
        self.root.geometry("1000x850")
        self.root.resizable(True, True)
        
        # Message queue for thread-to-GUI communication (CRITICAL for thread safety)
        self.message_queue = queue.Queue(maxsize=1000)
        
        # Threading state
        self.send_cancel_event = threading.Event()
        self.receive_cancel_event = threading.Event()
        self.is_sending = False
        self.is_receiving = False
        
        # Auto-refresh state
        self.auto_refresh_enabled = False
        self.last_subject = ""
        
        # Apply modern theme FIRST
        self.apply_modern_theme()
        
        # Build GUI components
        self.create_widgets()
        
        # Start queue polling (CRITICAL - this enables thread-safe updates)
        self.poll_message_queue()
        
        # Redirect stdout/stderr to queue
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = QueuedStreamCapture(self.original_stdout, self.message_queue, 'stdout')
        sys.stderr = QueuedStreamCapture(self.original_stderr, self.message_queue, 'stderr')
    
    def apply_modern_theme(self):
        """Apply Alexandria University Blue professional theme"""
        
        style = ttk.Style()
        
        # Use 'clam' as base (best for customization)
        style.theme_use('clam')
        
        # Alexandria University Blue color scheme
        AU_BLUE = '#003366'  # Dark blue
        AU_LIGHT_BLUE = '#0066CC'  # Lighter blue
        AU_ACCENT = '#FFD700'  # Gold accent
        BG_DARK = '#1E1E1E'  # Dark background
        BG_LIGHT = '#2D2D30'  # Lighter dark background
        FG_WHITE = '#FFFFFF'  # White text
        FG_GRAY = '#CCCCCC'  # Gray text
        
        # Configure root window
        self.root.configure(bg=BG_DARK)
        
        # Notebook (tabs)
        style.configure('TNotebook', background=BG_DARK, borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=BG_LIGHT, 
                       foreground=FG_GRAY,
                       padding=[20, 10],
                       font=('Arial', 10, 'bold'))
        style.map('TNotebook.Tab',
                 background=[('selected', AU_BLUE)],
                 foreground=[('selected', FG_WHITE)])
        
        # Frames
        style.configure('TFrame', background=BG_DARK)
        style.configure('Card.TFrame', background=BG_LIGHT, relief='raised')
        
        # Labels
        style.configure('TLabel', 
                       background=BG_DARK, 
                       foreground=FG_GRAY,
                       font=('Arial', 10))
        style.configure('Title.TLabel',
                       background=BG_DARK,
                       foreground=AU_ACCENT,
                       font=('Arial', 18, 'bold'))
        style.configure('Subtitle.TLabel',
                       background=BG_LIGHT,
                       foreground=FG_WHITE,
                       font=('Arial', 11))
        
        # Buttons
        style.configure('TButton',
                       background=AU_LIGHT_BLUE,
                       foreground=FG_WHITE,
                       borderwidth=0,
                       focuscolor='none',
                       padding=[15, 8],
                       font=('Arial', 10, 'bold'))
        style.map('TButton',
                 background=[('active', AU_BLUE), ('pressed', AU_BLUE)])
        
        style.configure('Action.TButton',
                       background=AU_LIGHT_BLUE,
                       foreground=FG_WHITE,
                       font=('Arial', 11, 'bold'),
                       padding=[20, 10])
        
        style.configure('Danger.TButton',
                       background='#CC0000',
                       foreground=FG_WHITE,
                       font=('Arial', 10, 'bold'))
        style.map('Danger.TButton',
                 background=[('active', '#990000')])
        
        # LabelFrame
        style.configure('TLabelframe',
                       background=BG_LIGHT,
                       foreground=AU_ACCENT,
                       borderwidth=2,
                       relief='solid')
        style.configure('TLabelframe.Label',
                       background=BG_LIGHT,
                       foreground=AU_ACCENT,
                       font=('Arial', 11, 'bold'))
        
        # Entry fields
        style.configure('TEntry',
                       fieldbackground='#3C3C3C',
                       foreground=FG_WHITE,
                       borderwidth=1,
                       insertcolor=FG_WHITE)
        
        # Checkbutton
        style.configure('TCheckbutton',
                       background=BG_LIGHT,
                       foreground=FG_GRAY,
                       font=('Arial', 10))
        
        # Progress bar
        style.configure('TProgressbar',
                       background=AU_LIGHT_BLUE,
                       troughcolor=BG_LIGHT,
                       borderwidth=0,
                       thickness=20)
    
    def create_widgets(self):
        """Create all GUI components with modern layout"""
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 15))
        
        title_label = ttk.Label(header_frame,
                               text="Email Client",
                               style='Title.TLabel')
        title_label.pack(side='left')
        
        subtitle_label = ttk.Label(header_frame,
                                   text="Computer Networks Lab 2",
                                   foreground='#999999',
                                   font=('Arial', 10))
        subtitle_label.pack(side='left', padx=(15, 0))
        
        # Tabbed interface
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Create tabs
        self.send_tab = ttk.Frame(self.notebook)
        self.receive_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.send_tab, text='  Send Email  ')
        self.notebook.add(self.receive_tab, text='  Receive Email  ')
        
        # Build each tab
        self.build_send_tab()
        self.build_receive_tab()
    
    def build_send_tab(self):
        """Build the send email tab with modern design"""
        
        # Scrollable container
        canvas = tk.Canvas(self.send_tab, bg='#1E1E1E', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.send_tab, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Input section
        input_frame = ttk.LabelFrame(scrollable_frame, 
                                    text=" Compose Email ",
                                    padding=20)
        input_frame.pack(fill='both', expand=False, padx=20, pady=20)
        
        # Create form fields
        fields = [
            ("From Email:", "send_from_email", False, None),
            ("Password:", "send_password", True, None),
            ("To Email:", "send_to_email", False, None),
            ("Subject:", "send_subject", False, None),
        ]
        
        for idx, (label_text, attr_name, is_password, _) in enumerate(fields):
            label = ttk.Label(input_frame, text=label_text)
            label.grid(row=idx, column=0, sticky='w', pady=8, padx=(0, 10))
            
            entry = ttk.Entry(input_frame, width=55, font=('Arial', 10))
            if is_password:
                entry.config(show='*')
            entry.grid(row=idx, column=1, pady=8, sticky='ew')
            setattr(self, attr_name, entry)
        
        # Body field
        body_label = ttk.Label(input_frame, text="Body:")
        body_label.grid(row=4, column=0, sticky='nw', pady=8, padx=(0, 10))
        
        self.send_body = scrolledtext.ScrolledText(input_frame, 
                                                   width=55, height=8,
                                                   font=('Arial', 10),
                                                   bg='#3C3C3C',
                                                   fg='#FFFFFF',
                                                   insertbackground='#FFFFFF',
                                                   wrap=tk.WORD)
        self.send_body.grid(row=4, column=1, pady=8, sticky='ew')
        
        # SMTP Server (Advanced)
        smtp_label = ttk.Label(input_frame, text="SMTP Server:")
        smtp_label.grid(row=5, column=0, sticky='w', pady=8, padx=(0, 10))
        
        smtp_container = ttk.Frame(input_frame)
        smtp_container.grid(row=5, column=1, sticky='ew', pady=8)
        
        self.send_smtp_server = ttk.Entry(smtp_container, width=38, font=('Arial', 9))
        self.send_smtp_server.pack(side='left', padx=(0, 10))
        
        port_label = ttk.Label(smtp_container, text="Port:")
        port_label.pack(side='left', padx=(0, 5))
        
        self.send_smtp_port = ttk.Entry(smtp_container, width=8, font=('Arial', 9))
        self.send_smtp_port.insert(0, "587")
        self.send_smtp_port.pack(side='left')
        
        input_frame.columnconfigure(1, weight=1)
        
        # Progress bar (hidden initially)
        self.send_progress_frame = ttk.Frame(scrollable_frame)
        self.send_progress_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.send_progress = ttk.Progressbar(self.send_progress_frame,
                                            mode='indeterminate',
                                            length=300)
        self.send_progress.pack(fill='x')
        self.send_progress_frame.pack_forget()  # Hide initially
        
        # Buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.send_button = ttk.Button(button_frame,
                                      text="Send Email",
                                      style='Action.TButton',
                                      command=self.send_email_action)
        self.send_button.pack(side='left', padx=(0, 10))
        
        self.terminate_send_button = ttk.Button(button_frame,
                                               text="Terminate",
                                               style='Danger.TButton',
                                               command=self.terminate_send_action,
                                               state='disabled')
        self.terminate_send_button.pack(side='left')
        
        # Status label
        self.send_status = tk.Label(button_frame,
                                   text="",
                                   font=('Arial', 11, 'bold'),
                                   bg='#1E1E1E',
                                   fg='#CCCCCC')
        self.send_status.pack(side='right', padx=10)
        
        # Console output
        console_frame = ttk.LabelFrame(scrollable_frame,
                                      text=" Console Output ",
                                      padding=15)
        console_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.send_console = scrolledtext.ScrolledText(console_frame,
                                                      width=80, height=10,
                                                      font=('Consolas', 9),
                                                      bg='#0C0C0C',
                                                      fg='#00FF00',
                                                      insertbackground='#00FF00',
                                                      wrap=tk.WORD)
        self.send_console.pack(fill='both', expand=True)
        self.send_console.config(state='disabled')
    
    def build_receive_tab(self):
        """Build the receive email tab with modern design"""
        
        # Scrollable container
        canvas = tk.Canvas(self.receive_tab, bg='#1E1E1E', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.receive_tab, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Credentials section
        cred_frame = ttk.LabelFrame(scrollable_frame,
                                   text=" Account Credentials ",
                                   padding=20)
        cred_frame.pack(fill='x', padx=20, pady=20)
        
        # Email
        email_label = ttk.Label(cred_frame, text="Email:")
        email_label.grid(row=0, column=0, sticky='w', pady=8, padx=(0, 10))
        
        self.receive_email_entry = ttk.Entry(cred_frame, width=55, font=('Arial', 10))
        self.receive_email_entry.grid(row=0, column=1, pady=8, sticky='ew')
        
        # Password
        pass_label = ttk.Label(cred_frame, text="Password:")
        pass_label.grid(row=1, column=0, sticky='w', pady=8, padx=(0, 10))
        
        self.receive_password = ttk.Entry(cred_frame, width=55, show='*', font=('Arial', 10))
        self.receive_password.grid(row=1, column=1, pady=8, sticky='ew')
        
        # IMAP Server
        imap_label = ttk.Label(cred_frame, text="IMAP Server:")
        imap_label.grid(row=2, column=0, sticky='w', pady=8, padx=(0, 10))
        
        imap_container = ttk.Frame(cred_frame)
        imap_container.grid(row=2, column=1, sticky='ew', pady=8)
        
        self.receive_imap_server = ttk.Entry(imap_container, width=38, font=('Arial', 9))
        self.receive_imap_server.pack(side='left', padx=(0, 10))
        
        port_label = ttk.Label(imap_container, text="Port:")
        port_label.pack(side='left', padx=(0, 5))
        
        self.receive_imap_port = ttk.Entry(imap_container, width=8, font=('Arial', 9))
        self.receive_imap_port.insert(0, "993")
        self.receive_imap_port.pack(side='left')
        
        cred_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        self.receive_progress_frame = ttk.Frame(scrollable_frame)
        self.receive_progress_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        self.receive_progress = ttk.Progressbar(self.receive_progress_frame,
                                               mode='indeterminate',
                                               length=300)
        self.receive_progress.pack(fill='x')
        self.receive_progress_frame.pack_forget()
        
        # Buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        self.receive_button = ttk.Button(button_frame,
                                        text="Fetch Latest Email",
                                        style='Action.TButton',
                                        command=self.receive_email_action)
        self.receive_button.pack(side='left', padx=(0, 10))
        
        self.terminate_receive_button = ttk.Button(button_frame,
                                                  text="Terminate",
                                                  style='Danger.TButton',
                                                  command=self.terminate_receive_action,
                                                  state='disabled')
        self.terminate_receive_button.pack(side='left', padx=(0, 15))
        
        # Auto-refresh
        self.auto_refresh_var = tk.BooleanVar()
        self.auto_refresh_check = ttk.Checkbutton(button_frame,
                                                 text="Auto-refresh (30s)",
                                                 variable=self.auto_refresh_var,
                                                 command=self.toggle_auto_refresh)
        self.auto_refresh_check.pack(side='left')
        
        # Email display
        display_frame = ttk.LabelFrame(scrollable_frame,
                                      text=" Email Content ",
                                      padding=15)
        display_frame.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        
        self.receive_display = scrolledtext.ScrolledText(display_frame,
                                                         width=80, height=12,
                                                         font=('Arial', 10),
                                                         bg='#2D2D30',
                                                         fg='#FFFFFF',
                                                         insertbackground='#FFFFFF',
                                                         wrap=tk.WORD)
        self.receive_display.pack(fill='both', expand=True)
        self.receive_display.config(state='disabled')
        
        # Console output
        console_frame = ttk.LabelFrame(scrollable_frame,
                                      text=" Console Output ",
                                      padding=15)
        console_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        self.receive_console = scrolledtext.ScrolledText(console_frame,
                                                         width=80, height=8,
                                                         font=('Consolas', 9),
                                                         bg='#0C0C0C',
                                                         fg='#00FF00',
                                                         insertbackground='#00FF00',
                                                         wrap=tk.WORD)
        self.receive_console.pack(fill='both', expand=True)
        self.receive_console.config(state='disabled')
    
    def poll_message_queue(self):
        """
        CRITICAL: Poll the message queue periodically for thread-to-GUI communication.
        This method runs on the main thread and safely updates the GUI.
        """
        try:
            # Process all pending messages (non-blocking)
            while True:
                try:
                    msg_type, data = self.message_queue.get_nowait()
                    
                    if msg_type == 'log':
                        # Update appropriate console based on current state
                        if self.is_sending:
                            self._append_to_console(self.send_console, data)
                        if self.is_receiving:
                            self._append_to_console(self.receive_console, data)
                    
                    elif msg_type == 'send_complete':
                        success, email_details = data
                        self._handle_send_complete(success, email_details)
                    
                    elif msg_type == 'receive_complete':
                        email_details = data
                        self._handle_receive_complete(email_details)
                    
                    elif msg_type == 'notification':
                        title, message, timeout = data
                        self._show_notification_main_thread(title, message, timeout)
                    
                except queue.Empty:
                    break  # No more messages
        
        except Exception as e:
            print(f"[ERROR] Queue polling exception: {e}")
        
        # Schedule next poll (every 100ms)
        self.root.after(100, self.poll_message_queue)
    
    def _append_to_console(self, console_widget, text):
        """Safely append text to console widget"""
        console_widget.config(state='normal')
        console_widget.insert(tk.END, text)
        console_widget.see(tk.END)
        console_widget.config(state='disabled')
    
    def send_email_action(self):
        """Handle send email button click"""
        
        # Get input values
        from_email = self.send_from_email.get().strip()
        password = self.send_password.get().strip()
        to_email = self.send_to_email.get().strip()
        subject = self.send_subject.get().strip()
        body = self.send_body.get('1.0', tk.END).strip()
        smtp_server = self.send_smtp_server.get().strip() or None
        smtp_port = None
        
        if self.send_smtp_port.get().strip():
            try:
                smtp_port = int(self.send_smtp_port.get().strip())
            except ValueError:
                smtp_port = 587
        
        # Validate required fields
        if not from_email or not password or not to_email:
            messagebox.showerror("Missing Information",
                               "Please fill in all required fields:\n\n• From Email\n• Password\n• To Email")
            return
        
        # Prepare for sending
        self.send_cancel_event.clear()
        self.is_sending = True
        
        self.send_button.config(state='disabled')
        self.terminate_send_button.config(state='normal')
        self.send_status.config(text="Sending...", fg='#FFD700')
        
        # Show progress bar
        self.send_progress_frame.pack(fill='x', padx=20, pady=(0, 10))
        self.send_progress.start(10)
        
        # Clear and prepare console
        self.send_console.config(state='normal')
        self.send_console.delete('1.0', tk.END)
        self.send_console.insert('1.0', f"[{self._get_timestamp()}] Starting email send operation...\n")
        self.send_console.config(state='disabled')
        
        # Start send thread
        def send_thread():
            try:
                print(f"\n{'='*60}")
                print(f"[SEND] Initiating SMTP connection...")
                print(f"{'='*60}")
                
                # Check cancellation
                if self.send_cancel_event.is_set():
                    self.message_queue.put(('log', "\n[CANCELLED] Operation terminated by user\n"))
                    self.message_queue.put(('send_complete', (False, {'to': to_email, 'cancelled': True})))
                    return
                
                # Send email
                success = send_email(from_email, password, to_email, subject, body,
                                   smtp_server, smtp_port)
                
                # Check if cancelled during send
                if self.send_cancel_event.is_set():
                    self.message_queue.put(('log', "\n[CANCELLED] Operation terminated during send\n"))
                    self.message_queue.put(('send_complete', (False, {'to': to_email, 'cancelled': True})))
                    return
                
                # Send completion message to queue
                self.message_queue.put(('send_complete', (success, {'to': to_email, 'subject': subject})))
                
            except Exception as e:
                import traceback
                error_msg = f"\n[EXCEPTION] {type(e).__name__}: {e}\n"
                error_msg += f"\nStack trace:\n{traceback.format_exc()}\n"
                self.message_queue.put(('log', error_msg))
                self.message_queue.put(('send_complete', (False, {'to': to_email, 'error': str(e)})))
        
        threading.Thread(target=send_thread, daemon=True).start()
    
    def _handle_send_complete(self, success, email_details):
        """Handle send completion on main thread"""
        
        self.is_sending = False
        self.send_button.config(state='normal')
        self.terminate_send_button.config(state='disabled')
        
        # Stop and hide progress bar
        self.send_progress.stop()
        self.send_progress_frame.pack_forget()
        
        # Append completion message
        timestamp = self._get_timestamp()
        self._append_to_console(self.send_console, f"\n[{timestamp}] --- Operation Complete ---\n")
        
        # Handle cancellation
        if email_details.get('cancelled'):
            self.send_status.config(text="Cancelled", fg='#FF9900')
            messagebox.showwarning("Operation Cancelled",
                                 "Send operation was terminated by user.")
            return
        
        # Handle success/failure
        if success:
            self.send_status.config(text="Email Sent Successfully!", fg='#00FF00')
            messagebox.showinfo("Success",
                              f"Email sent successfully to:\n{email_details.get('to', '')}")
            
            # Queue notification (will be shown on main thread)
            self.message_queue.put(('notification', (
                "Email Sent",
                f"Email sent to {email_details.get('to', 'recipient')}",
                5
            )))
        else:
            self.send_status.config(text="Send Failed", fg='#FF0000')
            error_msg = email_details.get('error', 'Unknown error occurred')
            messagebox.showerror("Send Failed",
                               f"Failed to send email.\n\nError: {error_msg}\n\nCheck console output for details.")
    
    def terminate_send_action(self):
        """Handle terminate button for send"""
        if self.is_sending:
            self.send_cancel_event.set()
            self.send_status.config(text="Terminating...", fg='#FF9900')
            self._append_to_console(self.send_console, f"\n[{self._get_timestamp()}] [SYSTEM] Termination requested...\n")
    
    def receive_email_action(self):
        """Handle receive email button click"""
        
        # Get credentials
        email_addr = self.receive_email_entry.get().strip()
        password = self.receive_password.get().strip()
        imap_server = self.receive_imap_server.get().strip() or None
        imap_port = None
        
        if self.receive_imap_port.get().strip():
            try:
                imap_port = int(self.receive_imap_port.get().strip())
            except ValueError:
                imap_port = 993
        
        # Validate
        if not email_addr or not password:
            messagebox.showerror("Missing Information",
                               "Please enter email and password!")
            return
        
        # Prepare for receiving
        self.receive_cancel_event.clear()
        self.is_receiving = True
        
        self.receive_button.config(state='disabled')
        self.terminate_receive_button.config(state='normal')
        
        # Show progress bar
        self.receive_progress_frame.pack(fill='x', padx=20, pady=(0, 10))
        self.receive_progress.start(10)
        
        # Clear displays
        self.receive_display.config(state='normal')
        self.receive_display.delete('1.0', tk.END)
        self.receive_display.insert('1.0', "Fetching email...\n")
        self.receive_display.config(state='disabled')
        
        self.receive_console.config(state='normal')
        self.receive_console.delete('1.0', tk.END)
        self.receive_console.insert('1.0', f"[{self._get_timestamp()}] Starting email fetch operation...\n")
        self.receive_console.config(state='disabled')
        
        # Start receive thread
        def receive_thread():
            try:
                print(f"\n{'='*60}")
                print(f"[RECEIVE] Initiating IMAP connection...")
                print(f"{'='*60}")
                
                # Check cancellation
                if self.receive_cancel_event.is_set():
                    self.message_queue.put(('log', "\n[CANCELLED] Operation terminated by user\n"))
                    self.message_queue.put(('receive_complete', {'cancelled': True}))
                    return
                
                # Receive email
                email_details = receive_latest_email(email_addr, password, imap_server, imap_port)
                
                # Check if cancelled during receive
                if self.receive_cancel_event.is_set():
                    self.message_queue.put(('log', "\n[CANCELLED] Operation terminated during fetch\n"))
                    self.message_queue.put(('receive_complete', {'cancelled': True}))
                    return
                
                # Send result to queue
                if email_details:
                    self.message_queue.put(('receive_complete', email_details))
                else:
                    self.message_queue.put(('receive_complete', {'failed': True}))
                
            except Exception as e:
                import traceback
                error_msg = f"\n[EXCEPTION] {type(e).__name__}: {e}\n"
                error_msg += f"\nStack trace:\n{traceback.format_exc()}\n"
                self.message_queue.put(('log', error_msg))
                self.message_queue.put(('receive_complete', {'failed': True, 'error': str(e)}))
        
        threading.Thread(target=receive_thread, daemon=True).start()
    
    def _handle_receive_complete(self, email_details):
        """Handle receive completion on main thread"""
        
        self.is_receiving = False
        self.receive_button.config(state='normal')
        self.terminate_receive_button.config(state='disabled')
        
        # Stop and hide progress bar
        self.receive_progress.stop()
        self.receive_progress_frame.pack_forget()
        
        # Append completion message
        timestamp = self._get_timestamp()
        self._append_to_console(self.receive_console, f"\n[{timestamp}] --- Operation Complete ---\n")
        
        # Handle cancellation
        if email_details.get('cancelled'):
            self.receive_display.config(state='normal')
            self.receive_display.delete('1.0', tk.END)
            self.receive_display.insert('1.0', "Receive operation cancelled by user.")
            self.receive_display.config(state='disabled')
            messagebox.showwarning("Operation Cancelled",
                                 "Receive operation was terminated by user.")
            return
        
        # Handle failure
        if email_details.get('failed'):
            self.receive_display.config(state='normal')
            self.receive_display.delete('1.0', tk.END)
            self.receive_display.insert('1.0', "Failed to fetch email.\n\nSee console output for details.")
            self.receive_display.config(state='disabled')
            
            error_msg = email_details.get('error', 'Unknown error occurred')
            messagebox.showerror("Fetch Failed",
                               f"Failed to fetch email.\n\nError: {error_msg}\n\nCheck console output for details.")
            return
        
        # Handle success - display email
        display_text = f"""
{'-'*70}
EMAIL DETAILS
{'-'*70}

FROM:     {email_details.get('from', 'Unknown')}

SUBJECT:  {email_details.get('subject', 'No Subject')}

DATE:     {email_details.get('date', 'Unknown Date')}

{'-'*70}
BODY:
{'-'*70}

{email_details.get('body', 'No body content')}

{'-'*70}
        """.strip()
        
        self.receive_display.config(state='normal')
        self.receive_display.delete('1.0', tk.END)
        self.receive_display.insert('1.0', display_text)
        self.receive_display.config(state='disabled')
        
        # Queue notification
        self.message_queue.put(('notification', (
            "Email Received",
            f"From: {email_details.get('from', 'Unknown')[:30]}...\nSubject: {email_details.get('subject', 'No subject')[:30]}...",
            10
        )))
    
    def terminate_receive_action(self):
        """Handle terminate button for receive"""
        if self.is_receiving:
            self.receive_cancel_event.set()
            self._append_to_console(self.receive_console, f"\n[{self._get_timestamp()}] [SYSTEM] Termination requested...\n")
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh feature"""
        
        if self.auto_refresh_var.get():
            self.auto_refresh_enabled = True
            self.start_auto_refresh()
            messagebox.showinfo("Auto-Refresh Enabled",
                              "Auto-refresh is now active!\n\nYou'll receive notifications for new emails every 30 seconds.")
        else:
            self.auto_refresh_enabled = False
            messagebox.showinfo("Auto-Refresh Disabled",
                              "Auto-refresh has been turned off.")
    
    def start_auto_refresh(self):
        """Start auto-refresh background thread"""
        
        def auto_refresh_loop():
            while self.auto_refresh_enabled:
                time.sleep(30)  # Check every 30 seconds
                
                if not self.auto_refresh_enabled:
                    break
                
                # Get credentials
                email_addr = self.receive_email_entry.get().strip()
                password = self.receive_password.get().strip()
                
                if not email_addr or not password:
                    continue
                
                try:
                    # Fetch silently
                    imap_server = self.receive_imap_server.get().strip() or None
                    imap_port = None
                    if self.receive_imap_port.get().strip():
                        try:
                            imap_port = int(self.receive_imap_port.get().strip())
                        except:
                            imap_port = 993
                    
                    result = receive_latest_email(email_addr, password, imap_server, imap_port)
                    
                    if result:
                        # Check if it's a new email
                        if result.get('subject') != self.last_subject:
                            self.last_subject = result.get('subject', '')
                            
                            # Queue notification
                            self.message_queue.put(('notification', (
                                "New Email Arrived!",
                                f"From: {result.get('from', 'Unknown')[:40]}\nSubject: {result.get('subject', 'No subject')[:40]}",
                                15
                            )))
                
                except Exception as e:
                    print(f"[Auto-refresh] Error: {e}")
        
        threading.Thread(target=auto_refresh_loop, daemon=True).start()
    
    def _show_notification_main_thread(self, title, message, timeout):
        """Show notification - MUST run on main thread"""
        
        # Try plyer first
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout
                )
                print(f"[NOTIFICATION] {title}: {message}")
                return
            except Exception as e:
                print(f"[WARNING] Plyer notification failed: {e}")
        
        # Fallback to OS-specific methods
        try:
            if platform.system() == 'Darwin':  # macOS
                script = f'display notification "{message}" with title "{title}"'
                subprocess.run(['osascript', '-e', script],
                             check=False,
                             capture_output=True,
                             timeout=2)
                print(f"[NOTIFICATION] {title}: {message}")
            elif platform.system() == 'Linux':
                subprocess.run(['notify-send', title, message],
                             check=False,
                             capture_output=True,
                             timeout=2)
                print(f"[NOTIFICATION] {title}: {message}")
            elif platform.system() == 'Windows':
                print(f"[NOTIFICATION] {title}: {message}")
            else:
                print(f"[NOTIFICATION] {title}: {message}")
        except Exception as e:
            print(f"[WARNING] System notification failed: {e}")
            print(f"[NOTIFICATION] {title}: {message}")
    
    def _get_timestamp(self):
        """Get formatted timestamp"""
        return datetime.now().strftime("%H:%M:%S")
    
    def __del__(self):
        """Cleanup: Restore original stdout/stderr"""
        try:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
        except:
            pass


def main():
    """Launch the email client GUI"""
    
    print("=" * 70)
    print("EMAIL CLIENT - COMPUTER NETWORKS LAB 2")
    print("Alexandria University Engineering")
    print("=" * 70)
    print()
    
    if not PLYER_AVAILABLE:
        print("WARNING: plyer not installed")
        print("    Notifications will use system fallback methods")
        print("    Install with: pip install plyer")
        print()
    
    print("Starting GUI application...")
    print("=" * 70)
    print()
    
    root = tk.Tk()
    app = EmailClientGUI(root)
    
    print("GUI launched successfully!")
    print("=" * 70)
    print()
    
    try:
        root.mainloop()
    finally:
        # Cleanup
        print("\n" + "=" * 70)
        print("Email Client closed")
        print("=" * 70)


if __name__ == "__main__":
    main()
