"""
Main entry point for AutoSolve application.
Coordinates all modules and runs the monitoring loop.
"""

import asyncio
import signal
import sys
import time
import threading
import os
import warnings
from pathlib import Path
from typing import Optional
import traceback
import torch

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*pin_memory.*")
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from utils.logger_v2 import setup_logging, get_logger
from utils.startup import get_computer_name, check_first_run, show_system_info, optimize_for_cpu
from utils.remote_logger import remote_logger
from core.screen_capture import ScreenCapture
from core.ocr_detector import OCRDetector
from core.jigsaw_detector import JigsawDetector
from core.telegram_notifier import TelegramNotifier
from core.captcha_solver import CaptchaSolver
from config.constants import DetectionState, MonitoringState, NotificationType


class AutoSolveApp:
    """Main application class for AutoSolve."""

    def __init__(self):
        # Initialize computer name
        self.computer_name = get_computer_name()

        # Setup logging with the new logger
        self.logger = setup_logging(
            log_level=settings.config.log_level,
            log_file=settings.config.paths.log_file
        )

        # Show system info on first run
        if check_first_run():
            show_system_info()

        # Check for GPU and optimize if needed
        self.has_gpu = torch.cuda.is_available()
        if not self.has_gpu:
            optimize_for_cpu()

        self.logger.info(
            f"AutoSolve initialized (computer: {self.computer_name}, gpu: {self.has_gpu}, monitors: {settings.config.monitoring})"
        )

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
        self.last_screenshot = None
        self.last_detection_time = 0

        # Statistics
        self.stats = {
            'screenshots_taken': 0,
            'detections_found': 0,
            'notifications_sent': 0,
            'errors': 0
        }

    def initialize_components(self):
        """Initialize all application components."""
        try:
            # Initialize components silently
            self.screen_capture = ScreenCapture()
            self.ocr_detector = OCRDetector(gpu_enabled=self.has_gpu)
            self.jigsaw_detector = JigsawDetector(enable_gpu=self.has_gpu)
            self.telegram_notifier = TelegramNotifier()
            self.captcha_solver = CaptchaSolver()

            # Send startup notification (non-blocking)
            if self.telegram_notifier and self.telegram_notifier.is_connected:
                import threading
                # Send notification in background thread to avoid blocking
                notification_thread = threading.Thread(
                    target=self.telegram_notifier.send_message,
                    args=(f"AutoSolve started\nComputer: {self.computer_name}",),
                    daemon=True
                )
                notification_thread.start()

        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            self.logger.error("Failed to initialize components", error=e)
            raise

    def run(self) -> int:
        """Run the main application loop."""
        try:
            # Initialize components
            self.initialize_components()

            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

            # Start monitoring
            self.is_running = True
            self.monitoring_state = MonitoringState.RUNNING

            # Main monitoring loop
            self._monitoring_loop()

            return 0

        except KeyboardInterrupt:
            print("✅ Received keyboard interrupt")
            return 0
        except Exception as e:
            print(f"❌ Fatal error in main loop")
            self.logger.error("Fatal error in main loop", error=e)
            return 1
        finally:
            self.cleanup()

    def _monitoring_loop(self):
        """Main monitoring loop."""
        check_interval = settings.config.detection.check_interval
        cycle_count = 0
        last_status_time = time.time()
        status_interval = 10  # Show status every 10 seconds

        print(f"\n🔍 Monitoring started - checking every {check_interval} seconds")
        print(f"💻 Computer: {self.computer_name}")
        print("Press Ctrl+C to stop\n")

        while self.is_running and not self.should_stop:
            try:
                # Update state
                self.monitoring_state = MonitoringState.RUNNING
                self.detection_state = DetectionState.SCREENCAPTURING

                # Show status every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= status_interval:
                    print(f"⏰ {time.strftime('%H:%M:%S')} - Monitoring... (Checks: {cycle_count}, Screenshots: {self.stats['screenshots_taken']}, Detections: {self.stats['detections_found']})")
                    last_status_time = current_time

                # Capture screen (only center region for faster processing)
                # Get monitor dimensions
                monitor = self.screen_capture.primary_monitor
                width, height = monitor['width'], monitor['height']

                # Capture center region (80% of screen, centered)
                capture_width = int(width * 0.8)
                capture_height = int(height * 0.3)  # Top 30% where captcha usually appears
                left = (width - capture_width) // 2
                top = 0
                right = left + capture_width
                bottom = top + capture_height

                img, screenshot_path = self.screen_capture.capture_screen(
                    region=(left, top, right, bottom),
                    save_to_file=True
                )
                self.last_screenshot = (img, screenshot_path)
                self.stats['screenshots_taken'] += 1
                cycle_count += 1
                self.detection_state = DetectionState.OCR_SCANNING

                # Debug: Show we're processing
                if cycle_count == 1:
                    print(f"📸 First screenshot captured: {img.size if img else 'None'} (region: {(left, top, right, bottom)})")

                # Check for trigger text with OCR
                ocr_detections = self.ocr_detector.detect_text(img)

                # Debug: Show OCR results
                if cycle_count <= 3:
                    print(f"   OCR found {len(ocr_detections)} text regions")

                # Check if any trigger phrases were found
                ocr_found = self.ocr_detector.has_trigger_phrase(ocr_detections)

                # Debug: Show trigger detection results for first few cycles
                if cycle_count <= 3:
                    print(f"   Trigger phrase found: {ocr_found}")
                    if len(ocr_detections) > 0:
                        for i, det in enumerate(ocr_detections[:3]):  # Show first 3 detections
                            print(f"     {i+1}. '{det.text[:50]}...' (trigger: {det.trigger_type})")

                if ocr_found:
                    # Find the trigger phrase that was detected
                    trigger_phrase = "unknown"
                    detected_text = ""
                    for detection in ocr_detections:
                        if detection.trigger_type:
                            trigger_phrase = detection.trigger_type
                            detected_text = detection.text
                            break

                    print(f"\n🚨 TRIGGER DETECTED: '{trigger_phrase}'")
                    print(f"📝 Text found: {detected_text}")
                    self.logger.info(f"Trigger phrase detected: '{trigger_phrase}'")
                    self.detection_state = DetectionState.JIGSAW_DETECTION

                    # Check for jigsaw captcha
                    jigsaw_result = self.jigsaw_detector.detect_jigsaw(img)

                    if jigsaw_result.is_detected:
                        self.stats['detections_found'] += 1
                        print(f"✅ {jigsaw_result.detection_method} captcha detected! (confidence: {jigsaw_result.confidence:.0%})")

                        # Send notification immediately
                        if self.telegram_notifier and self.telegram_notifier.is_connected:
                            import threading
                            notification_thread = threading.Thread(
                                target=self.telegram_notifier.send_photo,
                                args=(f"🚨 Captcha Detected!\nType: {jigsaw_result.detection_method}\nConfidence: {jigsaw_result.confidence:.0%}\nComputer: {self.computer_name}", screenshot_path),
                                daemon=True
                            )
                            notification_thread.start()
                            print("📤 Notification sent")

                        # Handle detection (attempt to solve if enabled)
                        self._handle_captcha_detection(
                            "Jigsaw",
                            jigsaw_result.confidence,
                            screenshot_path,
                            jigsaw_result.boxes
                        )
                    else:
                        self.logger.info("Trigger phrase found but no jigsaw detected")

                # Update state
                self.detection_state = DetectionState.IDLE

                # Sleep until next check
                time.sleep(check_interval)

            except Exception as e:
                self.stats['errors'] += 1
                import traceback
                error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                self.logger.error("Error in monitoring cycle", details=error_details)
                print(f"❌ Error in monitoring cycle: {type(e).__name__}: {str(e)}")
                # Don't print full stack trace to console, just the error
                time.sleep(check_interval)

    def _handle_captcha_detection(
        self,
        captcha_type: str,
        confidence: float,
        screenshot_path: Optional[str],
        detection_boxes: list
    ):
        """Handle captcha detection."""
        self.detection_state = DetectionState.NOTIFYING

        try:
            # Send notification
            if self.telegram_notifier and self.telegram_notifier.is_connected:
                # Check cooldown
                if not self.telegram_notifier._can_send_notification(
                    NotificationType.CAPTCHA_DETECTED
                ):
                    self.logger.info("Notification skipped due to cooldown")
                    return

                message = f"{captcha_type} captcha detected (confidence: {confidence:.0%})"

                # Send photo notification if screenshot available
                if screenshot_path:
                    success = self.telegram_notifier.send_photo(
                        message,
                        screenshot_path
                    )
                else:
                    success = self.telegram_notifier.send_message(message)

                if success:
                    self.stats['notifications_sent'] += 1
                    print(f"✅ Notification sent: {message}")

                    # Try to solve if enabled
                    if self.captcha_solver and self.captcha_solver.enabled:
                        self.detection_state = DetectionState.SOLVING
                        solve_result = self.captcha_solver.solve_captcha(
                            detection_boxes,
                            img.size,
                            screenshot_path
                        )
                        self.logger.info(f"Auto-solve result: {solve_result.result.value}")

        except Exception as e:
            self.logger.error("Error handling captcha detection", error=e)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.should_stop = True

    def cleanup(self):
        """Clean up resources before exit."""
        print("✅ Cleaning up...")

        try:
            # Stop monitoring
            if self.monitoring_state == MonitoringState.RUNNING:
                self.monitoring_state = MonitoringState.STOPPING

            # Stop continuous screen capture
            if self.screen_capture:
                self.screen_capture.stop_continuous_capture()

            # Print statistics
            print("✅ === Statistics ===")
            print(f"✅ Screenshots taken: {self.stats['screenshots_taken']}")
            print(f"✅ Detections found: {self.stats['detections_found']}")
            print(f"✅ Notifications sent: {self.stats['notifications_sent']}")
            print(f"✅ Errors encountered: {self.stats['errors']}")

            print("✅ Cleanup complete")

        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Flush remote logs
        remote_logger.flush()


def main():
    """Main entry point."""
    # Create and run application
    app = AutoSolveApp()
    exit_code = app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()