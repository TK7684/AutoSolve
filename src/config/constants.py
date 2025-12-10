"""
Constants and shared values for AutoSolve application.
"""

import os
from pathlib import Path
from enum import Enum

# Application constants
APP_NAME = "AutoSolve"
APP_VERSION = "1.0.0"
APP_AUTHOR = "AutoSolve Team"

# File extensions
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
MODEL_EXTENSIONS = ['.pt', '.pth', '.onnx']

# OCR trigger phrases for high-priority detection
OCR_TRIGGER_PHRASES = [
    "live will end in",
    "ending in",
    "ends in",
    "will end",
    "finishing in",
    "complete in",
    "time left"
]

# Captcha-related keywords
CAPTCHA_KEYWORDS = [
    "captcha",
    "verify",
    "prove you're human",
    "robot check",
    "security check",
    "i'm not a robot",
    "jigsaw",
    "puzzle"
]

# YOLO class names (adjust based on model)
YOLO_CLASS_NAMES = {
    0: 'jigsaw_piece',
    1: 'puzzle_slot',
    2: 'captcha'
}

# Detection states
class DetectionState(Enum):
    """Detection process states."""
    IDLE = "idle"
    SCREENCAPTURING = "screen_capturing"
    OCR_SCANNING = "ocr_scanning"
    JIGSAW_DETECTION = "jigsaw_detection"
    SOLVING = "solving"
    NOTIFYING = "notifying"
    ERROR = "error"


# Monitoring states
class MonitoringState(Enum):
    """Monitoring system states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"


# Notification types
class NotificationType(Enum):
    """Types of notifications."""
    CAPTCHA_DETECTED = "captcha_detected"
    STREAM_ENDED = "stream_ended"
    ERROR = "error"
    TEST = "test"
    SYSTEM_STATUS = "system_status"


# Mouse movement patterns
class MousePattern(Enum):
    """Mouse movement patterns for human-like behavior."""
    STRAIGHT = "straight"
    CURVED = "curved"
    ZIGZAG = "zigzag"
    HOVER = "hover"
    DRAG = "drag"


# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    'max_cpu_usage': 80.0,  # percentage
    'max_memory_usage': 512.0,  # MB
    'max_disk_usage': 1000.0,  # MB
    'min_fps': 10,  # frames per second for screen capture
    'max_response_time': 5.0  # seconds
}

# UI constants
UI_CONSTANTS = {
    'window_width': 800,
    'window_height': 600,
    'min_window_width': 400,
    'min_window_height': 300,
    'system_tray_update_interval': 1000,  # milliseconds
    'gui_update_interval': 500,  # milliseconds
}

# Colors (RGB)
COLORS = {
    'PRIMARY': (64, 128, 255),
    'SUCCESS': (76, 175, 80),
    'WARNING': (255, 193, 7),
    'ERROR': (244, 67, 54),
    'INFO': (33, 150, 243),
    'BACKGROUND': (245, 245, 245),
    'TEXT': (33, 33, 33),
    'TEXT_LIGHT': (117, 117, 117)
}

# Time constants
TIME_CONSTANTS = {
    'SECOND': 1,
    'MINUTE': 60,
    'HOUR': 3600,
    'DAY': 86400,
    'WEEK': 604800,
}

# Error codes
class ErrorCode(Enum):
    """Application error codes."""
    SUCCESS = 0
    INVALID_CONFIG = 1001
    MODEL_LOAD_FAILED = 1002
    SCREEN_CAPTURE_FAILED = 1003
    OCR_FAILED = 1004
    TELEGRAM_FAILED = 1005
    MOUSE_CONTROL_FAILED = 1006
    PERMISSION_DENIED = 1007
    RESOURCE_EXHAUSTED = 1008
    UNKNOWN_ERROR = 9999


# Log levels
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Default paths
DEFAULT_PATHS = {
    'root': Path(__file__).parent.parent.parent,
    'src': Path(__file__).parent.parent,
    'model': Path(__file__).parent.parent.parent / 'Model',
    'logs': Path(__file__).parent.parent.parent / 'logs',
    'captured_images': Path(__file__).parent.parent.parent / 'captured_images',
    'resources': Path(__file__).parent.parent.parent / 'resources',
    'config': Path(__file__).parent.parent.parent / 'config.yaml',
    'env': Path(__file__).parent.parent.parent / '.env'
}

# Validation patterns
VALIDATION_PATTERNS = {
    'telegram_bot_token': r'^\d+:[a-zA-Z0-9_-]+$',
    'telegram_chat_id': r'^-?\d+$',
    'computer_name': r'^[a-zA-Z0-9_-]+$',
    'version': r'^\d+\.\d+\.\d+$'
}

# Regional settings
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'zh': '中文',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'ja': '日本語',
    'ko': '한국어'
}

# Keyboard shortcuts
SHORTCUTS = {
    'exit': 'Ctrl+Q',
    'settings': 'Ctrl+S',
    'start_stop': 'Space',
    'screenshot': 'Ctrl+P',
    'test_notification': 'Ctrl+T',
    'show_logs': 'Ctrl+L'
}

# Debug constants
DEBUG = {
    'save_screenshots': False,
    'verbose_logging': False,
    'performance_profiling': False,
    'show_detection_boxes': False,
    'simulate_detection': False
}

# Registry keys for Windows startup
REGISTRY_KEYS = {
    'startup_path': r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'app_name': APP_NAME
}

# System requirements
SYSTEM_REQUIREMENTS = {
    'min_python_version': '3.8',
    'min_ram_mb': 4096,
    'min_disk_space_mb': 1000,
    'required_dlls': [
        'vcruntime140.dll',
        'msvcp140.dll'
    ]
}