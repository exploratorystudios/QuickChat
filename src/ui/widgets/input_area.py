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

from PySide6.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QPushButton, QVBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QPixmap

class InputArea(QWidget):
    send_message = Signal(str, str) # Emits message content and image path
    thinking_toggled = Signal(bool) # Emits thinking enabled state
    vision_toggled = Signal(bool) # Emits vision enabled state
    stop_requested = Signal() # Emits when user clicks Stop button

    def __init__(self):
        super().__init__()
        self.setObjectName("InputArea")
        self.thinking_enabled = True
        self.thinking_supported = True  # Track if current model supports thinking
        self.vision_enabled = False  # Track if vision is enabled
        self.vision_supported = False  # Track if current model supports vision
        self.is_generating = False  # Track if model is currently generating (response)
        self.is_generating_title = False  # Track if title is being generated
        self.attached_image_path = None  # Store path to attached image
        self.setup_ui()
        # Set initial height to minimum (text input + buttons + margins)
        self.setFixedHeight(125)  # 60 (text input) + 35 (buttons) + 30 (margins/spacing)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(8)

        # Buttons and Image Preview row
        buttons_preview_row = QHBoxLayout()
        buttons_preview_row.setSpacing(8)
        buttons_preview_row.setContentsMargins(0, 0, 0, 0)

        # Buttons sub-layout
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        # Thinking Toggle Button
        self.thinking_btn = QPushButton("🧠 Thinking")
        self.thinking_btn.setObjectName("ThinkingButton")
        self.thinking_btn.setFixedWidth(125)
        self.thinking_btn.setFixedHeight(35)
        self.thinking_btn.clicked.connect(self.on_thinking_toggle)
        self.update_thinking_button_style()
        buttons_layout.addWidget(self.thinking_btn)

        # Vision Toggle Button
        self.vision_btn = QPushButton("🖼️ Vision")
        self.vision_btn.setObjectName("VisionButton")
        self.vision_btn.setFixedWidth(125)
        self.vision_btn.setFixedHeight(35)
        self.vision_btn.setEnabled(False)
        self.vision_btn.clicked.connect(self.on_vision_toggle)
        self.update_vision_button_style()
        buttons_layout.addWidget(self.vision_btn)

        buttons_preview_row.addLayout(buttons_layout)

        # Image Preview Widget (hidden by default) - larger, can expand into chat area
        self.image_preview_widget = QWidget()
        self.image_preview_widget.setVisible(False)
        self.image_preview_widget.setMaximumHeight(100)
        preview_layout = QHBoxLayout(self.image_preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(8)

        # Image preview label - larger thumbnail
        self.image_preview_label = QLabel()
        self.image_preview_label.setFixedSize(80, 80)
        self.image_preview_label.setScaledContents(True)
        preview_layout.addWidget(self.image_preview_label)

        # Filename label
        self.image_filename_label = QLabel()
        self.image_filename_label.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        self.image_filename_label.setWordWrap(True)
        preview_layout.addWidget(self.image_filename_label)

        # Remove image button - large and red
        self.remove_image_btn = QPushButton("✕")
        self.remove_image_btn.setObjectName("RemoveImageButton")
        self.remove_image_btn.setFixedSize(50, 50)
        self.remove_image_btn.setStyleSheet("""
            QPushButton#RemoveImageButton {
                background-color: #ef4444;
                border: 2px solid #dc2626;
                border-radius: 4px;
                color: white;
                font-weight: bold;
                font-size: 24px;
                padding: 0px;
            }
            QPushButton#RemoveImageButton:hover {
                background-color: #dc2626;
            }
            QPushButton#RemoveImageButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.remove_image_btn.clicked.connect(self.remove_image)
        preview_layout.addWidget(self.remove_image_btn)
        preview_layout.addStretch()

        buttons_preview_row.addWidget(self.image_preview_widget)
        buttons_preview_row.addStretch()

        main_layout.addLayout(buttons_preview_row)

        # Text Input and Send Button row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        # Attach Image Button (LEFT side, before text input)
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setObjectName("AttachButton")
        self.attach_btn.setFixedSize(35, 35)
        self.attach_btn.setEnabled(False)  # Disabled until vision is supported and enabled
        self.attach_btn.clicked.connect(self.open_file_dialog)
        self.update_attach_button_style()
        input_row.addWidget(self.attach_btn)

        # Text Input
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Type a message...")
        self.text_input.setMinimumHeight(60)  # Minimum height for single line
        self.text_input.setMaximumHeight(180)  # Maximum height for ~4 lines
        self.text_input.setFixedHeight(60)  # Start at minimum height
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.text_input.textChanged.connect(self.on_text_changed)
        self.text_input.installEventFilter(self) # Handle Enter key
        input_row.addWidget(self.text_input)

        # Send/Stop Button
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setFixedSize(80, 35)
        self.send_btn.clicked.connect(self.on_send)
        input_row.addWidget(self.send_btn)

        main_layout.addLayout(input_row)

    def eventFilter(self, obj, event):
        if obj == self.text_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                # Only send if not currently generating (response or title)
                if not self.is_generating and not self.is_generating_title:
                    self.on_send()
                return True
        return super().eventFilter(obj, event)

    def update_thinking_button_style(self):
        """Update button style based on thinking state and support."""
        if not self.thinking_supported:
            # Red when thinking is NOT supported by the model
            self.thinking_btn.setStyleSheet("""
                QPushButton#ThinkingButton {
                    background-color: #ef4444;
                    border: 2px solid #dc2626;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#ThinkingButton:hover {
                    background-color: #dc2626;
                }
                QPushButton#ThinkingButton:pressed {
                    background-color: #b91c1c;
                }
            """)
        elif self.thinking_enabled:
            # Blue highlight when thinking is ON
            self.thinking_btn.setStyleSheet("""
                QPushButton#ThinkingButton {
                    background-color: #3b82f6;
                    border: 2px solid #2563eb;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#ThinkingButton:hover {
                    background-color: #2563eb;
                }
                QPushButton#ThinkingButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
        else:
            # Default gray color when thinking is OFF
            self.thinking_btn.setStyleSheet("""
                QPushButton#ThinkingButton {
                    background-color: #6b7280;
                    border: 2px solid #4b5563;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#ThinkingButton:hover {
                    background-color: #5a6370;
                }
                QPushButton#ThinkingButton:pressed {
                    background-color: #4b5563;
                }
            """)

    def update_vision_button_style(self):
        """Update button style based on vision state and support."""
        if not self.vision_supported:
            # Red when vision is NOT supported by the model
            self.vision_btn.setStyleSheet("""
                QPushButton#VisionButton {
                    background-color: #ef4444;
                    border: 2px solid #dc2626;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#VisionButton:hover {
                    background-color: #dc2626;
                }
                QPushButton#VisionButton:pressed {
                    background-color: #b91c1c;
                }
            """)
        elif self.vision_enabled:
            # Blue highlight when vision is ON
            self.vision_btn.setStyleSheet("""
                QPushButton#VisionButton {
                    background-color: #3b82f6;
                    border: 2px solid #2563eb;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#VisionButton:hover {
                    background-color: #2563eb;
                }
                QPushButton#VisionButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
        else:
            # Default gray color when vision is OFF
            self.vision_btn.setStyleSheet("""
                QPushButton#VisionButton {
                    background-color: #6b7280;
                    border: 2px solid #4b5563;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 0px;
                }
                QPushButton#VisionButton:hover {
                    background-color: #5a6370;
                }
                QPushButton#VisionButton:pressed {
                    background-color: #4b5563;
                }
            """)

    def update_attach_button_state(self):
        """Update attachment button enabled state based on vision support and enablement."""
        # Only enable attach button if vision is both supported AND enabled
        self.attach_btn.setEnabled(self.vision_supported and self.vision_enabled)
        self.update_attach_button_style()

    def update_attach_button_style(self):
        """Update attachment button styling based on enabled/disabled state."""
        if self.attach_btn.isEnabled():
            # Enabled state - bright blue
            self.attach_btn.setStyleSheet("""
                QPushButton#AttachButton {
                    background-color: #3b82f6;
                    border: 2px solid #2563eb;
                    border-radius: 4px;
                    color: white;
                    font-size: 16px;
                    padding: 0px;
                }
                QPushButton#AttachButton:hover {
                    background-color: #2563eb;
                }
                QPushButton#AttachButton:pressed {
                    background-color: #1d4ed8;
                }
            """)
        else:
            # Disabled state - muted gray with reduced opacity
            self.attach_btn.setStyleSheet("""
                QPushButton#AttachButton {
                    background-color: #4b5563;
                    border: 2px solid #3a414f;
                    border-radius: 4px;
                    color: #6b7280;
                    font-size: 16px;
                    padding: 0px;
                    opacity: 0.5;
                }
                QPushButton#AttachButton:hover {
                    background-color: #4b5563;
                }
                QPushButton#AttachButton:pressed {
                    background-color: #4b5563;
                }
            """)

    def on_thinking_toggle(self):
        """Toggle thinking mode on/off."""
        self.thinking_enabled = not self.thinking_enabled
        self.update_thinking_button_style()
        self.thinking_toggled.emit(self.thinking_enabled)

    def on_vision_toggle(self):
        """Toggle vision mode on/off."""
        self.vision_enabled = not self.vision_enabled

        # Remove attached image if vision is being disabled
        if not self.vision_enabled and self.attached_image_path:
            self.remove_image()

        self.update_vision_button_style()
        self.update_attach_button_state()  # This also calls update_attach_button_style()
        self.vision_toggled.emit(self.vision_enabled)

    def on_send(self):
        # If generating title OR response, don't allow sending
        # During response generation: silently ignore to prevent accidental sends during setup gap
        # During title generation: silently ignore to prevent interference
        if self.is_generating_title or self.is_generating:
            return

        content = self.text_input.toPlainText().strip()
        image_path = self.attached_image_path if self.vision_enabled and self.attached_image_path else ""

        if content or image_path:
            self.send_message.emit(content, image_path)
            self.text_input.clear()
            if image_path:
                self.remove_image()

    def is_thinking_enabled(self):
        """Returns whether thinking mode is enabled."""
        return self.thinking_enabled

    def set_thinking_supported(self, supported):
        """
        Enable or disable the thinking button based on model support.

        Args:
            supported (bool): Whether the current model supports thinking.
        """
        self.thinking_supported = supported
        self.thinking_btn.setEnabled(supported)

        # If model supports thinking, enable it by default
        if supported and not self.thinking_enabled:
            self.thinking_enabled = True
        # If model doesn't support thinking, disable it
        elif not supported and self.thinking_enabled:
            self.thinking_enabled = False

        # Update button style to reflect support status
        self.update_thinking_button_style()

        # Emit signal if state changed
        if supported and self.thinking_enabled:
            self.thinking_toggled.emit(True)
        elif not supported and not self.thinking_enabled:
            self.thinking_toggled.emit(False)

    def on_text_changed(self):
        """Adjust input area height based on text content."""
        # Get document height
        doc_height = self.text_input.document().size().height()
        # Clamp between min and max
        new_height = max(60, min(int(doc_height) + 10, 180))
        self.text_input.setFixedHeight(new_height)
        # Keep button at fixed 35px height
        self.send_btn.setFixedHeight(35)
        # Adjust parent widget height accordingly
        self.setFixedHeight(new_height + 65)  # 65 = buttons row + margins

    def set_generating(self, is_generating):
        """
        Set the generating state and update button appearance.
        User can still type, but send button is disabled until generation completes.
        Stop button remains enabled so user can stop generation.

        Args:
            is_generating (bool): Whether the model is currently generating.
        """
        self.is_generating = is_generating
        # Keep text input enabled so user can type
        # Button is always enabled (Send when not generating, Stop when generating)
        self.send_btn.setEnabled(True)

        if is_generating:
            self.send_btn.setText("Stop")
            self.send_btn.setObjectName("StopButton")
            self.send_btn.setStyleSheet("""
                QPushButton#StopButton {
                    background-color: #ef4444;
                    border: 2px solid #dc2626;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton#StopButton:hover {
                    background-color: #dc2626;
                }
                QPushButton#StopButton:pressed {
                    background-color: #b91c1c;
                }
            """)
        else:
            self.send_btn.setText("Send")
            self.send_btn.setObjectName("PrimaryButton")
            self.send_btn.setStyleSheet("")  # Reset to default theme styling

    def is_stop_requested(self):
        """Returns True if user clicked Stop."""
        return self.is_generating

    def set_generating_title(self, is_generating):
        """
        Set the title generation state.
        When title is being generated, user cannot send messages (silently blocked).

        Args:
            is_generating (bool): Whether the title is currently being generated.
        """
        self.is_generating_title = is_generating

    def set_vision_supported(self, supported):
        """
        Enable or disable the vision button based on model support.

        Args:
            supported (bool): Whether the current model supports vision.
        """
        self.vision_supported = supported
        self.vision_btn.setEnabled(supported)

        # If model supports vision, enable it by default
        if supported and not self.vision_enabled:
            self.vision_enabled = True
        # If model doesn't support vision, disable it
        elif not supported and self.vision_enabled:
            self.vision_enabled = False

        # Update button style to reflect support status
        self.update_vision_button_style()
        # Update attachment button state based on vision support
        self.update_attach_button_state()

        # Emit signal if state changed
        if supported and self.vision_enabled:
            self.vision_toggled.emit(True)
        elif not supported and not self.vision_enabled:
            self.vision_toggled.emit(False)

    def open_file_dialog(self):
        """Open file dialog to select an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )

        if file_path:
            self.attach_image(file_path)

    def attach_image(self, file_path):
        """
        Attach an image and show preview.

        Args:
            file_path (str): Path to the image file.
        """
        self.attached_image_path = file_path

        # Show preview thumbnail
        pixmap = QPixmap(file_path)
        self.image_preview_label.setPixmap(pixmap)

        # Show filename
        import os
        filename = os.path.basename(file_path)
        self.image_filename_label.setText(filename)

        # Show preview widget
        self.image_preview_widget.setVisible(True)

    def remove_image(self):
        """Remove the attached image."""
        self.attached_image_path = None
        self.image_preview_widget.setVisible(False)
        self.image_preview_label.clear()
        self.image_filename_label.clear()
