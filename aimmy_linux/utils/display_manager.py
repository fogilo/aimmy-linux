"""
Display manager for Aimmy Linux.
Port of Other/DisplayManager.cs

Uses screeninfo for monitor enumeration instead of Win32 EnumDisplayMonitors.
"""

import os
import re
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from utils.log_manager import log, LogLevel


def _get_monitors_safe(timeout: float = 3.0):
    """Get monitors with a timeout to prevent hanging in headless envs."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        try:
            from screeninfo import get_monitors
            future = pool.submit(get_monitors)
            return future.result(timeout=timeout)
        except FuturesTimeout:
            log(LogLevel.WARNING, "screeninfo.get_monitors() timed out, using xrandr fallback")
            return None
        except Exception as e:
            log(LogLevel.WARNING, f"screeninfo failed: {e}, using xrandr fallback")
            return None


def _get_monitors_xrandr():
    """Fallback: parse xrandr output for monitor info."""
    try:
        result = subprocess.run(
            ["xrandr", "--query"], capture_output=True, text=True, timeout=3
        )
        monitors = []
        # Match lines like: "HDMI-1 connected primary 1920x1080+0+0"
        pattern = re.compile(
            r"(\S+)\s+connected\s*(primary)?\s*(\d+)x(\d+)\+(\d+)\+(\d+)"
        )
        for match in pattern.finditer(result.stdout):
            name, primary, w, h, x, y = match.groups()
            monitors.append({
                "name": name,
                "is_primary": primary is not None,
                "width": int(w),
                "height": int(h),
                "x": int(x),
                "y": int(y),
            })
        return monitors if monitors else None
    except Exception:
        return None


@dataclass
class DisplayInfo:
    """Information about a single display/monitor."""
    index: int = 0
    is_primary: bool = False
    device_name: str = ""
    x: int = 0
    y: int = 0
    width: int = 1920
    height: int = 1080
    width_mm: int = 0
    height_mm: int = 0

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    def contains_point(self, px: int, py: int) -> bool:
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)


class DisplayManager:
    """Central manager for multi-display functionality.
    Port of the static DisplayManager class from C#.
    """

    def __init__(self):
        self._current_display: Optional[DisplayInfo] = None
        self._current_index: int = 0
        self._displays: List[DisplayInfo] = []
        self._lock = threading.Lock()
        self._initialized = False
        self._on_change_callbacks = []

    def initialize(self):
        """Initialize the display manager. Call early in startup."""
        with self._lock:
            if self._initialized:
                return
            self.refresh_displays()
            self._load_saved_display()
            self._initialized = True

    def on_display_changed(self, callback):
        """Register a callback for display change events."""
        self._on_change_callbacks.append(callback)

    def refresh_displays(self):
        """Refresh the list of available displays using safe methods."""
        with self._lock:
            old_count = len(self._displays)
            old_index = self._current_index

            self._displays = []
            
            # Try screeninfo first (with timeout)
            monitors = _get_monitors_safe()
            
            # If screeninfo fails/times out, try xrandr
            if not monitors:
                monitors = _get_monitors_xrandr()

            if monitors:
                for i, m in enumerate(monitors):
                    # Handle both screeninfo objects and dicts from xrandr
                    if hasattr(m, 'width'):
                        is_primary = getattr(m, 'is_primary', False) or (i == 0)
                        name = getattr(m, 'name', f"Monitor-{i}")
                        x, y = m.x, m.y
                        w, h = m.width, m.height
                        w_mm = getattr(m, 'width_mm', 0)
                        h_mm = getattr(m, 'height_mm', 0)
                    else:
                        is_primary = m.get('is_primary', False)
                        name = m.get('name', f"Monitor-{i}")
                        x, y = m.get('x', 0), m.get('y', 0)
                        w, h = m.get('width', 1920), m.get('height', 1080)
                        w_mm, h_mm = 0, 0

                    self._displays.append(DisplayInfo(
                        index=i,
                        is_primary=is_primary,
                        device_name=name,
                        x=x, y=y,
                        width=w, height=h,
                        width_mm=w_mm, height_mm=h_mm,
                    ))
            
            if not self._displays:
                log(LogLevel.WARNING, "No displays detected, using fallback virtual display")
                # Fallback: create a single virtual display
                self._displays = [DisplayInfo(
                    index=0, is_primary=True, device_name="Default",
                    x=0, y=0, width=1920, height=1080
                )]

            # Handle display removal
            if self._current_index >= len(self._displays):
                primary_idx = next(
                    (i for i, d in enumerate(self._displays) if d.is_primary), 0
                )
                self._current_index = primary_idx

            # Update current display reference
            if 0 <= self._current_index < len(self._displays):
                self._current_display = self._displays[self._current_index]
            else:
                self._current_display = None

            if len(self._displays) != old_count or self._current_index != old_index:
                self._notify_changed()

    def set_display(self, display_index: int) -> bool:
        """Set the active display by index."""
        with self._lock:
            if display_index < 0 or display_index >= len(self._displays):
                return False

            self._current_index = display_index
            self._current_display = self._displays[display_index]

            from utils.config_manager import config
            config.slider_settings["SelectedDisplay"] = display_index

            self._notify_changed()
            return True

    @property
    def current_display(self) -> Optional[DisplayInfo]:
        with self._lock:
            return self._current_display

    @property
    def current_display_index(self) -> int:
        with self._lock:
            return self._current_index

    @property
    def screen_width(self) -> int:
        d = self.current_display
        return d.width if d else 1920

    @property
    def screen_height(self) -> int:
        d = self.current_display
        return d.height if d else 1080

    @property
    def screen_left(self) -> int:
        d = self.current_display
        return d.x if d else 0

    @property
    def screen_top(self) -> int:
        d = self.current_display
        return d.y if d else 0

    def get_all_displays(self) -> List[DisplayInfo]:
        with self._lock:
            return list(self._displays)

    @property
    def display_count(self) -> int:
        with self._lock:
            return len(self._displays)

    def is_point_in_current_display(self, x: int, y: int) -> bool:
        d = self.current_display
        return d is not None and d.contains_point(x, y)

    def screen_to_display(self, x: int, y: int) -> Tuple[int, int]:
        """Convert absolute screen coordinates to display-relative."""
        return (x - self.screen_left, y - self.screen_top)

    def display_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convert display-relative coordinates to absolute screen."""
        return (x + self.screen_left, y + self.screen_top)

    def _load_saved_display(self):
        """Load saved display preference from config."""
        from utils.config_manager import config
        if not self._displays:
            self.refresh_displays()

        saved = config.slider_settings.get("SelectedDisplay", 0)
        saved_index = int(saved)
        if 0 <= saved_index < len(self._displays):
            self._current_index = saved_index
            self._current_display = self._displays[saved_index]
            return

        # Default to primary
        primary_idx = next(
            (i for i, d in enumerate(self._displays) if d.is_primary), 0
        )
        self._current_index = primary_idx
        if self._displays:
            self._current_display = self._displays[primary_idx]

    def _notify_changed(self):
        for cb in self._on_change_callbacks:
            try:
                cb(self._current_index, self._current_display)
            except Exception:
                pass


# Global singleton
display_manager = DisplayManager()
