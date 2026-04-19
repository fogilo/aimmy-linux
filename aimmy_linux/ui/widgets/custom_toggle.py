from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt

class CustomToggle(QCheckBox):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QCheckBox {
                color: white;
                font-weight: bold;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #722ED1;
            }
        """)
