"""
Telegram notifier module for AutoSolve.
Sends notifications and screenshots via Telegram bot.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import threading
import requests
from telegram import Bot, InputFile
from telegram.error import TelegramError, NetworkError, TimedOut
from telegram.request import BaseRequest
import aiofiles

from ..config.settings import settings
from ..utils.logger import get_logger
from ..config.constants import NotificationType


class TelegramNotifier:
    """Handles Telegram notifications with retry logic and rate limiting."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[int] = None,
        cooldown_period: Optional[int] = None
    ):
        self.logger = get_logger(f"{__name__}.TelegramNotifier")

        # Configuration
        self.bot_token = bot_token or settings.config.telegram.bot_token
        self.chat_id = chat_id or settings.config.telegram.chat_id
        self.max_retries = max_retries or settings.config.telegram.max_retry_attempts
        self.retry_delay = retry_delay or settings.config.telegram.retry_delay
        self.cooldown_period = cooldown_period or settings.config.telegram.notification_cooldown

        # State tracking
        self.bot = None
        self.is_connected = False
        self.last_notification_time = 0
        self.last_notification_type = None
        self.notification_queue = asyncio.Queue()
        self.is_running = False
        self.worker_task = None

        # Statistics
        self.total_sent = 0
        self.total_failed = 0
        self.last_errors: List[Dict[str, Any]] = []

        # Initialize bot
        self._initialize_bot()

    def _initialize_bot(self):
        """Initialize the Telegram bot."""
        try:
            if not self.bot_token:
                raise ValueError("Telegram bot token is required")

            if not self.chat_id:
                raise ValueError("Telegram chat ID is required")

            # Create bot instance
            self.bot = Bot(token=self.bot_token, request=BaseRequest(connect_timeout=10.0))

            # Test connection
            self.is_connected = self._test_connection()

            if self.is_connected:
                self.logger.info(
                    f"Telegram notifier initialized successfully for chat {self.chat_id}"
                )
            else:
                self.logger.error("Failed to connect to Telegram bot")

        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram bot: {e}")
            self.is_connected = False

    def _test_connection(self) -> bool:
        """Test connection to Telegram bot."""
        try:
            # Try to get bot info
            bot_info = asyncio.run(self.bot.get_me())
            self.logger.info(f"Connected to bot: @{bot_info.username}")
            return True
        except Exception as e:
            self.logger.error(f"Bot connection test failed: {e}")
            return False

    def send_message(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.SYSTEM_STATUS,
        force_send: bool = False
    ) -> bool:
        """
        Send a text message to Telegram.

        Args:
            message: Message text to send
            notification_type: Type of notification
            force_send: Whether to bypass cooldown

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Cannot send message: Bot not connected")
            return False

        # Check cooldown
        if not force_send and not self._can_send_notification(notification_type):
            self.logger.debug(
                f"Notification skipped due to cooldown: {notification_type.value}"
            )
            return False

        # Add computer name and timestamp
        formatted_message = self._format_message(message, notification_type)

        try:
            # Run the async send operation
            result = asyncio.run(self._send_with_retry(
                lambda: self.bot.send_message(
                    chat_id=self.chat_id,
                    text=formatted_message,
                    parse_mode='Markdown'
                )
            ))

            if result:
                self._update_statistics(True, notification_type)
                self.logger.info(f"Message sent successfully: {notification_type.value}")

            return result

        except Exception as e:
            self._update_statistics(False, notification_type, str(e))
            self.logger.error(f"Failed to send message: {e}")
            return False

    def send_photo(
        self,
        image_path: str,
        caption: Optional[str] = None,
        notification_type: NotificationType = NotificationType.CAPTCHA_DETECTED,
        force_send: bool = False
    ) -> bool:
        """
        Send a photo to Telegram.

        Args:
            image_path: Path to image file
            caption: Optional caption for the photo
            notification_type: Type of notification
            force_send: Whether to bypass cooldown

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            self.logger.error("Cannot send photo: Bot not connected")
            return False

        # Check cooldown
        if not force_send and not self._can_send_notification(notification_type):
            self.logger.debug(
                f"Photo notification skipped due to cooldown: {notification_type.value}"
            )
            return False

        image_path = Path(image_path)
        if not image_path.exists():
            self.logger.error(f"Image file not found: {image_path}")
            return False

        # Format caption
        if caption:
            formatted_caption = self._format_message(caption, notification_type)
        else:
            formatted_caption = self._format_message("", notification_type)

        try:
            # Read and send photo
            result = asyncio.run(self._send_photo_with_retry(
                image_path,
                formatted_caption
            ))

            if result:
                self._update_statistics(True, notification_type)
                self.logger.info(f"Photo sent successfully: {image_path.name}")

            return result

        except Exception as e:
            self._update_statistics(False, notification_type, str(e))
            self.logger.error(f"Failed to send photo: {e}")
            return False

    def send_captcha_alert(
        self,
        screenshot_path: str,
        detection_confidence: float,
        detection_method: str,
        computer_name: Optional[str] = None
    ) -> bool:
        """
        Send a captcha detection alert with screenshot.

        Args:
            screenshot_path: Path to screenshot
            detection_confidence: Confidence score of detection
            detection_method: Method used for detection
            computer_name: Name of the computer

        Returns:
            True if successful, False otherwise
        """
        computer_name = computer_name or settings.config.monitoring.computer_name

        caption = (
            f"🚨 *CAPTCHA DETECTED*\n\n"
            f"📍 Computer: {computer_name}\n"
            f"🎯 Confidence: {detection_confidence:.1%}\n"
            f"🔍 Method: {detection_method}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Manual intervention required!"
        )

        return self.send_photo(
            screenshot_path,
            caption,
            NotificationType.CAPTCHA_DETECTED
        )

    def send_stream_ended_notification(
        self,
        computer_name: Optional[str] = None
    ) -> bool:
        """
        Send notification when stream ends.

        Args:
            computer_name: Name of the computer

        Returns:
            True if successful, False otherwise
        """
        computer_name = computer_name or settings.config.monitoring.computer_name

        message = (
            f"✅ *Stream Ended*\n\n"
            f"📍 Computer: {computer_name}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Ready to start new monitoring session."
        )

        return self.send_message(message, NotificationType.STREAM_ENDED)

    def send_test_notification(
        self,
        include_screenshot: bool = False,
        computer_name: Optional[str] = None
    ) -> bool:
        """
        Send a test notification.

        Args:
            include_screenshot: Whether to include a screenshot
            computer_name: Name of the computer

        Returns:
            True if successful, False otherwise
        """
        computer_name = computer_name or settings.config.monitoring.computer_name

        if include_screenshot:
            # Take a quick screenshot
            from ..core.screen_capture import ScreenCapture

            try:
                capturer = ScreenCapture()
                img, path = capturer.capture_screen(
                    save_to_file=True,
                    filename="test_screenshot.png"
                )

                caption = (
                    f"🧪 *Test Notification with Screenshot*\n\n"
                    f"📍 Computer: {computer_name}\n"
                    f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"If you see this, notifications are working correctly!"
                )

                return self.send_photo(path, caption, NotificationType.TEST, force_send=True)

            except Exception as e:
                self.logger.error(f"Failed to capture screenshot for test: {e}")
                # Fallback to text-only test

        # Text-only test
        message = (
            f"🧪 *Test Notification*\n\n"
            f"📍 Computer: {computer_name}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Notifications are working correctly!"
        )

        return self.send_message(message, NotificationType.TEST, force_send=True)

    def send_error_notification(
        self,
        error_message: str,
        error_details: Optional[str] = None,
        computer_name: Optional[str] = None
    ) -> bool:
        """
        Send an error notification.

        Args:
            error_message: Main error message
            error_details: Additional error details
            computer_name: Name of the computer

        Returns:
            True if successful, False otherwise
        """
        computer_name = computer_name or settings.config.monitoring.computer_name

        message = (
            f"❌ *Error Detected*\n\n"
            f"📍 Computer: {computer_name}\n"
            f"📝 Error: {error_message}\n"
        )

        if error_details:
            message += f"🔍 Details: {error_details}\n"

        message += f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return self.send_message(message, NotificationType.ERROR)

    def _can_send_notification(self, notification_type: NotificationType) -> bool:
        """Check if notification can be sent (cooldown)."""
        current_time = time.time()

        # Test notifications can always be sent
        if notification_type == NotificationType.TEST:
            return True

        # Check cooldown period
        if current_time - self.last_notification_time < self.cooldown_period:
            # Allow different types during cooldown if urgent
            urgent_types = {NotificationType.CAPTCHA_DETECTED, NotificationType.ERROR}
            if notification_type not in urgent_types:
                return False

        return True

    def _format_message(
        self,
        message: str,
        notification_type: NotificationType
    ) -> str:
        """Format message with emoji and prefix."""
        # Get computer name
        computer_name = settings.config.monitoring.computer_name

        # Add emoji based on type
        type_emojis = {
            NotificationType.CAPTCHA_DETECTED: "🚨",
            NotificationType.STREAM_ENDED: "✅",
            NotificationType.ERROR: "❌",
            NotificationType.TEST: "🧪",
            NotificationType.SYSTEM_STATUS: "ℹ️"
        }

        prefix = f"{type_emojis.get(notification_type, 'ℹ️')} *{notification_type.value.replace('_', ' ').title()}*"

        # Build formatted message
        if message:
            formatted = f"{prefix}\n\n{message}"
        else:
            formatted = prefix

        # Add computer name and timestamp if not already included
        if computer_name not in message:
            formatted += f"\n\n📍 Computer: {computer_name}"
            formatted += f"\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return formatted

    async def _send_with_retry(self, send_func) -> bool:
        """Send with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                await send_func()
                return True

            except NetworkError as e:
                last_exception = e
                self.logger.warning(f"Network error (attempt {attempt + 1}): {e}")

            except TimedOut as e:
                last_exception = e
                self.logger.warning(f"Timeout error (attempt {attempt + 1}): {e}")

            except TelegramError as e:
                last_exception = e
                self.logger.error(f"Telegram error (attempt {attempt + 1}): {e}")
                # Don't retry for Telegram API errors
                break

            except Exception as e:
                last_exception = e
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")

            # Wait before retry
            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

        return False

    async def _send_photo_with_retry(
        self,
        image_path: Path,
        caption: str
    ) -> bool:
        """Send photo with retry logic."""
        async def send_func():
            async with aiofiles.open(image_path, 'rb') as photo_file:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=InputFile(photo_file, filename=image_path.name),
                    caption=caption,
                    parse_mode='Markdown'
                )

        return await self._send_with_retry(send_func)

    def _update_statistics(
        self,
        success: bool,
        notification_type: NotificationType,
        error_message: Optional[str] = None
    ):
        """Update notification statistics."""
        if success:
            self.total_sent += 1
            self.last_notification_time = time.time()
            self.last_notification_type = notification_type
        else:
            self.total_failed += 1
            if error_message:
                self.last_errors.append({
                    'timestamp': datetime.now().isoformat(),
                    'error': error_message,
                    'type': notification_type.value
                })
                # Keep only last 10 errors
                if len(self.last_errors) > 10:
                    self.last_errors = self.last_errors[-10:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics."""
        return {
            'is_connected': self.is_connected,
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'success_rate': (
                self.total_sent / (self.total_sent + self.total_failed)
                if (self.total_sent + self.total_failed) > 0 else 0
            ),
            'last_notification_time': self.last_notification_time,
            'last_notification_type': (
                self.last_notification_type.value
                if self.last_notification_type else None
            ),
            'recent_errors': self.last_errors[-5:]  # Last 5 errors
        }

    def test_connection(self) -> bool:
        """Test Telegram connection."""
        try:
            return self._test_connection()
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def update_config(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[int] = None,
        cooldown_period: Optional[int] = None
    ):
        """Update configuration."""
        if bot_token and bot_token != self.bot_token:
            self.bot_token = bot_token
            self._initialize_bot()

        if chat_id:
            self.chat_id = chat_id

        if max_retries is not None:
            self.max_retries = max_retries

        if retry_delay is not None:
            self.retry_delay = retry_delay

        if cooldown_period is not None:
            self.cooldown_period = cooldown_period

        self.logger.info("Telegram notifier configuration updated")

    def reset_statistics(self):
        """Reset notification statistics."""
        self.total_sent = 0
        self.total_failed = 0
        self.last_notification_time = 0
        self.last_notification_type = None
        self.last_errors.clear()
        self.logger.info("Telegram notifier statistics reset")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Cleanup if needed
        pass