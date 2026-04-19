"""
Configuration manager for Aimmy Linux.
Port of Class/Dictionary.cs + Class/SaveDictionary.cs

Central configuration store that holds all toggle states, slider values,
dropdown selections, keybindings, and color settings.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Central configuration singleton. Mirrors the C# Dictionary class."""

    def __init__(self):
        self.last_loaded_model: str = "N/A"
        self.last_loaded_config: str = "N/A"

        # Keybind settings — Linux key names
        self.binding_settings: Dict[str, str] = {
            "Aim Keybind": "Button.right",       # Right mouse button
            "Second Aim Keybind": "Key.alt_l",    # Left Alt
            "Dynamic FOV Keybind": "Button.left", # Left mouse button
            "Emergency Stop Keybind": "Key.delete",
            "Model Switch Keybind": "Key.backslash",
        }

        # Slider (numeric) settings
        self.slider_settings: Dict[str, Any] = {
            "Suggested Model": "",
            "FOV Size": 640,
            "Dynamic FOV Size": 200,
            "Mouse Sensitivity (+/-)": 0.80,
            "Mouse Jitter": 4,
            "Sticky Aim Threshold": 50,
            "Y Offset (Up/Down)": 0,
            "Y Offset (%)": 50,
            "X Offset (Left/Right)": 0,
            "X Offset (%)": 50,
            "EMA Smoothening": 0.5,
            "Kalman Lead Time": 0.10,
            "WiseTheFox Lead Time": 0.15,
            "Shalloe Lead Multiplier": 3.0,
            "Auto Trigger Delay": 0.1,
            "AI Minimum Confidence": 45,
            "AI Confidence Font Size": 20,
            "Corner Radius": 0,
            "Border Thickness": 1,
            "Opacity": 1,
            "SelectedDisplay": 0,
        }

        # Toggle (boolean) settings
        self.toggle_state: Dict[str, bool] = {
            "Aim Assist": False,
            "Sticky Aim": False,
            "Constant AI Tracking": False,
            "Predictions": False,
            "EMA Smoothening": False,
            "Enable Model Switch Keybind": True,
            "Auto Trigger": False,
            "FOV": False,
            "Dynamic FOV": False,
            "Third Person Support": False,
            "Masking": False,
            "Show Detected Player": False,
            "Cursor Check": False,
            "Spray Mode": False,
            "Show FOV": True,
            "Show AI Confidence": False,
            "Show Tracers": False,
            "Collect Data While Playing": False,
            "Auto Label Data": False,
            "Mouse Background Effect": True,
            "Debug Mode": False,
            "UI TopMost": False,
            "X Axis Percentage Adjustment": False,
            "Y Axis Percentage Adjustment": False,
        }

        # Minimize/collapse states for UI sections
        self.minimize_state: Dict[str, bool] = {
            "Aim Assist": False,
            "Aim Config": False,
            "Predictions": False,
            "Auto Trigger": False,
            "FOV Config": False,
            "ESP Config": False,
            "Model Settings": False,
            "Settings Menu": False,
            "X/Y Percentage Adjustment": False,
            "Theme Settings": False,
            "Screen Settings": False,
        }

        # Dropdown (string choice) settings
        self.dropdown_state: Dict[str, str] = {
            "Prediction Method": "Kalman Filter",
            "Detection Area Type": "Closest to Center Screen",
            "Aiming Boundaries Alignment": "Center",
            "Mouse Movement Method": "pynput",   # Linux: pynput or xdotool
            "Screen Capture Method": "mss",       # Linux: mss
            "Tracer Position": "Bottom",
            "Movement Path": "Cubic Bezier",
            "Image Size": "640",
            "Target Class": "Best Confidence",
        }

        # Color settings
        self.color_state: Dict[str, str] = {
            "FOV Color": "#FF8080FF",
            "Detected Player Color": "#FF00FFFF",
            "Theme Color": "#FF722ED1",
        }

    def get_base_dir(self) -> Path:
        """Get the application base directory."""
        return Path(os.path.dirname(os.path.abspath(__file__))).parent

    def get_bin_dir(self) -> Path:
        """Get the bin directory."""
        return self.get_base_dir() / "bin"


# Global singleton
config = Config()


def ensure_directories():
    """Create required directories if they don't exist."""
    base = config.get_bin_dir()
    for subdir in ["configs", "labels", "models", "images"]:
        dir_path = base / subdir
        dir_path.mkdir(parents=True, exist_ok=True)


def save_config(dictionary: Optional[Dict[str, Any]] = None, path: str = "bin/configs/Default.cfg",
                suggested_model: str = "", extra_strings: str = ""):
    """Save configuration dictionary to a JSON file.

    Port of SaveDictionary.WriteJSON
    """
    try:
        # Ensure directory exists
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if dictionary is None:
            # Combine all for saving
            saved = {}
            saved.update(config.binding_settings)
            saved.update(config.slider_settings)
            saved.update(config.toggle_state)
            saved.update(config.minimize_state)
            saved.update(config.dropdown_state)
            saved.update(config.color_state)
        else:
            saved = dict(dictionary)
            
        if suggested_model and "Suggested Model" in saved:
            saved["Suggested Model"] = suggested_model + ".onnx" + extra_strings

        with open(path, "w") as f:
            json.dump(saved, f, indent=4)
    except Exception as e:
        from utils.log_manager import log, LogLevel
        log(LogLevel.ERROR, f"Error writing config: {e}", notify_user=True)


def load_config(dictionary: Dict[str, Any], path: str = "bin/configs/Default.cfg",
                strict: bool = True):
    """Load configuration from a JSON file into the given dictionary.

    Port of SaveDictionary.LoadJSON
    """
    try:
        # Ensure directory exists
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if not os.path.exists(path):
            save_config(dictionary, path)
            return

        with open(path, "r") as f:
            loaded = json.load(f)

        if loaded is None:
            return

        for key, value in loaded.items():
            if key in dictionary:
                # Type-coerce to match existing type
                existing = dictionary[key]
                try:
                    if isinstance(existing, bool):
                        dictionary[key] = bool(value)
                    elif isinstance(existing, int) and not isinstance(existing, bool):
                        dictionary[key] = int(value)
                    elif isinstance(existing, float):
                        dictionary[key] = float(value)
                    else:
                        dictionary[key] = value
                except (TypeError, ValueError):
                    dictionary[key] = value
            elif not strict:
                dictionary[key] = value

    except Exception as e:
        try:
            save_config(dictionary, path)
        except Exception:
            from utils.log_manager import log, LogLevel
            log(LogLevel.ERROR, f"Error loading config: {e}", notify_user=True)
