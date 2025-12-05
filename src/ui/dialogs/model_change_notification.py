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

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QPoint
from PySide6.QtGui import QFont
import qasync


class ModelChangeNotification(QWidget):
    """Professional animated notification widget for model changes."""

    # Class variable to track the current notification
    _current_notification = None

    def __init__(self, model_name, parent=None):
        super().__init__(parent)
        self.model_name = model_name

        # Close any existing notification
        if ModelChangeNotification._current_notification is not None:
            ModelChangeNotification._current_notification.close()
        ModelChangeNotification._current_notification = self

        self.setup_ui()
        self.setup_animation()

    def setup_ui(self):
        """Set up the notification UI."""
        # Configure as a widget (not a dialog)
        self.setFixedSize(450, 130)
        # Enable clipping to parent bounds
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        # Make mouse events pass through to widgets beneath
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # Ensure it paints over other widgets
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("✓ Model Changed")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2ecc71;")
        main_layout.addWidget(title)

        # Model name display
        model_display = QLabel(self.model_name)
        model_font = QFont()
        model_font.setPointSize(11)
        model_font.setBold(True)
        model_display.setFont(model_font)
        model_display.setStyleSheet("color: #2c3e50; padding: 5px; background-color: #ecf0f1; border-radius: 4px;")
        model_display.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(model_display)

        # Auto-close after 3 seconds
        self.auto_close_timer = QTimer()
        self.auto_close_timer.timeout.connect(self.close)
        self.auto_close_timer.start(3000)

    def setup_animation(self):
        """Set up slide-in animation."""
        # Position to top-right inside parent window
        if self.parent():
            parent = self.parent()
            parent_rect = parent.rect()

            # Position inside parent window with 20px padding from edges
            end_x = parent_rect.right() - self.width() - 20
            end_y = parent_rect.top() + 20

            # Start position is off-screen to the right
            start_x = parent_rect.right()
            start_y = end_y
        else:
            # Fallback if no parent
            end_x = 20
            end_y = 20
            start_x = 500
            start_y = 20

        # Slide in from right
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(400)
        self.animation.setStartValue(QRect(start_x, start_y, self.width(), self.height()))
        self.animation.setEndValue(QRect(end_x, end_y, self.width(), self.height()))
        self.animation.finished.connect(self.on_animation_finished)

        # Show and start animation
        self.show()
        # Raise to top of stacking order
        self.raise_()
        self.animation.start()

    def apply_stylesheet(self):
        """Apply professional styling."""
        stylesheet = """
            ModelChangeNotification {
                background-color: #ffffff;
                border: 2px solid #2ecc71;
                border-radius: 8px;
            }
        """
        self.setStyleSheet(stylesheet)

    def showEvent(self, event):
        """Apply stylesheet when shown and bring to front."""
        super().showEvent(event)
        self.apply_stylesheet()
        # Raise to top of sibling widgets
        self.raise_()

    def on_animation_finished(self):
        """Called when animation finishes."""
        pass  # Animation complete

    def closeEvent(self, event):
        """Stop timer on close and clear reference."""
        if self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
        # Clear the current notification reference
        if ModelChangeNotification._current_notification is self:
            ModelChangeNotification._current_notification = None
        super().closeEvent(event)
