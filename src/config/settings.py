"""
Configuration management for AutoSolve.
Handles loading and validating environment variables and settings.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file
load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str
    chat_id: str
    notification_cooldown: int = 300  # 5 minutes
    max_retry_attempts: int = 3
    retry_delay: int = 5  # seconds


@dataclass
class DetectionConfig:
    """Detection settings configuration."""
    check_interval: int = 10  # seconds
    ocr_confidence_threshold: float = 0.5
    yolo_confidence_threshold: float = 0.5
    yolo_iou_threshold: float = 0.45
    enable_gpu: bool = True
    max_cpu_usage: int = 80  # percentage


@dataclass
class PathsConfig:
    """File paths configuration."""
    yolo_model_path: str = "Model/100824-YOLOv8.pt"
    log_file: str = "logs/autosolve.log"
    captured_images_dir: str = "captured_images"
    config_file: str = "config.yaml"


@dataclass
class ImageConfig:
    """Image processing configuration."""
    max_screenshot_age: int = 3600  # 1 hour in seconds
    max_screenshots_stored: int = 100
    screenshot_quality: int = 95
    save_debug_images: bool = False


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    computer_name: str = "MyComputer"
    enable_auto_solve: bool = False
    monitoring_mode: str = "247"  # 24/7 mode
    debug_mode: bool = False
    performance_monitoring: bool = True


@dataclass
class AppConfig:
    """Main application configuration."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    language: str = "en"
    time_zone: str = "UTC"
    log_level: str = "INFO"


class SettingsManager:
    """Manages application settings and configuration."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.yaml"
        self._config: Optional[AppConfig] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from environment variables and config file."""
        # First load from environment variables
        telegram = TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            notification_cooldown=int(os.getenv("NOTIFICATION_COOLDOWN", "300")),
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "5"))
        )

        detection = DetectionConfig(
            check_interval=int(os.getenv("CHECK_INTERVAL", "10")),
            ocr_confidence_threshold=float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.5")),
            yolo_confidence_threshold=float(os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.5")),
            yolo_iou_threshold=float(os.getenv("YOLO_IOU_THRESHOLD", "0.45")),
            enable_gpu=os.getenv("ENABLE_GPU", "true").lower() == "true",
            max_cpu_usage=int(os.getenv("MAX_CPU_USAGE", "80"))
        )

        paths = PathsConfig(
            yolo_model_path=os.getenv("YOLO_MODEL_PATH", "Model/100824-YOLOv8.pt"),
            log_file=os.getenv("LOG_FILE", "logs/autosolve.log"),
            captured_images_dir=os.getenv("CAPTURED_IMAGES_DIR", "captured_images"),
            config_file=self.config_file
        )

        image = ImageConfig(
            max_screenshot_age=int(os.getenv("MAX_SCREENSHOT_AGE", "3600")),
            max_screenshots_stored=int(os.getenv("MAX_SCREENSHOTS_STORED", "100")),
            screenshot_quality=int(os.getenv("SCREENSHOT_QUALITY", "95")),
            save_debug_images=os.getenv("SAVE_DEBUG_IMAGES", "false").lower() == "true"
        )

        monitoring = MonitoringConfig(
            computer_name=os.getenv("COMPUTER_NAME", "MyComputer"),
            enable_auto_solve=os.getenv("ENABLE_AUTO_SOLVE", "false").lower() == "true",
            monitoring_mode=os.getenv("MONITORING_MODE", "247"),
            debug_mode=os.getenv("DEBUG_MODE", "false").lower() == "true",
            performance_monitoring=os.getenv("PERFORMANCE_MONITORING", "true").lower() == "true"
        )

        self._config = AppConfig(
            telegram=telegram,
            detection=detection,
            paths=paths,
            image=image,
            monitoring=monitoring,
            language=os.getenv("LANGUAGE", "en"),
            time_zone=os.getenv("TIME_ZONE", "UTC"),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )

        # Then load from config file if it exists
        if Path(self.config_file).exists():
            self._load_from_file()

    def _load_from_file(self):
        """Load additional configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                file_config = yaml.safe_load(f) or {}

            # Update configuration with file values
            if 'telegram' in file_config:
                for key, value in file_config['telegram'].items():
                    if hasattr(self._config.telegram, key):
                        setattr(self._config.telegram, key, value)

            if 'detection' in file_config:
                for key, value in file_config['detection'].items():
                    if hasattr(self._config.detection, key):
                        setattr(self._config.detection, key, value)

            if 'monitoring' in file_config:
                for key, value in file_config['monitoring'].items():
                    if hasattr(self._config.monitoring, key):
                        setattr(self._config.monitoring, key, value)

        except Exception as e:
            print(f"Warning: Could not load config file {self.config_file}: {e}")

    def save_config(self):
        """Save current configuration to YAML file."""
        try:
            config_dict = {
                'telegram': {
                    'bot_token': self._config.telegram.bot_token,
                    'chat_id': self._config.telegram.chat_id,
                    'notification_cooldown': self._config.telegram.notification_cooldown,
                    'max_retry_attempts': self._config.telegram.max_retry_attempts,
                    'retry_delay': self._config.telegram.retry_delay
                },
                'detection': {
                    'check_interval': self._config.detection.check_interval,
                    'ocr_confidence_threshold': self._config.detection.ocr_confidence_threshold,
                    'yolo_confidence_threshold': self._config.detection.yolo_confidence_threshold,
                    'yolo_iou_threshold': self._config.detection.yolo_iou_threshold,
                    'enable_gpu': self._config.detection.enable_gpu,
                    'max_cpu_usage': self._config.detection.max_cpu_usage
                },
                'monitoring': {
                    'computer_name': self._config.monitoring.computer_name,
                    'enable_auto_solve': self._config.monitoring.enable_auto_solve,
                    'monitoring_mode': self._config.monitoring.monitoring_mode,
                    'debug_mode': self._config.monitoring.debug_mode,
                    'performance_monitoring': self._config.monitoring.performance_monitoring
                },
                'image': {
                    'max_screenshot_age': self._config.image.max_screenshot_age,
                    'max_screenshots_stored': self._config.image.max_screenshots_stored,
                    'screenshot_quality': self._config.image.screenshot_quality,
                    'save_debug_images': self._config.image.save_debug_images
                }
            }

            with open(self.config_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)

        except Exception as e:
            print(f"Error saving config file: {e}")

    @property
    def config(self) -> AppConfig:
        """Get the application configuration."""
        return self._config

    def validate(self) -> bool:
        """Validate configuration settings."""
        errors = []

        # Validate Telegram configuration
        if not self._config.telegram.bot_token:
            errors.append("Telegram bot token is required")
        if not self._config.telegram.chat_id:
            errors.append("Telegram chat ID is required")

        # Validate paths
        if not Path(self._config.paths.yolo_model_path).exists():
            errors.append(f"YOLO model not found at {self._config.paths.yolo_model_path}")

        # Validate detection settings
        if self._config.detection.check_interval < 1:
            errors.append("Check interval must be at least 1 second")
        if not 0 <= self._config.detection.ocr_confidence_threshold <= 1:
            errors.append("OCR confidence threshold must be between 0 and 1")
        if not 0 <= self._config.detection.yolo_confidence_threshold <= 1:
            errors.append("YOLO confidence threshold must be between 0 and 1")

        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True


# Global settings instance
settings = SettingsManager()