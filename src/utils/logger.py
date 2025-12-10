"""
Logging utilities for AutoSolve application.
Provides structured logging with colored console output and file logging.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import colorlog
from rich.logging import RichHandler
from rich.console import Console

from ..config.constants import DEFAULT_PATHS, LOG_LEVELS


class ColoredFormatter(colorlog.ColoredFormatter):
    """Custom colored formatter for log messages."""

    def __init__(self, fmt: str = None, datefmt: str = None):
        # Color codes for different log levels
        self.colors = {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }

        if fmt is None:
            fmt = (
                '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - '
                '%(message)s%(reset)s'
            )

        super().__init__(fmt, datefmt=datefmt, log_colors=self.colors)


class AutoSolveLogger:
    """Enhanced logger with console colors, file rotation, and structured output."""

    def __init__(
        self,
        name: str = 'AutoSolve',
        log_file: Optional[str] = None,
        log_level: str = 'INFO',
        enable_console: bool = True,
        enable_file: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_rich: bool = True
    ):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

        # Clear existing handlers to avoid duplicate logs
        self.logger.handlers.clear()

        # Setup paths
        self.log_file = log_file or str(DEFAULT_PATHS['logs'] / 'autosolve.log')
        self._ensure_log_directory()

        # Setup formatters
        self.console_formatter = ColoredFormatter()
        self.file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

        # Setup handlers
        if enable_console:
            self._setup_console_handler(enable_rich)

        if enable_file:
            self._setup_file_handler(max_file_size, backup_count)

    def _ensure_log_directory(self):
        """Ensure log directory exists."""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def _setup_console_handler(self, enable_rich: bool):
        """Setup console logging handler."""
        if enable_rich:
            console = Console()
            handler = RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True
            )
        else:
            handler = colorlog.StreamHandler(sys.stdout)
            handler.setFormatter(self.console_formatter)

        self.logger.addHandler(handler)

    def _setup_file_handler(self, max_file_size: int, backup_count: int):
        """Setup file logging handler with rotation."""
        handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setFormatter(self.file_formatter)
        self.logger.addHandler(handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._log_with_context(logging.ERROR, message, exc_info=True, **kwargs)

    def _log_with_context(
        self,
        level: int,
        message: str,
        exc_info: bool = False,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Log message with additional context."""
        # Add any extra context to the log record
        if extra is None:
            extra = {}

        # Add custom fields from kwargs
        for key, value in kwargs.items():
            if key not in extra:
                extra[key] = value

        # Log the message
        self.logger.log(level, message, exc_info=exc_info, extra=extra)

    def log_detection_result(
        self,
        captcha_type: str,
        confidence: float,
        processing_time: float,
        action_taken: str
    ):
        """Log captcha detection result."""
        self.info(
            f"Detection: {captcha_type} (confidence: {confidence:.2%}, "
            f"time: {processing_time:.2f}s, action: {action_taken})",
            captcha_type=captcha_type,
            confidence=confidence,
            processing_time=processing_time,
            action_taken=action_taken
        )

    def log_notification_sent(
        self,
        notification_type: str,
        success: bool,
        recipient: str,
        error: Optional[str] = None
    ):
        """Log notification result."""
        if success:
            self.info(
                f"Notification sent: {notification_type} to {recipient}",
                notification_type=notification_type,
                success=success,
                recipient=recipient
            )
        else:
            self.error(
                f"Notification failed: {notification_type} to {recipient} - {error}",
                notification_type=notification_type,
                success=success,
                recipient=recipient,
                error=error
            )

    def log_performance_metrics(
        self,
        cpu_usage: float,
        memory_usage: float,
        disk_usage: float,
        fps: float
    ):
        """Log performance metrics."""
        self.debug(
            f"Performance: CPU {cpu_usage:.1f}%, Memory {memory_usage:.1f}MB, "
            f"Disk {disk_usage:.1f}MB, FPS {fps:.1f}",
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=disk_usage,
            fps=fps
        )

    def log_error_with_context(
        self,
        error: Exception,
        context: Dict[str, Any],
        message: Optional[str] = None
    ):
        """Log error with additional context information."""
        error_msg = message or f"Error occurred: {str(error)}"

        # Create error context string
        context_str = ", ".join([f"{k}={v}" for k, v in context.items()])

        self.exception(
            f"{error_msg} | Context: {context_str}",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context
        )

    def set_level(self, level: str):
        """Change logging level."""
        self.logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))

    def add_file_handler(self, file_path: str, level: str = 'INFO'):
        """Add additional file handler."""
        handler = logging.FileHandler(file_path, encoding='utf-8')
        handler.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
        handler.setFormatter(self.file_formatter)
        self.logger.addHandler(handler)

    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        stats = {
            'log_file': self.log_file,
            'log_file_size': 0,
            'log_file_exists': False,
            'handlers_count': len(self.logger.handlers),
            'log_level': logging.getLevelName(self.logger.level)
        }

        if Path(self.log_file).exists():
            stats['log_file_exists'] = True
            stats['log_file_size'] = Path(self.log_file).stat().st_size

        return stats


# Global logger instance
_logger_instance: Optional[AutoSolveLogger] = None


def get_logger(name: Optional[str] = None) -> AutoSolveLogger:
    """Get or create logger instance."""
    global _logger_instance

    if _logger_instance is None:
        _logger_instance = AutoSolveLogger(name or 'AutoSolve')
    elif name:
        # Create child logger with different name
        return AutoSolveLogger(name)

    return _logger_instance


def setup_logging(
    log_level: str = 'INFO',
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True
) -> AutoSolveLogger:
    """Setup global logging configuration."""
    global _logger_instance
    _logger_instance = AutoSolveLogger(
        'AutoSolve',
        log_file=log_file,
        log_level=log_level,
        enable_console=enable_console,
        enable_file=enable_file
    )
    return _logger_instance


def log_function_call(func):
    """Decorator to log function calls."""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        func_name = f"{func.__module__}.{func.__name__}"

        logger.debug(f"Calling {func_name}", function=func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Completed {func_name}", function=func.__name__)
            return result
        except Exception as e:
            logger.error(f"Error in {func_name}: {str(e)}", function=func.__name__)
            raise

    return wrapper


# Convenience functions
def debug(message: str, **kwargs):
    """Log debug message."""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """Log info message."""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """Log warning message."""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """Log error message."""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """Log critical message."""
    get_logger().critical(message, **kwargs)


def exception(message: str, **kwargs):
    """Log exception with traceback."""
    get_logger().exception(message, **kwargs)