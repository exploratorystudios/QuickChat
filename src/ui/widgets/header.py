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

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QIcon
import qasync
from src.services.ollama_client import ollama_service, OllamaClient
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.model_change_notification import ModelChangeNotification

class Header(QWidget):
    model_changed = Signal(str)
    settings_requested = Signal()
    sidebar_toggle_requested = Signal()

    def __init__(self, on_detection_complete=None):
        super().__init__()
        self.setObjectName("Header")
        self.setFixedHeight(60)
        self.on_detection_complete = on_detection_complete  # Callback when capabilities are loaded
        self.rotation_angle = 0
        self.is_refreshing = False
        self.is_generating = False  # Track if a message is being generated
        self.setup_ui()
        self.load_models()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)

        # Sidebar Toggle Button (left side, beside title)
        self.toggle_sidebar_btn = QPushButton("◀")
        self.toggle_sidebar_btn.setObjectName("SidebarToggleButton")
        self.toggle_sidebar_btn.setFixedSize(32, 32)
        self.toggle_sidebar_btn.setToolTip("Hide sidebar")
        self.toggle_sidebar_btn.clicked.connect(self.on_toggle_sidebar)
        layout.addWidget(self.toggle_sidebar_btn)

        # Title
        title = QLabel("QuickChat")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addStretch()

        # Refresh Models Button
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setToolTip("Refresh available models")
        self.refresh_btn.clicked.connect(self.refresh_models)
        layout.addWidget(self.refresh_btn)

        # Model Selector
        self.model_selector = QComboBox()
        self.model_selector.setFixedWidth(200)
        # Set maximum dropdown height to show ~6 items before scrolling
        self.model_selector.setMaxVisibleItems(6)
        self.model_selector.currentTextChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_selector)

        # Settings Button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(self.settings_btn)

    @qasync.asyncSlot()
    async def load_models(self):
        models = await ollama_service.list_models()
        self.model_selector.clear()
        if models:
            self.model_selector.addItems(models)
        else:
            self.model_selector.addItem("No models found")

    @qasync.asyncSlot(str)
    async def on_model_changed(self, text):
        """Handle model selection change with instant capability detection via Ollama API."""
        if not text or text == "No models found":
            return

        print(f"[Header] Model selected: {text}")

        try:
            print(f"[Header] Fetching capabilities for: {text}")
            # Get capabilities from the Ollama show() API (instant, uses cache)
            capabilities = await ollama_service.get_model_capabilities(text)

            print(f"[Header] Capabilities loaded for {text}: {capabilities}")

            # Call callback to update UI with capabilities
            if self.on_detection_complete:
                self.on_detection_complete(text)

            # Emit signal to notify other components
            self.model_changed.emit(text)

            # Show model change notification - reparent to main window to ensure it's on top
            # Find the main window
            main_window = self.window()
            notification = ModelChangeNotification(text, main_window)
            notification.show()

        except Exception as e:
            print(f"[Header] Error fetching capabilities: {e}")
            # Even on error, call the callback so UI is updated
            if self.on_detection_complete:
                self.on_detection_complete(text)

            # Still show notification even on error
            notification = ModelChangeNotification(text, self)
            notification.show()

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Settings saved, maybe reload theme or other things
            self.settings_requested.emit()

    @qasync.asyncSlot()
    async def refresh_models(self):
        """Refresh the list of available models and restore previously selected model."""
        # Prevent refreshing while any generation is happening
        main_window = self.window()
        if hasattr(main_window, 'is_any_generation_active') and main_window.is_any_generation_active():
            print("[Header] Cannot refresh models while generating. Please wait...")
            return

        if self.is_refreshing:
            return

        # Save current selection
        current_model = self.model_selector.currentText()

        self.is_refreshing = True
        self.refresh_btn.setEnabled(False)

        # Start rotation animation
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.rotate_icon)
        self.rotation_timer.start(50)

        try:
            # Reload models from Ollama
            await self.load_models()

            # Restore previous selection if it still exists
            if current_model and current_model != "No models found":
                index = self.model_selector.findText(current_model)
                if index >= 0:
                    self.model_selector.setCurrentIndex(index)
                    print(f"[Header] Restored model selection to: {current_model}")
        finally:
            # Stop animation
            self.rotation_timer.stop()
            self.refresh_btn.setEnabled(True)
            self.is_refreshing = False
            self.rotation_angle = 0
            self.refresh_btn.setText("🔄 Refresh")

    def rotate_icon(self):
        """Rotate the refresh icon."""
        self.rotation_angle = (self.rotation_angle + 15) % 360
        # Note: We use text rotation with CSS transform for simplicity
        # The emoji will appear to spin smoothly

    def set_generating(self, is_generating):
        """Disable model selector during message generation to prevent async conflicts."""
        self.is_generating = is_generating
        self.model_selector.setEnabled(not is_generating)

    def on_toggle_sidebar(self):
        """Emit signal to toggle sidebar."""
        self.sidebar_toggle_requested.emit()

    def set_sidebar_collapsed(self, is_collapsed):
        """Update toggle button appearance based on sidebar state."""
        self.toggle_sidebar_btn.setText("▶" if is_collapsed else "◀")
        self.toggle_sidebar_btn.setToolTip("Show sidebar" if is_collapsed else "Hide sidebar")
