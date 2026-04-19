from PyQt6.QtWidgets import QSlider, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt

class CustomSlider(QWidget):
    def __init__(self, name: str, min_val: int, max_val: int, current_val: int, parent=None):
        super().__init__(parent)
        self.name = name
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(f"{name}: {current_val}")
        self.label.setStyleSheet("color: white; font-weight: bold;")
        self.label.setMinimumWidth(180)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(current_val)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border-radius: 4px;
                height: 8px;
                background: #2a2a2a;
            }
            QSlider::sub-page:horizontal {
                background: #722ED1;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 16px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 8px;
            }
        """)
        
        self.slider.valueChanged.connect(self.on_value_changed)
        
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        self.setLayout(layout)
        
    def on_value_changed(self, val):
        self.label.setText(f"{self.name}: {val}")
        
    def value(self):
        return self.slider.value()

    def setValue(self, val):
        self.slider.setValue(val)
