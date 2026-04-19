import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QListWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from utils.config_manager import config

class ModelSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Models Group
        model_group = QGroupBox("Available AI Models")
        model_group.setStyleSheet("QGroupBox { color: white; font-weight: bold; }")
        model_layout = QVBoxLayout()
        
        self.model_list = QListWidget()
        self.model_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #722ED1;
                border-radius: 2px;
            }
        """)
        self.refresh_models()
        model_layout.addWidget(self.model_list)
        
        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("background-color: #2a2a2a; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.refresh_btn.clicked.connect(self.refresh_models)
        
        self.load_btn = QPushButton("Load Model")
        self.load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_btn.setStyleSheet("background-color: #722ED1; color: white; padding: 8px; border-radius: 4px; font-weight: bold;")
        self.load_btn.clicked.connect(self.load_model)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.load_btn)
        model_layout.addLayout(btn_layout)
        
        self.status_label = QLabel("Active Model: None")
        self.status_label.setStyleSheet("color: #AAAAAA; font-style: italic;")
        model_layout.addWidget(self.status_label)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def refresh_models(self):
        self.model_list.clear()
        models_dir = config.get_bin_dir() / "models"
        if not models_dir.exists():
            models_dir.mkdir(parents=True, exist_ok=True)
            
        for file in os.listdir(models_dir):
            if file.endswith(".onnx"):
                self.model_list.addItem(file)
                
    def load_model(self):
        selected = self.model_list.currentItem()
        if selected:
            model_name = selected.text()
            self.status_label.setText(f"Active Model: {model_name}")
            # The actual model loading will be handled by the main window / AI manager bridging.
            # We can emit a signal here in a real implementation.
