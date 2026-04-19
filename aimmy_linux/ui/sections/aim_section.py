from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QFormLayout
from ui.widgets import CustomSlider, CustomToggle, CustomDropdown
from utils.config_manager import config, save_config

class AimSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # General Settings Group
        general_group = QGroupBox("General Aim Settings")
        general_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        general_layout = QVBoxLayout()
        
        self.aim_assist_toggle = CustomToggle("Enable Aim Assist")
        self.aim_assist_toggle.setChecked(config.toggle_state.get("Aim Assist", False))
        self.aim_assist_toggle.toggled.connect(lambda v: self.update_toggle("Aim Assist", v))
        general_layout.addWidget(self.aim_assist_toggle)
        
        self.trigger_toggle = CustomToggle("Auto Trigger")
        self.trigger_toggle.setChecked(config.toggle_state.get("Auto Trigger", False))
        self.trigger_toggle.toggled.connect(lambda v: self.update_toggle("Auto Trigger", v))
        general_layout.addWidget(self.trigger_toggle)
        
        self.smoothing_slider = CustomSlider("EMA Smoothening", 0, 100, int(config.slider_settings.get("EMA Smoothening", 0.5) * 100))
        self.smoothing_slider.slider.valueChanged.connect(lambda v: self.update_slider_float("EMA Smoothening", v, 100.0))
        general_layout.addWidget(self.smoothing_slider)
        
        general_group.setLayout(general_layout)
        layout.addWidget(general_group)
        
        # FOV Group
        fov_group = QGroupBox("FOV Settings")
        fov_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        fov_layout = QVBoxLayout()
        
        self.fov_toggle = CustomToggle("Show FOV Overlay")
        self.fov_toggle.setChecked(config.toggle_state.get("Show FOV", True))
        self.fov_toggle.toggled.connect(lambda v: self.update_toggle("Show FOV", v))
        fov_layout.addWidget(self.fov_toggle)
        
        self.fov_slider = CustomSlider("FOV Size", 10, 1000, config.slider_settings.get("FOV Size", 640))
        self.fov_slider.slider.valueChanged.connect(lambda v: self.update_slider("FOV Size", v))
        fov_layout.addWidget(self.fov_slider)
        
        fov_group.setLayout(fov_layout)
        layout.addWidget(fov_group)
        
        # Keybinds Group
        keybind_group = QGroupBox("Keybindings")
        keybind_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        keybind_layout = QFormLayout()
        
        # Simple dropdown for keybinds for now, in a real app this would be a custom key catcher
        self.aim_key = CustomDropdown(["Button.left", "Button.right", "Button.middle", "Key.shift", "Key.alt_l", "Key.ctrl_l"])
        self.aim_key.setCurrentText(config.binding_settings.get("Aim Keybind", "Button.right"))
        self.aim_key.currentTextChanged.connect(lambda v: self.update_keybind("Aim Keybind", v))
        
        label = QLabel("Aim Keybind:")
        label.setStyleSheet("color: white;")
        keybind_layout.addRow(label, self.aim_key)
        
        keybind_group.setLayout(keybind_layout)
        layout.addWidget(keybind_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def update_toggle(self, key: str, value: bool):
        config.toggle_state[key] = value
        save_config(None) # Save will dump config

    def update_slider(self, key: str, value: int):
        config.slider_settings[key] = value
        save_config(None)

    def update_slider_float(self, key: str, value: int, divisor: float):
        config.slider_settings[key] = value / divisor
        save_config(None)
        
    def update_keybind(self, key: str, value: str):
        config.binding_settings[key] = value
        save_config(None)
