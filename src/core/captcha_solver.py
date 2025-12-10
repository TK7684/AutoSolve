"""
Captcha solver module for AutoSolve.
Handles automatic captcha solving with human-like behavior.
"""

import time
import random
import math
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import pyautogui
    import pynput
    from pynput import mouse
except ImportError:
    pyautogui = None
    pynput = None

from ..config.settings import settings
from ..utils.logger import get_logger
from ..config.constants import MousePattern, DetectionBox
from ..utils.mouse_controller import MouseController


class SolveResult(Enum):
    """Result of captcha solving attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NOT_DETECTED = "not_detected"
    DISABLED = "disabled"


@dataclass
class SolveAttempt:
    """Record of a captcha solving attempt."""
    timestamp: float
    result: SolveResult
    confidence: float
    processing_time: float
    method_used: str
    error_message: Optional[str] = None


class CaptchaSolver:
    """
    Automatic captcha solver with human-like behavior.
    Currently implements placeholder logic pending real implementation.
    """

    def __init__(
        self,
        enabled: bool = False,
        mouse_controller: Optional[MouseController] = None,
        solve_timeout: float = 30.0,
        max_attempts: int = 3
    ):
        self.logger = get_logger(f"{__name__}.CaptchaSolver")

        # Configuration
        self.enabled = enabled or settings.config.monitoring.enable_auto_solve
        self.solve_timeout = solve_timeout
        self.max_attempts = max_attempts

        # Mouse controller for human-like movements
        self.mouse_controller = mouse_controller or MouseController()
        self.pyautogui_available = pyautogui is not None

        # State tracking
        self.current_attempt = 0
        self.is_solving = False
        self.last_solve_time = 0

        # Statistics
        self.solve_history: List[SolveAttempt] = []
        self.total_solves = 0
        self.successful_solves = 0

        # Human behavior parameters
        self.human_delays = {
            'initial_pause': (0.5, 2.0),  # Initial thinking pause
            'between_actions': (0.1, 0.3),  # Delay between mouse actions
            'drag_speed': (0.5, 1.5),  # Speed of dragging
            'settle_time': (0.2, 0.5),  # Time to settle on target
            'retry_delay': (1.0, 3.0)  # Delay between retry attempts
        }

        self.logger.info(
            f"CaptchaSolver initialized: enabled={self.enabled}, "
            f"pyautogui={self.pyautogui_available}"
        )

    def solve_captcha(
        self,
        detection_boxes: List[DetectionBox],
        image_size: Tuple[int, int],
        screenshot_path: Optional[str] = None
    ) -> SolveResult:
        """
        Attempt to solve detected captcha.

        Args:
            detection_boxes: List of detected puzzle pieces
            image_size: Size of the captured image (width, height)
            screenshot_path: Path to screenshot for analysis

        Returns:
            SolveResult indicating success or failure
        """
        if not self.enabled:
            self.logger.info("Auto-solve is disabled")
            return SolveResult.DISABLED

        if not detection_boxes:
            self.logger.warning("No detection boxes provided")
            return SolveResult.NOT_DETECTED

        if self.is_solving:
            self.logger.warning("Solver already in progress")
            return SolveResult.FAILED

        start_time = time.time()
        self.is_solving = True
        self.current_attempt = 0

        try:
            self.logger.info(f"Starting captcha solving with {len(detection_boxes)} pieces")

            # Multiple attempts
            while self.current_attempt < self.max_attempts:
                self.current_attempt += 1

                try:
                    # Attempt to solve
                    result = self._attempt_solve(detection_boxes, image_size)

                    # Record attempt
                    processing_time = time.time() - start_time
                    attempt = SolveAttempt(
                        timestamp=time.time(),
                        result=result,
                        confidence=0.8,  # Placeholder confidence
                        processing_time=processing_time,
                        method_used="placeholder"
                    )
                    self.solve_history.append(attempt)

                    if result == SolveResult.SUCCESS:
                        self.successful_solves += 1
                        self.logger.info(
                            f"Captcha solved successfully in {processing_time:.2f}s "
                            f"(attempt {self.current_attempt})"
                        )
                        return result

                    # Wait before retry
                    if self.current_attempt < self.max_attempts:
                        delay = random.uniform(*self.human_delays['retry_delay'])
                        time.sleep(delay)

                except Exception as e:
                    self.logger.error(f"Solve attempt {self.current_attempt} failed: {e}")
                    if self.current_attempt >= self.max_attempts:
                        break

            # All attempts failed
            processing_time = time.time() - start_time
            self.logger.error(
                f"Failed to solve captcha after {self.max_attempts} attempts "
                f"in {processing_time:.2f}s"
            )
            return SolveResult.FAILED

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Captcha solving failed with exception: {e}")

            # Record failure
            attempt = SolveAttempt(
                timestamp=time.time(),
                result=SolveResult.FAILED,
                confidence=0.0,
                processing_time=processing_time,
                method_used="placeholder",
                error_message=str(e)
            )
            self.solve_history.append(attempt)

            return SolveResult.FAILED

        finally:
            self.is_solving = False
            self.last_solve_time = time.time()
            self.total_solves += 1

    def _attempt_solve(
        self,
        detection_boxes: List[DetectionBox],
        image_size: Tuple[int, int]
    ) -> SolveResult:
        """
        Attempt a single solve operation.

        This is currently a placeholder implementation that simulates
        the solving process without actually solving the captcha.
        """
        self.logger.debug(f"Attempting solve #{self.current_attempt}")

        # Initial human-like pause
        initial_delay = random.uniform(*self.human_delays['initial_pause'])
        time.sleep(initial_delay)

        # Analyze detection boxes
        if not detection_boxes:
            return SolveResult.NOT_DETECTED

        # Find puzzle piece and slot (placeholder logic)
        puzzle_piece = self._find_puzzle_piece(detection_boxes)
        puzzle_slot = self._find_puzzle_slot(detection_boxes)

        if not puzzle_piece or not puzzle_slot:
            self.logger.warning("Could not identify puzzle piece and slot")
            return SolveResult.FAILED

        # Convert image coordinates to screen coordinates
        piece_screen_pos = self._image_to_screen_coords(
            (puzzle_piece.center[0], puzzle_piece.center[1]),
            image_size
        )
        slot_screen_pos = self._image_to_screen_coords(
            (puzzle_slot.center[0], puzzle_slot.center[1]),
            image_size
        )

        # Perform drag operation
        drag_success = self._perform_drag_operation(
            piece_screen_pos,
            slot_screen_pos
        )

        if drag_success:
            # Simulate verification time
            verification_delay = random.uniform(1.0, 2.0)
            time.sleep(verification_delay)

            # Placeholder: Assume success after drag
            # In real implementation, would verify if captcha is solved
            return SolveResult.SUCCESS
        else:
            return SolveResult.FAILED

    def _find_puzzle_piece(self, detection_boxes: List[DetectionBox]) -> Optional[DetectionBox]:
        """Find the puzzle piece from detection boxes."""
        # Placeholder: Look for highest confidence detection
        if not detection_boxes:
            return None

        # Filter for jigsaw pieces (based on class name or confidence)
        piece_boxes = [
            box for box in detection_boxes
            if 'jigsaw' in box.class_name.lower() or 'piece' in box.class_name.lower()
        ]

        if piece_boxes:
            # Return the piece with highest confidence
            return max(piece_boxes, key=lambda b: b.confidence)
        else:
            # Fallback to highest confidence box
            return max(detection_boxes, key=lambda b: b.confidence)

    def _find_puzzle_slot(self, detection_boxes: List[DetectionBox]) -> Optional[DetectionBox]:
        """Find the puzzle slot from detection boxes."""
        # Placeholder: Look for slot-like detection
        if not detection_boxes:
            return None

        # Filter for slots
        slot_boxes = [
            box for box in detection_boxes
            if 'slot' in box.class_name.lower() or 'target' in box.class_name.lower()
        ]

        if slot_boxes:
            return max(slot_boxes, key=lambda b: b.confidence)

        # Fallback: return different box than piece
        piece = self._find_puzzle_piece(detection_boxes)
        other_boxes = [b for b in detection_boxes if b != piece]

        return other_boxes[0] if other_boxes else None

    def _image_to_screen_coords(
        self,
        image_coords: Tuple[int, int],
        image_size: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Convert image coordinates to screen coordinates."""
        # This is a simplified conversion
        # In real implementation, would need to know where image was captured
        screen_width, screen_height = pyautogui.size() if self.pyautogui_available else (1920, 1080)
        img_width, img_height = image_size

        # Assume image was captured from primary monitor centered
        offset_x = (screen_width - img_width) // 2
        offset_y = (screen_height - img_height) // 2

        screen_x = image_coords[0] + offset_x
        screen_y = image_coords[1] + offset_y

        return (screen_x, screen_y)

    def _perform_drag_operation(
        self,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int]
    ) -> bool:
        """Perform human-like drag operation."""
        try:
            if not self.mouse_controller:
                self.logger.warning("Mouse controller not available")
                return False

            self.logger.debug(f"Dragging from {start_pos} to {end_pos}")

            # Move to start position with human-like path
            self.mouse_controller.move_to(
                start_pos[0],
                start_pos[1],
                pattern=MousePattern.CURVED,
                duration=random.uniform(*self.human_delays['drag_speed'])
            )

            # Small pause before grabbing
            time.sleep(random.uniform(*self.human_delays['settle_time']))

            # Press mouse button
            self.mouse_controller.press_button('left')

            # Drag to end position with human-like path
            time.sleep(random.uniform(*self.human_delays['between_actions']))
            self.mouse_controller.move_to(
                end_pos[0],
                end_pos[1],
                pattern=MousePattern.CURVED,
                duration=random.uniform(*self.human_delays['drag_speed'])
            )

            # Release mouse button
            time.sleep(random.uniform(*self.human_delays['settle_time']))
            self.mouse_controller.release_button('left')

            return True

        except Exception as e:
            self.logger.error(f"Drag operation failed: {e}")
            return False

    def simulate_solve(self, duration: float = 1.0) -> bool:
        """
        Simulate solving (placeholder method).
        This simulates the solving process without actual interaction.
        """
        self.logger.info(f"Simulating captcha solve for {duration}s")
        time.sleep(duration)

        # Random success/failure for simulation
        success = random.random() > 0.3  # 70% success rate

        attempt = SolveAttempt(
            timestamp=time.time(),
            result=SolveResult.SUCCESS if success else SolveResult.FAILED,
            confidence=random.uniform(0.7, 0.95),
            processing_time=duration,
            method_used="simulation"
        )
        self.solve_history.append(attempt)

        if success:
            self.successful_solves += 1
            self.logger.info("Simulated solve successful")
        else:
            self.logger.warning("Simulated solve failed")

        self.total_solves += 1
        return success

    def enable(self):
        """Enable auto-solve."""
        self.enabled = True
        self.logger.info("Auto-solve enabled")

    def disable(self):
        """Disable auto-solve."""
        self.enabled = False
        self.logger.info("Auto-solve disabled")

    def is_enabled(self) -> bool:
        """Check if auto-solve is enabled."""
        return self.enabled

    def is_busy(self) -> bool:
        """Check if solver is currently busy."""
        return self.is_solving

    def get_statistics(self) -> Dict[str, Any]:
        """Get solver statistics."""
        success_rate = (
            self.successful_solves / self.total_solves
            if self.total_solves > 0 else 0
        )

        avg_processing_time = (
            sum(a.processing_time for a in self.solve_history) / len(self.solve_history)
            if self.solve_history else 0
        )

        return {
            'enabled': self.enabled,
            'total_solves': self.total_solves,
            'successful_solves': self.successful_solves,
            'success_rate': success_rate,
            'avg_processing_time': avg_processing_time,
            'is_solving': self.is_solving,
            'last_solve_time': self.last_solve_time,
            'pyautogui_available': self.pyautogui_available
        }

    def get_recent_attempts(self, count: int = 10) -> List[SolveAttempt]:
        """Get recent solve attempts."""
        return self.solve_history[-count:]

    def reset_statistics(self):
        """Reset solver statistics."""
        self.solve_history.clear()
        self.total_solves = 0
        self.successful_solves = 0
        self.last_solve_time = 0
        self.logger.info("Captcha solver statistics reset")

    def update_human_behavior(self, **delays):
        """Update human behavior timing parameters."""
        for key, value in delays.items():
            if key in self.human_delays and isinstance(value, (tuple, list)) and len(value) == 2:
                self.human_delays[key] = tuple(value)
                self.logger.info(f"Updated human delay for {key}: {value}")

    def __del__(self):
        """Cleanup resources."""
        if self.is_solving:
            self.logger.warning("Solver was destroyed while solving")
        self.is_solving = False