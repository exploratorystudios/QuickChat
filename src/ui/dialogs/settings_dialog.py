# Copyright 2025 Exploratory Studios
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QSpinBox, QCheckBox, QPushButton, QFormLayout)
from src.services.settings_manager import settings_manager
from src.services.ollama_client import ollama_service
from config.theme import DARK_THEME
import qasync

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 350)
        self.setup_ui()
        # Load models asynchronously
        asyncio.create_task(self.load_models_async())
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        form_layout.addRow("Theme:", self.theme_combo)
        
        # Default Model (populated from detected models)
        self.model_input = QComboBox()
        self.model_input.setEditable(False)  # Read-only dropdown
        self.model_input.addItem("Loading models...")  # Placeholder
        form_layout.addRow("Default Model:", self.model_input)
        
        # Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 32)
        form_layout.addRow("Font Size:", self.font_size_spin)
        
        # Enter to Send
        self.enter_send_check = QCheckBox()
        form_layout.addRow("Enter to Send:", self.enter_send_check)
        
        layout.addLayout(form_layout)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # Styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {DARK_THEME['background']};
                color: {DARK_THEME['text_primary']};
            }}
            QLabel {{
                color: {DARK_THEME['text_primary']};
            }}
            QCheckBox {{
                color: {DARK_THEME['text_primary']};
            }}
        """)

    async def load_models_async(self):
        """Load available models from Ollama asynchronously."""
        try:
            models = await ollama_service.list_models()

            # Clear placeholder
            self.model_input.clear()

            if models:
                self.model_input.addItems(models)
                # Restore previously selected default model if it exists
                default_model = settings_manager.get("default_model", "llama3")
                index = self.model_input.findText(default_model)
                if index >= 0:
                    self.model_input.setCurrentIndex(index)
                else:
                    # If saved model not found, use first available
                    self.model_input.setCurrentIndex(0)
            else:
                self.model_input.addItem("No models found")
        except Exception as e:
            print(f"[SettingsDialog] Error loading models: {e}")
            self.model_input.clear()
            self.model_input.addItem("Error loading models")

    def load_settings(self):
        self.theme_combo.setCurrentText(settings_manager.get("theme", "dark"))
        # Default model will be set by load_models_async
        self.font_size_spin.setValue(settings_manager.get("font_size", 14))
        self.enter_send_check.setChecked(settings_manager.get("enter_to_send", True))

    def save_settings(self):
        settings_manager.set("theme", self.theme_combo.currentText())
        settings_manager.set("default_model", self.model_input.currentText())
        settings_manager.set("font_size", self.font_size_spin.value())
        settings_manager.set("enter_to_send", self.enter_send_check.isChecked())
        self.accept()
