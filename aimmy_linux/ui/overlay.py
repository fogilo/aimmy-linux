from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen
from utils.config_manager import config
from utils.display_manager import display_manager

class EspOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.ai_manager = None
        self.init_ui()
        
        # Fast timer for ESP update (60 fps)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_overlay)
        self.timer.start(16)
        
    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        display_manager.initialize()
        self.setGeometry(0, 0, display_manager.screen_width, display_manager.screen_height)
        
    def set_ai_manager(self, ai_manager):
        self.ai_manager = ai_manager
        
    def update_overlay(self):
        if not config.toggle_state.get("Show Detected Player", False):
            self.hide()
        else:
            self.show()
            self.update()
            
    def paintEvent(self, event):
        if not config.toggle_state.get("Show Detected Player", False):
            return
        if not self.ai_manager:
            return
            
        box = getattr(self.ai_manager, "_last_detection_box", None)
        if not box or box == (0.0, 0.0, 0.0, 0.0):
            return
            
        x, y, w, h = box
        
        # Color parsing
        hex_color = config.color_state.get("Detected Player Color", "#FF00FFFF")
        qcolor = QColor(0, 255, 255, 255) # cyan
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
        
        # Draw bounding box
        rect = QRectF(x - w/2, y - h/2, w, h)
        painter.drawRect(rect)
        
        painter.end()
