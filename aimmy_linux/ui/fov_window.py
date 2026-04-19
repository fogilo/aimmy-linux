from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from utils.config_manager import config
from utils.display_manager import display_manager

class FovWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Timer to force repaint
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(100) # 10 fps is enough for FOV circle as it only changes on settings change or resize
        
    def init_ui(self):
        # Make the window transparent, frameless, and pass through inputs
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Geometry matches primary screen or active display area
        # For simplicity we'll just cover the whole active display
        display_manager.initialize()
        self.setGeometry(0, 0, display_manager.screen_width, display_manager.screen_height)
        
    def update_overlay(self):
        if not config.toggle_state.get("Show FOV", True):
            self.hide()
        else:
            self.show()
            self.update()
            
    def paintEvent(self, event):
        if not config.toggle_state.get("Show FOV", True):
            return
            
        fov_size = config.slider_settings.get("FOV Size", 640)
        radius = fov_size // 2
        
        # Parse color
        hex_color = config.color_state.get("FOV Color", "#FF8080FF")
        # hex is usually #AARRGGBB in Aimmy, but PyQt expects #RRGGBBAA or #RRGGBB.
        # Aimmy uses Avalonia colors which are ARGB. Let's assume solid purple for now if parse fails.
        qcolor = QColor(128, 128, 255, 255) # default light purple
        if len(hex_color) == 9:
            a = int(hex_color[1:3], 16)
            r = int(hex_color[3:5], 16)
            g = int(hex_color[5:7], 16)
            b = int(hex_color[7:9], 16)
            qcolor = QColor(r, g, b, a)
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(qcolor)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw circle at center
        center_x = self.width() // 2
        center_y = self.height() // 2
        painter.drawEllipse(center_x - radius, center_y - radius, fov_size, fov_size)
        painter.end()
