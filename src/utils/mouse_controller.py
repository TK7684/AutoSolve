"""
Mouse controller utility for human-like mouse movements.
Provides smooth, natural mouse movements for automation.
"""

import time
import math
import random
from typing import Tuple, Optional, List
from enum import Enum

try:
    import pyautogui
    pyautogui.PAUSE = 0.01  # Small pause between actions
    pyautogui.FAILSAFE = True  # Move to corner to abort
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pynput
    from pynput import mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

from .logger import get_logger
from ..config.constants import MousePattern


class MouseController:
    """Controls mouse with human-like movements."""

    def __init__(self):
        self.logger = get_logger(f"{__name__}.MouseController")

        # Check availability
        self.pyautogui_available = PYAUTOGUI_AVAILABLE
        self.pynput_available = PYNPUT_AVAILABLE

        if not self.pyautogui_available:
            self.logger.error("pyautogui not available - mouse control limited")

        # Movement parameters
        self.base_speed = 0.5  # Base speed for movements
        self.deviation = 0.1  # Random deviation in path
        self.acceleration = 0.2  # Acceleration factor
        self.jitter = 2  # Pixel jitter for realism

        # Button state tracking
        self.buttons_pressed = set()

        # Current position
        self.current_x = 0
        self.current_y = 0
        self._update_position()

        self.logger.info(
            f"MouseController initialized: pyautogui={self.pyautogui_available}, "
            f"pynput={self.pynput_available}"
        )

    def _update_position(self):
        """Update current mouse position."""
        try:
            if self.pyautogui_available:
                self.current_x, self.current_y = pyautogui.position()
        except Exception as e:
            self.logger.error(f"Failed to get mouse position: {e}")

    def move_to(
        self,
        x: int,
        y: int,
        pattern: MousePattern = MousePattern.STRAIGHT,
        duration: float = 0.5,
        curve_strength: float = 0.5
    ):
        """
        Move mouse to position with specified pattern.

        Args:
            x: Target X coordinate
            y: Target Y coordinate
            pattern: Movement pattern
            duration: Duration of movement in seconds
            curve_strength: Strength of curve for curved patterns
        """
        if not self.pyautogui_available:
            self.logger.warning("Cannot move mouse: pyautogui not available")
            return False

        try:
            self.logger.debug(f"Moving mouse to ({x}, {y}) with pattern {pattern.value}")

            # Generate path points
            points = self._generate_path(
                (self.current_x, self.current_y),
                (x, y),
                pattern,
                curve_strength
            )

            # Execute movement
            self._execute_movement(points, duration)

            # Update position
            self.current_x = x
            self.current_y = y

            return True

        except Exception as e:
            self.logger.error(f"Mouse movement failed: {e}")
            return False

    def _generate_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        pattern: MousePattern,
        curve_strength: float
    ) -> List[Tuple[int, int]]:
        """Generate path points for movement."""
        points = []

        if pattern == MousePattern.STRAIGHT:
            points = self._straight_path(start, end)

        elif pattern == MousePattern.CURVED:
            points = self._curved_path(start, end, curve_strength)

        elif pattern == MousePattern.ZIGZAG:
            points = self._zigzag_path(start, end)

        elif pattern == MousePattern.HOVER:
            points = self._hover_path(start, end)

        else:
            # Default to straight
            points = self._straight_path(start, end)

        # Add small jitter to points for realism
        points = [
            (
                int(x + random.uniform(-self.jitter, self.jitter)),
                int(y + random.uniform(-self.jitter, self.jitter))
            )
            for x, y in points
        ]

        return points

    def _straight_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        num_points: int = 20
    ) -> List[Tuple[int, int]]:
        """Generate straight path between points."""
        points = []

        for i in range(num_points + 1):
            t = i / num_points
            # Ease in/out for more natural movement
            t = self._ease_in_out(t)

            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            points.append((int(x), int(y)))

        return points

    def _curved_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        curve_strength: float,
        num_points: int = 20
    ) -> List[Tuple[int, int]]:
        """Generate curved path using Bezier curve."""
        points = []

        # Calculate control point for curve
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2

        # Add perpendicular offset for curve
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = math.sqrt(dx**2 + dy**2)

        if length > 0:
            # Perpendicular direction
            perp_x = -dy / length
            perp_y = dx / length

            # Control point with some randomness
            offset = length * curve_strength
            control_x = mid_x + perp_x * offset * random.uniform(0.5, 1.5)
            control_y = mid_y + perp_y * offset * random.uniform(0.5, 1.5)
        else:
            control_x = mid_x
            control_y = mid_y

        # Quadratic Bezier curve
        for i in range(num_points + 1):
            t = i / num_points
            t = self._ease_in_out(t)

            # Bezier formula
            x = (1-t)**2 * start[0] + 2*(1-t)*t * control_x + t**2 * end[0]
            y = (1-t)**2 * start[1] + 2*(1-t)*t * control_y + t**2 * end[1]

            points.append((int(x), int(y)))

        return points

    def _zigzag_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        num_points: int = 20
    ) -> List[Tuple[int, int]]:
        """Generate zigzag path."""
        points = []

        dx = end[0] - start[0]
        dy = end[1] - start[1]

        # Zigzag amplitude
        amplitude = min(abs(dx), abs(dy)) * 0.1

        for i in range(num_points + 1):
            t = i / num_points
            t = self._ease_in_out(t)

            # Base position
            x = start[0] + dx * t
            y = start[1] + dy * t

            # Add zigzag offset
            if i > 0 and i < num_points:
                offset = amplitude * math.sin(t * math.pi * 4) * (1 - abs(2*t - 1))

                # Apply perpendicular offset
                if dx != 0 or dy != 0:
                    length = math.sqrt(dx**2 + dy**2)
                    perp_x = -dy / length * offset
                    perp_y = dx / length * offset
                    x += perp_x
                    y += perp_y

            points.append((int(x), int(y)))

        return points

    def _hover_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        num_points: int = 30
    ) -> List[Tuple[int, int]]:
        """Generate path with hovering near target."""
        # First move near target
        near_target = (
            end[0] + random.uniform(-50, 50),
            end[1] + random.uniform(-50, 50)
        )

        points = self._curved_path(start, near_target, 0.3, num_points // 2)

        # Add hovering around target
        hover_points = []
        for i in range(num_points // 2):
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(5, 20)

            x = end[0] + radius * math.cos(angle)
            y = end[1] + radius * math.sin(angle)

            hover_points.append((int(x), int(y)))

        # Finally move to exact target
        hover_points.append(end)

        return points + hover_points

    def _ease_in_out(self, t: float) -> float:
        """Apply ease-in-out timing function."""
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - pow(-2 * t + 2, 2) / 2

    def _execute_movement(self, points: List[Tuple[int, int]], duration: float):
        """Execute movement through points."""
        if not points:
            return

        num_points = len(points)

        for i, point in enumerate(points):
            # Calculate timing
            if i == num_points - 1:
                # Last point - ensure we reach target
                time_per_point = max(0.001, duration / num_points)
            else:
                time_per_point = duration / num_points

            # Move to point
            if self.pyautogui_available:
                pyautogui.moveTo(point[0], point[1])

            # Small delay
            time.sleep(time_per_point)

    def click(
        self,
        button: str = 'left',
        clicks: int = 1,
        interval: float = 0.1
    ) -> bool:
        """Perform mouse click."""
        if not self.pyautogui_available:
            self.logger.warning("Cannot click: pyautogui not available")
            return False

        try:
            self.logger.debug(f"Clicking {button} button {clicks} times")

            for i in range(clicks):
                pyautogui.click(button=button)

                # Small delay between clicks
                if i < clicks - 1:
                    time.sleep(interval)

            return True

        except Exception as e:
            self.logger.error(f"Mouse click failed: {e}")
            return False

    def press_button(self, button: str = 'left') -> bool:
        """Press and hold mouse button."""
        if not self.pyautogui_available:
            self.logger.warning("Cannot press button: pyautogui not available")
            return False

        try:
            self.logger.debug(f"Pressing {button} button")
            pyautogui.mouseDown(button=button)
            self.buttons_pressed.add(button)
            return True

        except Exception as e:
            self.logger.error(f"Button press failed: {e}")
            return False

    def release_button(self, button: str = 'left') -> bool:
        """Release mouse button."""
        if not self.pyautogui_available:
            self.logger.warning("Cannot release button: pyautogui not available")
            return False

        try:
            self.logger.debug(f"Releasing {button} button")
            pyautogui.mouseUp(button=button)
            self.buttons_pressed.discard(button)
            return True

        except Exception as e:
            self.logger.error(f"Button release failed: {e}")
            return False

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Scroll mouse wheel."""
        if not self.pyautogui_available:
            self.logger.warning("Cannot scroll: pyautogui not available")
            return False

        try:
            if x is not None and y is not None:
                self.logger.debug(f"Scrolling {clicks} clicks at ({x}, {y})")
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                self.logger.debug(f"Scrolling {clicks} clicks")
                pyautogui.scroll(clicks)

            return True

        except Exception as e:
            self.logger.error(f"Scroll failed: {e}")
            return False

    def drag_to(
        self,
        x: int,
        y: int,
        button: str = 'left',
        duration: float = 0.5
    ) -> bool:
        """Drag to position."""
        if not self.pyautogui_available:
            self.logger.warning("Cannot drag: pyautogui not available")
            return False

        try:
            self.logger.debug(f"Dragging to ({x}, {y}) with {button} button")

            # Use pyautogui's drag for simplicity
            pyautogui.dragTo(
                x, y,
                duration=duration,
                button=button
            )

            # Update position
            self.current_x = x
            self.current_y = y

            return True

        except Exception as e:
            self.logger.error(f"Drag failed: {e}")
            return False

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        self._update_position()
        return (self.current_x, self.current_y)

    def is_button_pressed(self, button: str) -> bool:
        """Check if button is currently pressed."""
        return button in self.buttons_pressed

    def release_all_buttons(self):
        """Release all pressed buttons."""
        for button in self.buttons_pressed.copy():
            self.release_button(button)