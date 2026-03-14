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

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt


class ContextBar(QWidget):
    """
    A thin status bar displayed between the header and the chat area.
    Shows estimated token usage vs. the configured context window, with a
    colour-coded progress bar and the model's hard maximum as reference.
    """

    def __init__(self):
        super().__init__()
        self.setObjectName("ContextBar")
        self.setFixedHeight(32)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # Left: used / configured token count
        self.token_label = QLabel("No chat selected")
        self.token_label.setObjectName("ContextBarLabel")
        layout.addWidget(self.token_label)

        # Centre: progress bar (thin, colour-coded)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000)   # 1000 steps for fine granularity
        self.progress_bar.setValue(0)
        self.progress_bar.setObjectName("ContextProgressBar")
        self._apply_bar_color("#3E4042")       # neutral until first update
        layout.addWidget(self.progress_bar, 1)

        # Right: model max context
        self.max_label = QLabel("")
        self.max_label.setObjectName("ContextBarLabel")
        self.max_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.max_label)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _apply_bar_color(self, chunk_color: str):
        """Set the progress bar stylesheet with the given chunk colour."""
        self.progress_bar.setStyleSheet(f"""
            QProgressBar#ContextProgressBar {{
                background-color: rgba(128, 128, 128, 50);
                border: none;
                border-radius: 3px;
                max-height: 6px;
                min-height: 6px;
            }}
            QProgressBar#ContextProgressBar::chunk {{
                background-color: {chunk_color};
                border-radius: 3px;
            }}
        """)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_display(self, used_tokens: int, ctx_size: int, model_max):
        """
        Refresh the bar with current usage data.

        Args:
            used_tokens: Estimated token count for the current conversation.
            ctx_size:    Configured context window size (from settings).
            model_max:   Model's hard maximum context (int) or None if unknown.
        """
        # Effective context is the smaller of what's configured and what the
        # model actually supports (model_max may be None if not yet fetched).
        if model_max is not None:
            effective_ctx = min(ctx_size, model_max)
            capped = ctx_size > model_max
        else:
            effective_ctx = ctx_size
            capped = False

        # Token count label
        if capped:
            self.token_label.setText(
                f"~{used_tokens:,} / {effective_ctx:,} tokens  (ctx capped at model max)"
            )
        else:
            self.token_label.setText(f"~{used_tokens:,} / {effective_ctx:,} tokens")

        # Model max label
        if model_max is not None:
            self.max_label.setText(f"Model max: {model_max:,}")
        else:
            self.max_label.setText("Model max: —")

        # Progress bar value and colour
        pct = min(1.0, used_tokens / effective_ctx) if effective_ctx > 0 else 0.0
        self.progress_bar.setValue(int(pct * 1000))

        if pct < 0.60:
            color = "#31A24C"   # green  — plenty of headroom
        elif pct < 0.80:
            color = "#F59E0B"   # amber  — getting full
        elif pct < 0.95:
            color = "#F97316"   # orange — nearly full
        else:
            color = "#FA383E"   # red    — at/over limit

        self._apply_bar_color(color)

    def clear(self):
        """Reset to the empty / no-chat-selected state."""
        self.token_label.setText("No chat selected")
        self.max_label.setText("")
        self.progress_bar.setValue(0)
        self._apply_bar_color("#3E4042")
