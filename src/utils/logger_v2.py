"""
Simplified logging utilities for AutoSolve.
Provides clean console output with detailed remote logging.
"""

import logging
import logging.handlers
import sys
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from config.constants import DEFAULT_PATHS, LOG_LEVELS
from utils.remote_logger import remote_logger


class SimpleFormatter(logging.Formatter):
    """Simple formatter for console output."""

    def __init__(self):
        super().__init__('%(message)s')

    def format(self, record):
        # Simplify console output
        if record.levelno >= logging.ERROR:
            prefix = '❌ '
        elif record.levelno >= logging.WARNING:
            prefix = '⚠️ '
        else:
            prefix = '✅ '

        return f"{prefix}{record.getMessage()}"


class DetailedFormatter(logging.Formatter):
    """Detailed formatter for file logging."""

    def __init__(self):
        super().__init__(
            '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class AutoSolveLogger:
    """Main logger class with simplified console output and remote logging."""

    def __init__(
        self,
        name: str,
        log_file: Optional[str] = None,
        log_level: str = "INFO",
        enable_remote: bool = True
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.enable_remote = enable_remote

        # Clear existing handlers
        self.logger.handlers.clear()

        # Setup console handler (simplified)
        self._setup_console_handler()

        # Setup file handler (detailed)
        if log_file:
            self.log_file = Path(log_file)
        else:
            self.log_file = DEFAULT_PATHS['logs'] / f"autosolve_{datetime.now().strftime('%Y%m%d')}.log"

        self._setup_file_handler()

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _setup_console_handler(self):
        """Setup simplified console handler."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SimpleFormatter())
        handler.setLevel(logging.ERROR)  # Only show ERROR and above in console
        self.logger.addHandler(handler)

    def _setup_file_handler(self):
        """Setup detailed file handler with rotation."""
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        handler.setFormatter(DetailedFormatter())
        handler.setLevel(logging.DEBUG)  # Log everything to file
        self.logger.addHandler(handler)

    def debug(self, message: str, **kwargs):
        """Log debug message (file only)."""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, details: Optional[str] = None, **kwargs):
        """Log error message with optional error details."""
        error_details = details
        if error and not details:
            error_details = f"{type(error).__name__}: {str(error)}"
            if hasattr(error, '__traceback__') and error.__traceback__:
                error_details += "\n" + "".join(traceback.format_tb(error.__traceback__))

        self._log(logging.ERROR, message, error=error_details, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        error_details = traceback.format_exc()
        self._log(logging.ERROR, message, error=error_details, **kwargs)

    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with remote logging support."""
        # Get module name from caller
        module = kwargs.get('module', self.name.split('.')[-1])

        # Log to local handlers
        self.logger.log(level, message)

        # Send to remote logging if enabled
        if self.enable_remote:
            level_name = logging.getLevelName(level)
            error = kwargs.get('error')
            remote_logger.log(level_name, message, module=module, error=error)

    # Specialized logging methods
    def log_startup(self, component: str, details: Dict[str, Any] = None):
        """Log component startup."""
        message = f"{component} initialized"
        if details:
            details_str = ", ".join(f"{k}: {v}" for k, v in details.items())
            message += f" ({details_str})"
        self.info(message)

    def log_detection(self, captcha_type: str, confidence: float, action: str):
        """Log captcha detection."""
        self.info(
            f"Detected {captcha_type} (confidence: {confidence:.0%}) - {action}",
            captcha_type=captcha_type,
            confidence=confidence,
            action=action
        )

    def log_notification(self, notification_type: str, success: bool, details: str = None):
        """Log notification result."""
        if success:
            self.info(f"Notification sent: {notification_type}")
        else:
            self.error(f"Notification failed: {notification_type}", error=Exception(details))

    def log_performance(self, operation: str, duration: float, details: Dict[str, Any] = None):
        """Log performance metrics (debug only)."""
        message = f"Performance: {operation} took {duration:.2f}s"
        if details:
            details_str = ", ".join(f"{k}: {v}" for k, v in details.items())
            message += f" | {details_str}"
        self.debug(message)


# Global logger cache
_loggers = {}


def get_logger(name: str, log_file: Optional[str] = None, log_level: str = "INFO") -> AutoSolveLogger:
    """Get or create a logger instance."""
    if name not in _loggers:
        _loggers[name] = AutoSolveLogger(name, log_file, log_level)
    return _loggers[name]


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup global logging configuration."""
    # Configure root logger to suppress warnings
    logging.getLogger().setLevel(logging.WARNING)

    # Suppress noisy third-party loggers
    noisy_loggers = [
        'telegram.ext',
        'httpx',
        'urllib3',
        'PIL',
        'matplotlib',
        'ultralytics'
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Create main application logger
    return get_logger('AutoSolve', log_file, log_level)