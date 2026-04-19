"""
Mouse manager for Aimmy Linux.
Port of InputLogic/MouseManager.cs + MouseMovementLibraries/

Replaces Win32 mouse_event / SendInput with pynput for Linux.
All vendor-specific drivers (LG HUB, Razer, ddxoft) are replaced
by the universal pynput controller.
"""

import random
import time
from typing import Optional, Tuple

from pynput.mouse import Controller as MouseController, Button

from input.movement_paths import apply_movement_path
from utils.config_manager import config
from utils.display_manager import display_manager
from utils.log_manager import log, LogLevel


class MouseManager:
    """Manages mouse movement and clicking for aim assist.

    Uses pynput.mouse.Controller for cross-platform mouse input on Linux.
    """

    def __init__(self):
        self._controller = MouseController()
        self._last_click_time: float = 0.0
        self._is_spraying: bool = False
        self._previous_x: float = 0.0
        self._previous_y: float = 0.0
        self._mouse_random = random.Random()

    @property
    def cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position as (x, y)."""
        pos = self._controller.position
        return (int(pos[0]), int(pos[1]))

    def move_crosshair(self, detected_x: int, detected_y: int):
        """Move the crosshair towards the detected target.

        Port of MouseManager.MoveCrosshair — calculates relative movement
        from screen center to detected position, applies movement path
        and sensitivity, then moves the mouse.

        Args:
            detected_x: Detected target X in screen coordinates
            detected_y: Detected target Y in screen coordinates
        """
        screen_width = display_manager.screen_width
        screen_height = display_manager.screen_height

        half_w = screen_width // 2
        half_h = screen_height // 2

        target_x = detected_x - half_w
        target_y = detected_y - half_h

        aspect_ratio = screen_width / screen_height

        # Mouse jitter
        jitter = int(config.slider_settings.get("Mouse Jitter", 4))
        jitter_x = self._mouse_random.randint(-jitter, jitter) if jitter > 0 else 0
        jitter_y = self._mouse_random.randint(-jitter, jitter) if jitter > 0 else 0

        # Apply movement path
        start = (0, 0)
        end = (target_x, target_y)
        sensitivity = float(config.slider_settings.get("Mouse Sensitivity (+/-)", 0.80))
        path_name = config.dropdown_state.get("Movement Path", "Cubic Bezier")

        new_x, new_y = apply_movement_path(start, end, sensitivity, path_name)

        # EMA smoothing
        if config.toggle_state.get("EMA Smoothening", False):
            smoothing = float(config.slider_settings.get("EMA Smoothening", 0.5))
            new_x = int(new_x * smoothing + self._previous_x * (1 - smoothing))
            new_y = int(new_y * smoothing + self._previous_y * (1 - smoothing))

        # Clamp
        new_x = max(-150, min(150, new_x))
        new_y = max(-150, min(150, new_y))

        # Aspect ratio correction
        new_y = int(new_y / aspect_ratio)

        # Add jitter
        new_x += jitter_x
        new_y += jitter_y

        # Move mouse (relative movement)
        try:
            self._controller.move(new_x, new_y)
        except Exception as e:
            log(LogLevel.ERROR, f"Mouse move failed: {e}")

        self._previous_x = float(new_x)
        self._previous_y = float(new_y)

        if not config.toggle_state.get("Auto Trigger", False):
            self.reset_spray_state()

    async def do_trigger_click(self, detection_box=None):
        """Perform auto-trigger click.

        Port of MouseManager.DoTriggerClick
        """
        from input.input_binding import input_binding_manager

        if not (input_binding_manager.is_holding("Aim Keybind") or
                input_binding_manager.is_holding("Second Aim Keybind")):
            self.reset_spray_state()
            return

        if config.toggle_state.get("Spray Mode", False):
            if config.toggle_state.get("Cursor Check", False) and detection_box is not None:
                mx, my = self.cursor_position
                bx, by, bw, bh = detection_box
                if not (bx <= mx <= bx + bw and by <= my <= by + bh):
                    if self._is_spraying:
                        self._release_mouse()
                    return

            if not self._is_spraying:
                self._hold_mouse()
            return

        # Single click mode
        now = time.monotonic()
        trigger_delay = float(config.slider_settings.get("Auto Trigger Delay", 0.1))
        time_since_last = now - self._last_click_time

        if time_since_last < trigger_delay and self._last_click_time > 0:
            return

        self._controller.press(Button.left)
        time.sleep(0.020)  # 20ms click duration
        self._controller.release(Button.left)
        self._last_click_time = now

    def _hold_mouse(self):
        """Press and hold the left mouse button (spray mode)."""
        if self._is_spraying:
            return
        self._controller.press(Button.left)
        self._is_spraying = True

    def _release_mouse(self):
        """Release the left mouse button."""
        if not self._is_spraying:
            return
        self._controller.release(Button.left)
        self._is_spraying = False

    def reset_spray_state(self):
        """Reset spray mode — release button if spraying."""
        if self._is_spraying:
            self._release_mouse()


# Global singleton
mouse_manager = MouseManager()
