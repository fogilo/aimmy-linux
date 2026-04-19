"""
Screen capture manager for Aimmy Linux.
Port of AILogic/CaptureManager.cs

Replaces DirectX DXGI Desktop Duplication and GDI+ with the `mss` library
for fast, cross-platform screen capture on Linux.
"""

import numpy as np
import mss
import mss.tools
from PIL import Image
from typing import Optional, Tuple

from utils.log_manager import log, LogLevel
from utils.config_manager import config


class CaptureManager:
    """Manages screen capture for the AI detection pipeline.

    Uses `mss` (Multiple Screen Shots) which works on X11 and Wayland
    and is significantly faster than PIL's ImageGrab.
    """

    def __init__(self):
        self._sct: Optional[mss.mss] = None
        self._last_frame: Optional[np.ndarray] = None
        self._initialized = False

    def initialize(self):
        """Initialize the screen capture backend."""
        try:
            self._sct = mss.mss()
            self._initialized = True
            log(LogLevel.INFO, "Screen capture initialized (mss backend)")
        except Exception as e:
            log(LogLevel.ERROR, f"Failed to initialize screen capture: {e}", notify_user=True)

    def screen_grab(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """Capture a region of the screen and return as a numpy array (RGB, HxWx3).

        Args:
            x: Left coordinate (absolute screen position)
            y: Top coordinate (absolute screen position)
            width: Width of the capture region
            height: Height of the capture region

        Returns:
            numpy array of shape (height, width, 3) in RGB format, or None on failure
        """
        if not self._initialized or self._sct is None:
            self.initialize()
            if not self._initialized:
                return None

        try:
            monitor = {
                "left": x,
                "top": y,
                "width": width,
                "height": height,
            }

            # mss returns BGRA format
            screenshot = self._sct.grab(monitor)

            # Convert to numpy array — mss gives us BGRA
            frame = np.frombuffer(screenshot.rgb, dtype=np.uint8)
            frame = frame.reshape((height, width, 3))  # .rgb gives us RGB directly

            # Apply third-person mask if enabled
            if config.toggle_state.get("Third Person Support", False):
                mask_w = width // 2
                mask_h = height // 2
                start_y = height - mask_h
                frame[start_y:, :mask_w, :] = 0

            self._last_frame = frame
            return frame

        except Exception as e:
            log(LogLevel.ERROR, f"Screen capture failed: {e}")
            return self._last_frame  # Return cached frame on failure

    def screen_grab_pil(self, x: int, y: int, width: int, height: int) -> Optional[Image.Image]:
        """Capture a region and return as a PIL Image (for saving/debug).

        Args:
            x, y, width, height: Capture region

        Returns:
            PIL Image in RGB format
        """
        frame = self.screen_grab(x, y, width, height)
        if frame is None:
            return None
        return Image.fromarray(frame)

    def dispose(self):
        """Clean up resources."""
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
            self._initialized = False
