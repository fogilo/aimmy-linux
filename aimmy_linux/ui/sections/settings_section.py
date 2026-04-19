from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QPushButton
from PyQt6.QtCore import Qt
from ui.widgets import CustomToggle
from utils.config_manager import config, save_config

class SettingsSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Display Settings
        disp_group = QGroupBox("Display & Overlays")
        disp_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        disp_layout = QVBoxLayout()
        
        self.esp_toggle = CustomToggle("Show ESP Overlay")
        self.esp_toggle.setChecked(config.toggle_state.get("Show Detected Player", False))
        self.esp_toggle.toggled.connect(lambda v: self.update_toggle("Show Detected Player", v))
        disp_layout.addWidget(self.esp_toggle)
        
        self.tracer_toggle = CustomToggle("Show Tracers")
        self.tracer_toggle.setChecked(config.toggle_state.get("Show Tracers", False))
        self.tracer_toggle.toggled.connect(lambda v: self.update_toggle("Show Tracers", v))
        disp_layout.addWidget(self.tracer_toggle)
        
        disp_group.setLayout(disp_layout)
        layout.addWidget(disp_group)
        
        # Data & Config Settings
        data_group = QGroupBox("Configuration")
        data_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        data_layout = QVBoxLayout()
        
        self.save_btn = QPushButton("Save Configuration to Disk")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("background-color: #2a2a2a; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.save_btn.clicked.connect(self.force_save)
        data_layout.addWidget(self.save_btn)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def update_toggle(self, key: str, value: bool):
        config.toggle_state[key] = value
        save_config(None)
        
    def force_save(self):
        save_config(None)
        # In a real app we might show a toast notification here
