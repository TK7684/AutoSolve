"""
Main entry point for AutoSolve application.
Coordinates all modules and runs the monitoring loop.
"""

import asyncio
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Optional
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from utils.logger import setup_logging, get_logger
from core.screen_capture import ScreenCapture
from core.ocr_detector import OCRDetector
from core.jigsaw_detector import JigsawDetector
from core.telegram_notifier import TelegramNotifier
from core.captcha_solver import CaptchaSolver
from config.constants import DetectionState, MonitoringState, NotificationType


class AutoSolveApp:
    """Main application class for AutoSolve."""

    def __init__(self):
        # Setup logging
        setup_logging(
            log_level=settings.config.log_level,
            log_file=settings.config.paths.log_file,
            enable_console=True,
            enable_file=True
        )
        self.logger = get_logger(__name__)

        self.logger.info("Starting AutoSolve application...")
        self.logger.info(f"Computer name: {settings.config.monitoring.computer_name}")

        # Application state
        self.monitoring_state = MonitoringState.STOPPED
        self.detection_state = DetectionState.IDLE
        self.is_running = False
        self.should_stop = False

        # Initialize components
        self.screen_capture = None
        self.ocr_detector = None
        self.jigsaw_detector = None
        self.telegram_notifier = None
        self.captcha_solver = None

        # Monitoring thread
        self.monitoring_thread = None

        # Statistics
        self.stats = {
            'start_time': time.time(),
            'total_detections': 0,
            'captcha_detected': 0,
            'auto_solves_attempted': 0,
            'notifications_sent': 0,
            'errors': 0
        }

        # Initialize signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def initialize_components(self) -> bool:
        """Initialize all application components."""
        try:
            self.logger.info("Initializing components...")

            # Validate configuration
            if not settings.validate():
                self.logger.error("Configuration validation failed")
                return False

            # Initialize screen capture
            self.screen_capture = ScreenCapture(
                capture_interval=settings.config.detection.check_interval,
                output_dir=settings.config.paths.captured_images_dir,
                image_quality=settings.config.image.screenshot_quality
            )

            # Initialize OCR detector
            self.ocr_detector = OCRDetector(
                confidence_threshold=settings.config.detection.ocr_confidence_threshold,
                gpu_enabled=settings.config.detection.enable_gpu
            )

            # Initialize jigsaw detector
            self.jigsaw_detector = JigsawDetector(
                confidence_threshold=settings.config.detection.yolo_confidence_threshold,
                iou_threshold=settings.config.detection.yolo_iou_threshold,
                enable_gpu=settings.config.detection.enable_gpu
            )

            # Initialize Telegram notifier
            self.telegram_notifier = TelegramNotifier()

            # Initialize captcha solver
            self.captcha_solver = CaptchaSolver(
                enabled=settings.config.monitoring.enable_auto_solve
            )

            self.logger.info("All components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def start_monitoring(self) -> bool:
        """Start the monitoring loop."""
        if self.monitoring_state != MonitoringState.STOPPED:
            self.logger.warning("Monitoring already running")
            return False

        self.logger.info("Starting monitoring...")
        self.monitoring_state = MonitoringState.STARTING
        self.should_stop = False

        # Start monitoring thread
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()

        return True

    def stop_monitoring(self):
        """Stop the monitoring loop."""
        if self.monitoring_state == MonitoringState.STOPPED:
            return

        self.logger.info("Stopping monitoring...")
        self.monitoring_state = MonitoringState.STOPPING
        self.should_stop = True

        # Wait for thread to finish
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)

        self.monitoring_state = MonitoringState.STOPPED
        self.logger.info("Monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        self.monitoring_state = MonitoringState.RUNNING
        self.logger.info("Monitoring loop started")

        try:
            while not self.should_stop:
                loop_start = time.time()

                try:
                    # Perform monitoring cycle
                    self._perform_monitoring_cycle()

                except Exception as e:
                    self.logger.error(f"Error in monitoring cycle: {e}")
                    self.stats['errors'] += 1

                # Calculate sleep time
                cycle_time = time.time() - loop_start
                sleep_time = max(0, settings.config.detection.check_interval - cycle_time)

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            self.logger.error(f"Monitoring loop crashed: {e}")
            self.monitoring_state = MonitoringState.ERROR

        finally:
            self.monitoring_state = MonitoringState.STOPPED
            self.logger.info("Monitoring loop ended")

    def _perform_monitoring_cycle(self):
        """Perform a single monitoring cycle."""
        self.detection_state = DetectionState.SCREENCAPTURING

        # Capture screen
        image, screenshot_path = self.screen_capture.capture_screen(
            save_to_file=True
        )

        if not image:
            self.logger.error("Failed to capture screen")
            return

        # High-priority OCR detection for trigger phrases
        self.detection_state = DetectionState.OCR_SCANNING
        ocr_detections = self.ocr_detector.detect_text(image)

        # Check for trigger phrases
        trigger_detected = self.ocr_detector.has_trigger_phrase(ocr_detections)

        if trigger_detected:
            self.logger.info("Trigger phrase detected, performing jigsaw detection")
            self.stats['total_detections'] += 1
            self.detection_state = DetectionState.JIGSAW_DETECTION

            # Perform jigsaw detection with high sensitivity
            jigsaw_result = self.jigsaw_detector.detect_jigsaw(
                image,
                use_fallback_if_needed=True
            )

            if jigsaw_result.is_detected:
                self._handle_captcha_detected(image, screenshot_path, jigsaw_result)
            else:
                self.logger.info("Trigger detected but no jigsaw found")

        else:
            # Secondary checks (lower priority)
            self._perform_secondary_checks(image)

        # Cleanup old screenshots
        self.screen_capture.cleanup_old_images()

        # Reset detection state
        self.detection_state = DetectionState.IDLE

    def _perform_secondary_checks(self, image):
        """Perform secondary checks when no trigger detected."""
        # Check for general captcha patterns
        jigsaw_result = self.jigsaw_detector.detect_jigsaw(
            image,
            use_fallback_if_needed=True
        )

        if jigsaw_result.is_detected:
            self.logger.info("Jigsaw detected without trigger phrase")
            self._handle_captcha_detected(image, None, jigsaw_result)

        # Check for "Start" button (stream ended)
        # This would need additional OCR implementation
        # For now, just log
        self.logger.debug("Performing secondary checks")

    def _handle_captcha_detected(self, image, screenshot_path, jigsaw_result):
        """Handle captcha detection."""
        self.stats['captcha_detected'] += 1
        self.logger.warning(
            f"Captcha detected! Confidence: {jigsaw_result.confidence:.2f}, "
            f"Method: {jigsaw_result.detection_method}"
        )

        # Save screenshot if not already saved
        if not screenshot_path:
            image, screenshot_path = self.screen_capture.capture_screen(
                save_to_file=True,
                filename=f"captcha_detected_{int(time.time())}.png"
            )

        # Attempt auto-solve if enabled
        if self.captcha_solver.is_enabled():
            self.detection_state = DetectionState.SOLVING
            self.stats['auto_solves_attempted'] += 1

            solve_result = self.captcha_solver.solve_captcha(
                jigsaw_result.boxes,
                jigsaw_result.image_size,
                screenshot_path
            )

            if solve_result == 'success':
                self.logger.info("Captcha solved successfully!")
                return
            else:
                self.logger.warning(f"Auto-solve failed: {solve_result}")

        # Send notification if solve failed or disabled
        self.detection_state = DetectionState.NOTIFYING
        notification_sent = self.telegram_notifier.send_captcha_alert(
            screenshot_path,
            jigsaw_result.confidence,
            jigsaw_result.detection_method
        )

        if notification_sent:
            self.stats['notifications_sent'] += 1

    def send_test_notification(self, include_screenshot: bool = False) -> bool:
        """Send a test notification."""
        return self.telegram_notifier.send_test_notification(
            include_screenshot=include_screenshot,
            computer_name=settings.config.monitoring.computer_name
        )

    def get_status(self) -> dict:
        """Get current application status."""
        uptime = time.time() - self.stats['start_time']

        return {
            'monitoring_state': self.monitoring_state.value,
            'detection_state': self.detection_state.value,
            'uptime_seconds': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'statistics': self.stats.copy(),
            'component_status': {
                'screen_capture': self.screen_capture is not None,
                'ocr_detector': self.ocr_detector is not None,
                'jigsaw_detector': self.jigsaw_detector is not None,
                'telegram_notifier': (
                    self.telegram_notifier.is_connected
                    if self.telegram_notifier else False
                ),
                'captcha_solver': (
                    self.captcha_solver.is_enabled()
                    if self.captcha_solver else False
                )
            },
            'performance': {
                'screen_capture': (
                    self.screen_capture.get_performance_stats()
                    if self.screen_capture else {}
                ),
                'ocr_detector': (
                    self.ocr_detector.get_performance_stats()
                    if self.ocr_detector else {}
                ),
                'jigsaw_detector': (
                    self.jigsaw_detector.get_performance_stats()
                    if self.jigsaw_detector else {}
                ),
                'telegram': (
                    self.telegram_notifier.get_statistics()
                    if self.telegram_notifier else {}
                )
            }
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime as human-readable string."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def run(self):
        """Run the application."""
        try:
            self.logger.info("AutoSolve is running...")

            # Initialize components
            if not self.initialize_components():
                self.logger.error("Failed to initialize components")
                return 1

            # Start monitoring
            if not self.start_monitoring():
                self.logger.error("Failed to start monitoring")
                return 1

            # Send startup notification
            self.telegram_notifier.send_message(
                f"✅ AutoSolve started on {settings.config.monitoring.computer_name}",
                NotificationType.SYSTEM_STATUS
            )

            # Keep application running
            self.is_running = True
            while self.is_running and not self.should_stop:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    break

            return 0

        except Exception as e:
            self.logger.error(f"Application error: {e}")
            self.logger.error(traceback.format_exc())
            return 1

        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up...")

        # Stop monitoring
        self.stop_monitoring()

        # Send shutdown notification
        if self.telegram_notifier:
            try:
                self.telegram_notifier.send_message(
                    f"🔴 AutoSolve stopped on {settings.config.monitoring.computer_name}",
                    NotificationType.SYSTEM_STATUS
                )
            except Exception as e:
                self.logger.error(f"Failed to send shutdown notification: {e}")

        # Cleanup components
        if self.screen_capture:
            self.screen_capture.stop_continuous_capture()

        self.logger.info("Cleanup complete")

    def stop(self):
        """Stop the application."""
        self.logger.info("Stopping application...")
        self.is_running = False
        self.should_stop = True


def main():
    """Main entry point."""
    # Create and run application
    app = AutoSolve()
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()