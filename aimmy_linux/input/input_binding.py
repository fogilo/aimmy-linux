"""
Input binding manager for Aimmy Linux.
Port of InputLogic/InputBindingManager.cs

Replaces Gma.System.MouseKeyHook (Win32 global hooks) with pynput
keyboard and mouse listeners for Linux.
"""

import threading
from typing import Callable, Dict, Optional, Set

from pynput import keyboard, mouse

from utils.log_manager import log, LogLevel


class InputBindingManager:
    """Manages global keyboard/mouse bindings for hotkeys.

    Uses pynput listeners instead of Win32 global hooks.
    """

    def __init__(self):
        self._bindings: Dict[str, str] = {}
        self._is_holding: Dict[str, bool] = {}
        self._setting_binding_id: Optional[str] = None

        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._mouse_listener: Optional[mouse.Listener] = None
        self._running = False

        # Callbacks
        self._on_binding_set: Optional[Callable[[str, str], None]] = None
        self._on_binding_pressed: Optional[Callable[[str], None]] = None
        self._on_binding_released: Optional[Callable[[str], None]] = None

    def set_on_binding_set(self, callback: Callable[[str, str], None]):
        self._on_binding_set = callback

    def set_on_binding_pressed(self, callback: Callable[[str], None]):
        self._on_binding_pressed = callback

    def set_on_binding_released(self, callback: Callable[[str], None]):
        self._on_binding_released = callback

    def setup_default(self, binding_id: str, key_code: str):
        """Register a default keybinding."""
        self._bindings[binding_id] = key_code
        self._is_holding[binding_id] = False
        if self._on_binding_set:
            self._on_binding_set(binding_id, key_code)
        self._ensure_listeners()

    def start_listening_for_binding(self, binding_id: str):
        """Enter 'listening' mode — next key/button press sets this binding."""
        self._setting_binding_id = binding_id
        self._ensure_listeners()

    def is_holding(self, binding_id: str) -> bool:
        """Check if a binding is currently held down."""
        return self._is_holding.get(binding_id, False)

    def _ensure_listeners(self):
        """Start global listeners if not already running."""
        if self._running:
            return

        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click,
        )

        self._keyboard_listener.daemon = True
        self._mouse_listener.daemon = True
        self._keyboard_listener.start()
        self._mouse_listener.start()
        self._running = True

    def _key_to_string(self, key) -> str:
        """Convert a pynput key to a string identifier."""
        if hasattr(key, 'char') and key.char is not None:
            return f"Key.{key.char}"
        return str(key)

    def _button_to_string(self, button) -> str:
        """Convert a pynput mouse button to a string identifier."""
        return str(button)

    def _on_key_press(self, key):
        """Handle global key press."""
        key_str = self._key_to_string(key)

        if self._setting_binding_id is not None:
            self._bindings[self._setting_binding_id] = key_str
            if self._on_binding_set:
                self._on_binding_set(self._setting_binding_id, key_str)
            self._setting_binding_id = None
        else:
            for binding_id, binding_key in self._bindings.items():
                if binding_key == key_str:
                    self._is_holding[binding_id] = True
                    if self._on_binding_pressed:
                        self._on_binding_pressed(binding_id)

    def _on_key_release(self, key):
        """Handle global key release."""
        key_str = self._key_to_string(key)

        for binding_id, binding_key in self._bindings.items():
            if binding_key == key_str:
                self._is_holding[binding_id] = False
                if self._on_binding_released:
                    self._on_binding_released(binding_id)

    def _on_mouse_click(self, x, y, button, pressed):
        """Handle global mouse button press/release."""
        btn_str = self._button_to_string(button)

        if pressed:
            if self._setting_binding_id is not None:
                self._bindings[self._setting_binding_id] = btn_str
                if self._on_binding_set:
                    self._on_binding_set(self._setting_binding_id, btn_str)
                self._setting_binding_id = None
            else:
                for binding_id, binding_key in self._bindings.items():
                    if binding_key == btn_str:
                        self._is_holding[binding_id] = True
                        if self._on_binding_pressed:
                            self._on_binding_pressed(binding_id)
        else:
            for binding_id, binding_key in self._bindings.items():
                if binding_key == btn_str:
                    self._is_holding[binding_id] = False
                    if self._on_binding_released:
                        self._on_binding_released(binding_id)

    def stop_listening(self):
        """Stop all listeners and clean up."""
        self._running = False
        if self._keyboard_listener:
            self._keyboard_listener.stop()
            self._keyboard_listener = None
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None


# Global singleton
input_binding_manager = InputBindingManager()
