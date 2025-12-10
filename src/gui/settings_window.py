"""
Settings GUI for AutoSolve.
Provides a simple interface for configuring application settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import Optional, Callable

from ..config.settings import settings
from ..utils.logger import get_logger


class SettingsWindow:
    """Settings configuration window."""

    def __init__(self, parent: Optional[tk.Tk] = None):
        self.logger = get_logger(f"{__name__}.SettingsWindow")

        # Create window
        self.parent = parent
        self.window = tk.Toplevel(parent) if parent else tk.Tk()
        self.window.title("AutoSolve Settings")
        self.window.geometry("600x700")
        self.window.resizable(True, True)

        # Callback for settings changes
        self.on_settings_changed: Optional[Callable] = None

        # Variables
        self.vars = {}

        # Setup UI
        self._setup_ui()
        self._load_settings()

        # Center window
        self._center_window()

        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        """Setup the user interface."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self._create_general_tab()
        self._create_detection_tab()
        self._create_telegram_tab()
        self._create_advanced_tab()

        # Button frame
        button_frame = ttk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)

        # Buttons
        ttk.Button(button_frame, text="Test Notification",
                  command=self._test_notification).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save",
                  command=self._save_settings).pack(side='right', padx=5)
        ttk.Button(button_frame, text="Cancel",
                  command=self._on_closing).pack(side='right', padx=5)

    def _create_general_tab(self):
        """Create general settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="General")

        # Computer name
        ttk.Label(frame, text="Computer Name:").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        self.vars['computer_name'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['computer_name'], width=30).grid(
            row=0, column=1, padx=10, pady=5)
        ttk.Label(frame, text="Name shown in notifications").grid(
            row=0, column=2, sticky='w', padx=10, pady=5)

        # Monitoring mode
        ttk.Label(frame, text="Monitoring Mode:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.vars['monitoring_mode'] = tk.StringVar()
        mode_combo = ttk.Combobox(frame, textvariable=self.vars['monitoring_mode'], width=28)
        mode_combo['values'] = ('247', 'scheduled', 'manual')
        mode_combo.grid(row=1, column=1, padx=10, pady=5)
        ttk.Label(frame, text="24/7, scheduled, or manual").grid(
            row=1, column=2, sticky='w', padx=10, pady=5)

        # Auto-solve
        self.vars['enable_auto_solve'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Enable Auto-Solve (Experimental)",
                       variable=self.vars['enable_auto_solve']).grid(
            row=2, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        # Debug mode
        self.vars['debug_mode'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Debug Mode",
                       variable=self.vars['debug_mode']).grid(
            row=3, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        # Performance monitoring
        self.vars['performance_monitoring'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Performance Monitoring",
                       variable=self.vars['performance_monitoring']).grid(
            row=4, column=0, columnspan=3, sticky='w', padx=10, pady=5)

    def _create_detection_tab(self):
        """Create detection settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Detection")

        # Check interval
        ttk.Label(frame, text="Check Interval (seconds):").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        self.vars['check_interval'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['check_interval'], width=10).grid(
            row=0, column=1, padx=10, pady=5)
        ttk.Label(frame, text="How often to check for captchas").grid(
            row=0, column=2, sticky='w', padx=10, pady=5)

        # OCR confidence
        ttk.Label(frame, text="OCR Confidence Threshold:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.vars['ocr_confidence'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['ocr_confidence'], width=10).grid(
            row=1, column=1, padx=10, pady=5)
        ttk.Label(frame, text="0.0 - 1.0").grid(
            row=1, column=2, sticky='w', padx=10, pady=5)

        # YOLO confidence
        ttk.Label(frame, text="YOLO Confidence Threshold:").grid(row=2, column=0, sticky='w', padx=10, pady=5)
        self.vars['yolo_confidence'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['yolo_confidence'], width=10).grid(
            row=2, column=1, padx=10, pady=5)
        ttk.Label(frame, text="0.0 - 1.0").grid(
            row=2, column=2, sticky='w', padx=10, pady=5)

        # GPU acceleration
        self.vars['enable_gpu'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Enable GPU Acceleration",
                       variable=self.vars['enable_gpu']).grid(
            row=3, column=0, columnspan=3, sticky='w', padx=10, pady=5)

        # Max CPU usage
        ttk.Label(frame, text="Max CPU Usage (%):").grid(row=4, column=0, sticky='w', padx=10, pady=5)
        self.vars['max_cpu_usage'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['max_cpu_usage'], width=10).grid(
            row=4, column=1, padx=10, pady=5)
        ttk.Label(frame, text="CPU usage limit").grid(
            row=4, column=2, sticky='w', padx=10, pady=5)

    def _create_telegram_tab(self):
        """Create Telegram settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Telegram")

        # Bot token
        ttk.Label(frame, text="Bot Token:").grid(row=0, column=0, sticky='nw', padx=10, pady=5)
        self.vars['bot_token'] = tk.StringVar()
        token_entry = ttk.Entry(frame, textvariable=self.vars['bot_token'], width=40, show='*')
        token_entry.grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(frame, text="Show",
                  command=lambda: self._toggle_password(token_entry)).grid(
            row=0, column=2, padx=5, pady=5)

        # Chat ID
        ttk.Label(frame, text="Chat ID:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.vars['chat_id'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['chat_id'], width=40).grid(
            row=1, column=1, padx=10, pady=5)

        # Notification cooldown
        ttk.Label(frame, text="Notification Cooldown (seconds):").grid(row=2, column=0, sticky='w', padx=10, pady=5)
        self.vars['notification_cooldown'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['notification_cooldown'], width=10).grid(
            row=2, column=1, padx=10, pady=5)

        # Max retry attempts
        ttk.Label(frame, text="Max Retry Attempts:").grid(row=3, column=0, sticky='w', padx=10, pady=5)
        self.vars['max_retry_attempts'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['max_retry_attempts'], width=10).grid(
            row=3, column=1, padx=10, pady=5)

        # Retry delay
        ttk.Label(frame, text="Retry Delay (seconds):").grid(row=4, column=0, sticky='w', padx=10, pady=5)
        self.vars['retry_delay'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['retry_delay'], width=10).grid(
            row=4, column=1, padx=10, pady=5)

        # Test notification button (duplicate for convenience)
        ttk.Button(frame, text="Send Test Notification",
                  command=self._test_notification).grid(
            row=5, column=0, columnspan=3, pady=20)

    def _create_advanced_tab(self):
        """Create advanced settings tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Advanced")

        # Model path
        ttk.Label(frame, text="YOLO Model Path:").grid(row=0, column=0, sticky='w', padx=10, pady=5)
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=0, column=1, columnspan=2, sticky='ew', padx=10, pady=5)

        self.vars['model_path'] = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.vars['model_path'], width=40).pack(side='left', fill='x', expand=True)
        ttk.Button(path_frame, text="Browse",
                  command=self._browse_model).pack(side='right', padx=5)

        # Log file
        ttk.Label(frame, text="Log File:").grid(row=1, column=0, sticky='w', padx=10, pady=5)
        self.vars['log_file'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['log_file'], width=40).grid(
            row=1, column=1, columnspan=2, sticky='ew', padx=10, pady=5)

        # Screenshot settings
        ttk.Label(frame, text="Screenshot Settings:", font=('TkDefaultFont', 9, 'bold')).grid(
            row=2, column=0, columnspan=3, sticky='w', padx=10, pady=(20, 5))

        # Max screenshot age
        ttk.Label(frame, text="Max Screenshot Age (hours):").grid(row=3, column=0, sticky='w', padx=10, pady=5)
        self.vars['screenshot_age'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['screenshot_age'], width=10).grid(
            row=3, column=1, padx=10, pady=5)

        # Max screenshots stored
        ttk.Label(frame, text="Max Screenshots Stored:").grid(row=4, column=0, sticky='w', padx=10, pady=5)
        self.vars['max_screenshots'] = tk.StringVar()
        ttk.Entry(frame, textvariable=self.vars['max_screenshots'], width=10).grid(
            row=4, column=1, padx=10, pady=5)

        # Screenshot quality
        ttk.Label(frame, text="Screenshot Quality:").grid(row=5, column=0, sticky='w', padx=10, pady=5)
        self.vars['screenshot_quality'] = tk.StringVar()
        quality_scale = ttk.Scale(frame, from_=1, to=100, orient='horizontal',
                                 variable=self.vars['screenshot_quality'])
        quality_scale.grid(row=5, column=1, padx=10, pady=5, sticky='ew')
        self.vars['screenshot_quality'].set(95)

        # Save debug images
        self.vars['save_debug_images'] = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Save Debug Images",
                       variable=self.vars['save_debug_images']).grid(
            row=6, column=0, columnspan=3, sticky='w', padx=10, pady=5)

    def _load_settings(self):
        """Load settings into UI."""
        config = settings.config

        # General
        self.vars['computer_name'].set(config.monitoring.computer_name)
        self.vars['monitoring_mode'].set(config.monitoring.monitoring_mode)
        self.vars['enable_auto_solve'].set(config.monitoring.enable_auto_solve)
        self.vars['debug_mode'].set(config.monitoring.debug_mode)
        self.vars['performance_monitoring'].set(config.monitoring.performance_monitoring)

        # Detection
        self.vars['check_interval'].set(str(config.detection.check_interval))
        self.vars['ocr_confidence'].set(str(config.detection.ocr_confidence_threshold))
        self.vars['yolo_confidence'].set(str(config.detection.yolo_confidence_threshold))
        self.vars['enable_gpu'].set(config.detection.enable_gpu)
        self.vars['max_cpu_usage'].set(str(config.detection.max_cpu_usage))

        # Telegram
        self.vars['bot_token'].set(config.telegram.bot_token)
        self.vars['chat_id'].set(config.telegram.chat_id)
        self.vars['notification_cooldown'].set(str(config.telegram.notification_cooldown))
        self.vars['max_retry_attempts'].set(str(config.telegram.max_retry_attempts))
        self.vars['retry_delay'].set(str(config.telegram.retry_delay))

        # Advanced
        self.vars['model_path'].set(config.paths.yolo_model_path)
        self.vars['log_file'].set(config.paths.log_file)
        self.vars['screenshot_age'].set(str(config.image.max_screenshot_age / 3600))
        self.vars['max_screenshots'].set(str(config.image.max_screenshots_stored))
        self.vars['screenshot_quality'].set(str(config.image.screenshot_quality))
        self.vars['save_debug_images'].set(config.image.save_debug_images)

    def _save_settings(self):
        """Save settings from UI."""
        try:
            # Update configuration
            config = settings.config

            # General
            config.monitoring.computer_name = self.vars['computer_name'].get()
            config.monitoring.monitoring_mode = self.vars['monitoring_mode'].get()
            config.monitoring.enable_auto_solve = self.vars['enable_auto_solve'].get()
            config.monitoring.debug_mode = self.vars['debug_mode'].get()
            config.monitoring.performance_monitoring = self.vars['performance_monitoring'].get()

            # Detection
            config.detection.check_interval = int(self.vars['check_interval'].get())
            config.detection.ocr_confidence_threshold = float(self.vars['ocr_confidence'].get())
            config.detection.yolo_confidence_threshold = float(self.vars['yolo_confidence'].get())
            config.detection.enable_gpu = self.vars['enable_gpu'].get()
            config.detection.max_cpu_usage = int(self.vars['max_cpu_usage'].get())

            # Telegram
            config.telegram.bot_token = self.vars['bot_token'].get()
            config.telegram.chat_id = self.vars['chat_id'].get()
            config.telegram.notification_cooldown = int(self.vars['notification_cooldown'].get())
            config.telegram.max_retry_attempts = int(self.vars['max_retry_attempts'].get())
            config.telegram.retry_delay = int(self.vars['retry_delay'].get())

            # Advanced
            config.paths.yolo_model_path = self.vars['model_path'].get()
            config.paths.log_file = self.vars['log_file'].get()
            config.image.max_screenshot_age = int(float(self.vars['screenshot_age'].get()) * 3600)
            config.image.max_screenshots_stored = int(self.vars['max_screenshots'].get())
            config.image.screenshot_quality = int(float(self.vars['screenshot_quality'].get()))
            config.image.save_debug_images = self.vars['save_debug_images'].get()

            # Validate settings
            if not settings.validate():
                messagebox.showerror("Error", "Invalid settings detected!")
                return

            # Save to file
            settings.save_config()

            messagebox.showinfo("Success", "Settings saved successfully!")

            # Notify callback
            if self.on_settings_changed:
                self.on_settings_changed()

        except Exception as e:
            self.logger.error(f"Failed to save settings: {e}")
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _test_notification(self):
        """Send a test notification."""
        def test():
            try:
                # Temporarily update telegram config
                old_token = settings.config.telegram.bot_token
                old_chat_id = settings.config.telegram.chat_id

                settings.config.telegram.bot_token = self.vars['bot_token'].get()
                settings.config.telegram.chat_id = self.vars['chat_id'].get()

                # Import here to avoid circular import
                from ..core.telegram_notifier import TelegramNotifier

                notifier = TelegramNotifier(
                    bot_token=settings.config.telegram.bot_token,
                    chat_id=settings.config.telegram.chat_id
                )

                success = notifier.send_test_notification(
                    include_screenshot=False,
                    computer_name=self.vars['computer_name'].get()
                )

                if success:
                    messagebox.showinfo("Success", "Test notification sent!")
                else:
                    messagebox.showerror("Error", "Failed to send test notification")

                # Restore settings
                settings.config.telegram.bot_token = old_token
                settings.config.telegram.chat_id = old_chat_id

            except Exception as e:
                self.logger.error(f"Test notification failed: {e}")
                messagebox.showerror("Error", f"Test notification failed: {e}")

        # Run in thread to avoid blocking UI
        threading.Thread(target=test, daemon=True).start()

    def _browse_model(self):
        """Browse for YOLO model file."""
        filename = filedialog.askopenfilename(
            title="Select YOLO Model",
            filetypes=[("PyTorch models", "*.pt"), ("ONNX models", "*.onnx"), ("All files", "*.*")]
        )
        if filename:
            self.vars['model_path'].set(filename)

    def _toggle_password(self, entry):
        """Toggle password visibility."""
        if entry.cget('show') == '*':
            entry.config(show='')
        else:
            entry.config(show='*')

    def _center_window(self):
        """Center window on screen."""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')

    def _on_closing(self):
        """Handle window closing."""
        if self.parent:
            # If we have a parent, just hide the window
            self.window.withdraw()
        else:
            # If this is the main window, destroy it
            self.window.destroy()

    def show(self):
        """Show the settings window."""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def hide(self):
        """Hide the settings window."""
        self.window.withdraw()

    def run(self):
        """Run the Tkinter main loop (if this is the main window)."""
        if not self.parent:
            self.window.mainloop()


def main():
    """Test the settings window."""
    window = SettingsWindow()
    window.run()


if __name__ == "__main__":
    main()