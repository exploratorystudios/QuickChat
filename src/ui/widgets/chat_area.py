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

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QApplication, QToolButton
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from src.ui.widgets.message_widget import MessageWidget

class ChatArea(QWidget):
    fork_requested = Signal(int)

    def __init__(self):
        super().__init__()
        self.setObjectName("ChatArea")
        self.user_scrolled_up = False  # Track if user has manually scrolled up
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Connect scrollbar changes to detect user scrolling and update nav buttons
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_moved)
        scrollbar.rangeChanged.connect(self._on_scroll_range_changed)

        # Container for messages
        self.message_container = QWidget()
        self.message_container.setObjectName("MessageContainer")
        self.message_layout = QVBoxLayout(self.message_container)

        # Messenger-style padding with more space on sides
        self.message_layout.setContentsMargins(40, 20, 40, 20)
        self.message_layout.setSpacing(12)  # Tighter spacing between messages
        self.message_layout.addStretch()

        self.scroll_area.setWidget(self.message_container)
        layout.addWidget(self.scroll_area)

        # Overlay navigation buttons (added after layout so they float on top)
        self._create_scroll_buttons()

    def add_message(self, role, content, thinking=None, message_id=None, images=None):
        """Add a new message to the chat area."""
        message_widget = MessageWidget(role, content, thinking, message_id, images)
        message_widget.fork_requested.connect(self.fork_requested.emit)
        self.message_layout.addWidget(message_widget)

        # Reset scroll state when a new message is added (user intent to continue conversation)
        self.user_scrolled_up = False

        # Scroll to bottom when a new message is added
        self.scroll_to_bottom()
        return message_widget

    def clear(self):
        """Clear all messages."""
        while self.message_layout.count():
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def detach_widgets(self):
        """Remove all message widgets from the layout without destroying them.

        Used when switching away from a chat that is still streaming — the
        widgets (including the live streaming bubble) are kept alive in memory
        so the stream can continue writing to them in the background.

        Returns a list of widgets for later restoration via restore_widgets().
        """
        widgets = []
        while self.message_layout.count():
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.setParent(None)  # Detach without destroying
                widgets.append(widget)
        # Re-add stretch so the now-empty layout is ready for new messages
        self.message_layout.addStretch()
        return widgets

    def restore_widgets(self, widgets):
        """Clear the current display and restore a previously detached set of widgets."""
        # Destroy whatever is currently shown
        while self.message_layout.count():
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        # Reattach the restored widgets
        for widget in widgets:
            widget.setParent(self.message_container)
            widget.show()
            self.message_layout.addWidget(widget)
        self.user_scrolled_up = False
        QApplication.processEvents()
        self.message_container.updateGeometry()
        QTimer.singleShot(0, self._do_scroll)

    def scroll_to_bottom(self):
        """Scroll to the bottom of the chat area if user hasn't scrolled up."""
        # Don't scroll if user has manually scrolled up
        if self.user_scrolled_up:
            return

        # Force layout update before scrolling
        QApplication.processEvents()
        self.message_container.updateGeometry()

        # Use QTimer to ensure scroll happens after layout is fully calculated
        QTimer.singleShot(0, self._do_scroll)

    def _do_scroll(self):
        """Actually perform the scroll to bottom."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _create_scroll_buttons(self):
        """Create floating scroll-to-top and scroll-to-bottom overlay buttons."""
        btn_style = """
            QToolButton {
                background-color: rgba(100, 100, 100, 200);
                color: white;
                border: 1px solid rgba(255, 255, 255, 50);
                border-radius: 17px;
                font-size: 15px;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: rgba(130, 130, 130, 230);
            }
            QToolButton:pressed {
                background-color: rgba(70, 70, 70, 255);
            }
        """

        self.scroll_top_btn = QToolButton(self)
        self.scroll_top_btn.setText("↑")
        self.scroll_top_btn.setFixedSize(34, 34)
        self.scroll_top_btn.setStyleSheet(btn_style)
        self.scroll_top_btn.setToolTip("Scroll to top")
        self.scroll_top_btn.clicked.connect(lambda: self._smooth_scroll_to(0))
        self.scroll_top_btn.hide()

        self.scroll_bottom_btn = QToolButton(self)
        self.scroll_bottom_btn.setText("↓")
        self.scroll_bottom_btn.setFixedSize(34, 34)
        self.scroll_bottom_btn.setStyleSheet(btn_style)
        self.scroll_bottom_btn.setToolTip("Scroll to bottom")
        self.scroll_bottom_btn.clicked.connect(
            lambda: self._smooth_scroll_to(self.scroll_area.verticalScrollBar().maximum())
        )
        self.scroll_bottom_btn.hide()

        self._scroll_animation = None  # Keep reference to prevent GC

    def _smooth_scroll_to(self, target):
        """Animate the scrollbar to target value with an eased interpolation."""
        scrollbar = self.scroll_area.verticalScrollBar()
        if self._scroll_animation:
            self._scroll_animation.stop()
        self._scroll_animation = QPropertyAnimation(scrollbar, b"value")
        self._scroll_animation.setDuration(350)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._scroll_animation.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_scroll_buttons()

    def _position_scroll_buttons(self):
        margin = 14
        btn_size = 34
        gap = 6
        x = self.width() - margin - btn_size
        self.scroll_bottom_btn.move(x, self.height() - margin - btn_size)
        self.scroll_top_btn.move(x, self.height() - margin - btn_size * 2 - gap)

    # ── Scroll range / button visibility ──────────────────────────────────

    def _on_scroll_range_changed(self, _min, _max):
        """Update buttons when the scrollable range changes (content added/removed)."""
        scrollbar = self.scroll_area.verticalScrollBar()
        self._update_scroll_buttons(scrollbar.value(), _max)

    def _update_scroll_buttons(self, value, max_value):
        """Show/hide scroll buttons based on current scroll position."""
        # No scrollable content — hide both
        if max_value <= 20:
            self.scroll_top_btn.hide()
            self.scroll_bottom_btn.hide()
            return

        at_top = value <= 0
        at_bottom = value >= max_value - 20

        self.scroll_top_btn.setVisible(not at_top)
        self.scroll_bottom_btn.setVisible(not at_bottom)

        # Keep buttons visually on top of the scroll area content
        self.scroll_top_btn.raise_()
        self.scroll_bottom_btn.raise_()

    def _on_scroll_moved(self, value):
        """Handle when scrollbar value changes (both user and programmatic)."""
        scrollbar = self.scroll_area.verticalScrollBar()
        max_value = scrollbar.maximum()

        if value != max_value and value < max_value - 20:
            self.user_scrolled_up = True
        elif value >= max_value - 20:
            self.user_scrolled_up = False

        self._update_scroll_buttons(value, max_value)
