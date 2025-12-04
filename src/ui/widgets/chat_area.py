from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFrame, QApplication
from PySide6.QtCore import Qt, Signal, QTimer
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

        # Connect scrollbar changes to detect user scrolling
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.valueChanged.connect(self._on_scroll_moved)

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

    def _on_scroll_moved(self, value):
        """Handle when scrollbar value changes (both user and programmatic)."""
        scrollbar = self.scroll_area.verticalScrollBar()
        max_value = scrollbar.maximum()

        # Only update if we're not already at max (programmatic scroll just happened)
        # This prevents us from immediately marking as scrolled_up after we just scrolled
        # Use smaller tolerance (20px) to detect scrolling even with small content
        if value != max_value and value < max_value - 20:
            # User has scrolled away from bottom
            self.user_scrolled_up = True
        elif value >= max_value - 20:
            # User is at or near bottom
            self.user_scrolled_up = False
