"""
Screen capture module for AutoSolve.
Handles high-DPI aware screen capture with multi-monitor support.
"""

import os
import time
import mss
import numpy as np
from PIL import Image, ImageGrab
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path
import platform
import ctypes
from datetime import datetime
import threading

from ..config.settings import settings
from ..utils.logger import get_logger
from ..config.constants import PERFORMANCE_THRESHOLDS


class ScreenCapture:
    """High-performance screen capture with multi-monitor and high-DPI support."""

    def __init__(
        self,
        capture_interval: float = 0.1,
        max_images: int = 100,
        output_dir: str = "captured_images",
        image_format: str = "PNG",
        image_quality: int = 95,
        enable_dpi_aware: bool = True
    ):
        self.logger = get_logger(f"{__name__}.ScreenCapture")
        self.capture_interval = capture_interval
        self.max_images = max_images
        self.output_dir = Path(output_dir)
        self.image_format = image_format.upper()
        self.image_quality = image_quality
        self.enable_dpi_aware = enable_dpi_aware

        # Initialize capture components
        self.mss_instance = mss.mss()
        self.monitors = self._get_monitors()
        self.primary_monitor = self._get_primary_monitor()

        # Performance tracking
        self.capture_times = []
        self.last_capture_time = 0
        self.is_capturing = False
        self.capture_lock = threading.Lock()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # DPI awareness setup (Windows only)
        if enable_dpi_aware and platform.system() == "Windows":
            self._setup_dpi_awareness()

        self.logger.info(
            f"ScreenCapture initialized: {len(self.monitors)} monitors, "
            f"primary: {self.primary_monitor.width}x{self.primary_monitor.height}"
        )

    def _setup_dpi_awareness(self):
        """Setup DPI awareness for Windows."""
        try:
            # Windows 8.1 and later
            if hasattr(ctypes, 'windll'):
                shcore = ctypes.windll.shcore
                if hasattr(shcore, 'SetProcessDpiAwareness'):
                    # PROCESS_PER_MONITOR_DPI_AWARE = 2
                    shcore.SetProcessDpiAwareness(2)
                    self.logger.debug("Set DPI awareness to Per-Monitor")
                    return

            # Windows Vista and later
            user32 = ctypes.windll.user32
            if hasattr(user32, 'SetProcessDPIAware'):
                user32.SetProcessDPIAware()
                self.logger.debug("Set DPI awareness (legacy)")
        except Exception as e:
            self.logger.warning(f"Failed to set DPI awareness: {e}")

    def _get_monitors(self) -> List[Dict[str, Any]]:
        """Get information about all monitors."""
        monitors = []
        for i, monitor in enumerate(self.mss_instance.monitors[1:], 1):  # Skip first (combined)
            monitors.append({
                'id': i,
                'left': monitor['left'],
                'top': monitor['top'],
                'width': monitor['width'],
                'height': monitor['height'],
                'dpi_scale': self._get_dpi_scale(monitor)
            })
        return monitors

    def _get_primary_monitor(self) -> Dict[str, Any]:
        """Get primary monitor information."""
        with mss.mss() as sct:
            primary = sct.monitors[1]  # First monitor is usually primary
            return {
                'left': primary['left'],
                'top': primary['top'],
                'width': primary['width'],
                'height': primary['height'],
                'dpi_scale': self._get_dpi_scale(primary)
            }

    def _get_dpi_scale(self, monitor: Dict[str, Any]) -> float:
        """Get DPI scale factor for monitor."""
        # This is a simplified approach - real DPI detection is more complex
        try:
            if platform.system() == "Windows":
                user32 = ctypes.windll.user32
                gdi32 = ctypes.windll.gdi32

                # Get DPI
                dpi = gdi32.GetDeviceCaps(user32.GetDC(0), 88)  # LOGPIXELSX
                return dpi / 96.0  # 96 is standard DPI
        except Exception:
            pass
        return 1.0

    def capture_screen(
        self,
        monitor_id: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
        save_to_file: bool = True,
        filename: Optional[str] = None
    ) -> Tuple[Image.Image, Optional[str]]:
        """
        Capture screen or specific region.

        Args:
            monitor_id: Monitor ID to capture (None for all)
            region: (left, top, width, height) region to capture
            save_to_file: Whether to save image to file
            filename: Custom filename (auto-generated if None)

        Returns:
            Tuple of (PIL Image, file path or None)
        """
        start_time = time.time()

        with self.capture_lock:
            try:
                # Determine capture area
                if region:
                    capture_bbox = {
                        'left': region[0],
                        'top': region[1],
                        'width': region[2],
                        'height': region[3]
                    }
                elif monitor_id is not None:
                    monitor = self.monitors[monitor_id - 1] if monitor_id <= len(self.monitors) else self.primary_monitor
                    capture_bbox = {
                        'left': monitor['left'],
                        'top': monitor['top'],
                        'width': monitor['width'],
                        'height': monitor['height']
                    }
                else:
                    # Capture all monitors
                    capture_bbox = self.mss_instance.monitors[0]  # Combined monitors

                # Capture screen
                screenshot = self.mss_instance.grab(capture_bbox)
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

                # Apply DPI scaling if needed
                if self.enable_dpi_aware:
                    dpi_scale = self._get_dpi_scale(capture_bbox)
                    if dpi_scale != 1.0:
                        new_size = (
                            int(img.width * dpi_scale),
                            int(img.height * dpi_scale)
                        )
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Save to file if requested
                filepath = None
                if save_to_file:
                    filepath = self._save_image(img, filename)

                # Track performance
                capture_time = time.time() - start_time
                self.capture_times.append(capture_time)
                self.last_capture_time = time.time()

                # Keep only recent performance data
                if len(self.capture_times) > 100:
                    self.capture_times = self.capture_times[-100:]

                self.logger.debug(
                    f"Screen captured in {capture_time:.3f}s, "
                    f"size: {img.size}, format: {self.image_format}"
                )

                return img, filepath

            except Exception as e:
                self.logger.error(f"Screen capture failed: {e}")
                raise

    def _save_image(self, img: Image.Image, filename: Optional[str] = None) -> str:
        """Save image to file with timestamp or custom filename."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"screenshot_{timestamp}.{self.image_format.lower()}"

        filepath = self.output_dir / filename

        # Save with appropriate settings
        save_kwargs = {}
        if self.image_format == 'JPEG':
            save_kwargs['quality'] = self.image_quality
            save_kwargs['optimize'] = True
        elif self.image_format == 'PNG':
            save_kwargs['optimize'] = True

        img.save(filepath, format=self.image_format, **save_kwargs)
        return str(filepath)

    def cleanup_old_images(self, max_age_seconds: Optional[int] = None):
        """Remove old screenshots based on age or count."""
        max_age = max_age_seconds or settings.image.max_screenshot_age
        current_time = time.time()

        try:
            # Get all image files
            image_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp']:
                image_files.extend(self.output_dir.glob(ext))

            # Remove by age
            removed_age = 0
            for filepath in image_files:
                if current_time - filepath.stat().st_mtime > max_age:
                    filepath.unlink()
                    removed_age += 1

            # Remove by count if still too many
            remaining_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp']:
                remaining_files.extend(self.output_dir.glob(ext))

            # Sort by modification time (newest first)
            remaining_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Keep only the newest files
            removed_count = 0
            for filepath in remaining_files[self.max_images:]:
                filepath.unlink()
                removed_count += 1

            if removed_age > 0 or removed_count > 0:
                self.logger.info(
                    f"Cleaned up {removed_age} old and {removed_count} excess images"
                )

        except Exception as e:
            self.logger.error(f"Image cleanup failed: {e}")

    def get_monitor_info(self, monitor_id: Optional[int] = None) -> Dict[str, Any]:
        """Get monitor information."""
        if monitor_id is None:
            return self.primary_monitor
        elif monitor_id <= len(self.monitors):
            return self.monitors[monitor_id - 1]
        else:
            return self.primary_monitor

    def get_all_monitors_info(self) -> List[Dict[str, Any]]:
        """Get information about all monitors."""
        return self.monitors.copy()

    def get_capture_region_for_text(self, text_regions: List[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        """
        Get bounding box for text regions to optimize OCR scanning.

        Args:
            text_regions: List of (left, top, right, bottom) regions

        Returns:
            Combined bounding box
        """
        if not text_regions:
            # Return entire primary screen
            monitor = self.primary_monitor
            return (monitor['left'], monitor['top'], monitor['width'], monitor['height'])

        # Calculate bounding box
        min_left = min(region[0] for region in text_regions)
        min_top = min(region[1] for region in text_regions)
        max_right = max(region[2] for region in text_regions)
        max_bottom = max(region[3] for region in text_regions)

        # Add padding
        padding = 50
        min_left = max(0, min_left - padding)
        min_top = max(0, min_top - padding)
        max_right += padding
        max_bottom += padding

        return (min_left, min_top, max_right - min_left, max_bottom - min_top)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get capture performance statistics."""
        if not self.capture_times:
            return {
                'avg_capture_time': 0,
                'fps': 0,
                'total_captures': 0
            }

        avg_time = sum(self.capture_times) / len(self.capture_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0

        return {
            'avg_capture_time': avg_time,
            'fps': fps,
            'total_captures': len(self.capture_times),
            'last_capture_time': self.last_capture_time
        }

    def start_continuous_capture(
        self,
        callback: callable,
        monitor_id: Optional[int] = None,
        region: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Start continuous screen capture with callback.

        Args:
            callback: Function to call with each captured image
            monitor_id: Monitor to capture (None for all)
            region: Region to capture
        """
        self.is_capturing = True

        def capture_loop():
            while self.is_capturing:
                try:
                    img, filepath = self.capture_screen(
                        monitor_id=monitor_id,
                        region=region,
                        save_to_file=False
                    )
                    callback(img, filepath)
                    time.sleep(self.capture_interval)
                except Exception as e:
                    self.logger.error(f"Continuous capture error: {e}")
                    time.sleep(1)  # Brief pause on error

        capture_thread = threading.Thread(target=capture_loop, daemon=True)
        capture_thread.start()
        self.logger.info("Started continuous screen capture")

    def stop_continuous_capture(self):
        """Stop continuous screen capture."""
        self.is_capturing = False
        self.logger.info("Stopped continuous screen capture")

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'mss_instance'):
            self.mss_instance.close()