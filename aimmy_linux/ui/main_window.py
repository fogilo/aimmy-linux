import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QStackedWidget, QListWidget, QPushButton, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from ui.sections import AimSection, ModelSection, SettingsSection
from ui.fov_window import FovWindow
from ui.overlay import EspOverlay
from utils.config_manager import config
from input.input_binding import input_binding_manager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ai_manager = None
        self.init_ui()
        
        # Initialize Overlays
        self.fov_window = FovWindow()
        self.esp_overlay = EspOverlay()
        
        # We need a way to pass ai_manager to esp_overlay, but we don't start AI until requested
        
    def init_ui(self):
        self.setWindowTitle("Aimmy Linux")
        self.setFixedSize(800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121212;
            }
            QLabel {
                color: white;
            }
        """)
        
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1e1e1e; border-right: 1px solid #2a2a2a;")
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        
        title = QLabel("AIMMY LINUX")
        title.setStyleSheet("color: #722ED1; font-weight: bold; font-size: 20px; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title)
        
        sidebar_layout.addSpacing(30)
        
        self.nav_list = QListWidget()
        self.nav_list.addItems(["Aim Settings", "Model Selection", "Global Settings"])
        self.nav_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QListWidget::item {
                padding: 10px;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #722ED1;
            }
        """)
        self.nav_list.currentRowChanged.connect(self.change_page)
        sidebar_layout.addWidget(self.nav_list)
        
        sidebar_layout.addStretch()
        
        self.toggle_ai_btn = QPushButton("Start Aimmy")
        self.toggle_ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #722ED1;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5b24a8;
            }
        """)
        self.toggle_ai_btn.clicked.connect(self.toggle_ai)
        sidebar_layout.addWidget(self.toggle_ai_btn)
        
        sidebar.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar)
        
        # Main Content Area
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #121212;")
        
        self.aim_section = AimSection()
        self.model_section = ModelSection()
        self.settings_section = SettingsSection()
        
        self.stacked_widget.addWidget(self.aim_section)
        self.stacked_widget.addWidget(self.model_section)
        self.stacked_widget.addWidget(self.settings_section)
        
        main_layout.addWidget(self.stacked_widget)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        self.nav_list.setCurrentRow(0)
        
    def change_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        
    def toggle_ai(self):
        if self.ai_manager is None:
            # Try to start AI
            # Get active model
            model_item = self.model_section.model_list.currentItem()
            if not model_item:
                from utils.log_manager import log, LogLevel
                log(LogLevel.WARNING, "No model selected. Please select a model in Model Settings.", notify_user=True)
                # auto select first if available
                if self.model_section.model_list.count() > 0:
                    self.model_section.model_list.setCurrentRow(0)
                    model_item = self.model_section.model_list.currentItem()
                else:
                    return
            
            model_name = model_item.text()
            model_dir = config.get_bin_dir() / "models"
            model_path = str(model_dir / model_name)
            
            from ai.ai_manager import AIManager
            
            # Setup binds
            for binding_id, key_code in config.binding_settings.items():
                input_binding_manager.setup_default(binding_id, key_code)
                
            self.ai_manager = AIManager(model_path)
            self.esp_overlay.set_ai_manager(self.ai_manager)
            self.toggle_ai_btn.setText("Stop Aimmy")
            self.toggle_ai_btn.setStyleSheet("background-color: #d12e2e; color: white; font-weight: bold; font-size: 16px; padding: 10px; border-radius: 5px; border: none;")
        else:
            # Stop AI
            self.ai_manager.dispose()
            self.ai_manager = None
            self.esp_overlay.set_ai_manager(None)
            input_binding_manager.stop_listening()
            self.toggle_ai_btn.setText("Start Aimmy")
            self.toggle_ai_btn.setStyleSheet("background-color: #722ED1; color: white; font-weight: bold; font-size: 16px; padding: 10px; border-radius: 5px; border: none;")
            
    def closeEvent(self, event):
        if self.ai_manager:
            self.ai_manager.dispose()
        self.fov_window.close()
        self.esp_overlay.close()
        input_binding_manager.stop_listening()
        event.accept()

def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
