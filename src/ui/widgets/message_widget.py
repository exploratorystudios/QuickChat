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

import mistune
import re
import json
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser, QGroupBox, QToolButton, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QApplication, QHBoxLayout, QScrollArea, QFrame
from PySide6.QtGui import QFont, QColor, QPixmap
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property, QUrl, QTimer
from src.services.latex_processor import LaTeXProcessor

class CodeCopyTextBrowser(QTextBrowser):
    """Custom QTextBrowser that handles copy code button clicks."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.code_blocks = []  # Store code block content
        self.message_widget = None  # Reference to parent MessageWidget
        self.setOpenExternalLinks(False)  # Disable automatic link opening

    def mousePressEvent(self, event):
        """Handle mouse clicks to detect copy button clicks."""
        # Get the anchor (link) at the click position
        anchor = self.anchorAt(event.pos())

        if anchor.startswith("copy-code://"):
            # Extract the code block index
            try:
                index = int(anchor.replace("copy-code://", ""))
                if 0 <= index < len(self.code_blocks):
                    clipboard = QApplication.clipboard()
                    clipboard.setText(self.code_blocks[index])

                    # Show feedback if we have reference to message widget
                    if self.message_widget:
                        self.message_widget.show_code_copied_feedback()
            except (ValueError, IndexError):
                pass
            # Don't propagate the event to prevent URL loading
            event.accept()
            return

        # For other clicks, use default behavior
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to prevent navigation on copy-code links."""
        anchor = self.anchorAt(event.pos())

        if anchor.startswith("copy-code://"):
            # Completely stop the event from propagating
            event.accept()
            return

        # For other releases, use default behavior
        super().mouseReleaseEvent(event)

    def setSource(self, url):
        """Override to prevent any URL navigation for copy-code links."""
        url_str = url.toString()
        if url_str.startswith("copy-code://"):
            # Completely ignore these - already handled in mousePressEvent
            return
        elif url_str.startswith("http://") or url_str.startswith("https://"):
            # Open external links
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(url)
        else:
            # Let parent handle other cases
            super().setSource(url)

    def contextMenuEvent(self, event):
        """Override context menu to show custom message options instead of text selection."""
        # Pass the context menu event to the parent MessageWidget
        if self.message_widget:
            self.message_widget.contextMenuEvent(event)
        else:
            # Fallback to default if no parent reference
            super().contextMenuEvent(event)

class MessageWidget(QWidget):
    fork_requested = Signal(int) # Emits message_id

    def __init__(self, role, content, thinking_content=None, message_id=None, images=None):
        super().__init__()
        self.role = role
        self.content = content
        self.thinking_content = thinking_content or ""
        self.message_id = message_id
        self.images = images or []  # List of image paths or metadata
        self.is_streaming = False
        self.thinking_animation = None
        self.code_copied_label = None  # For showing "Code copied!" feedback
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setAlignment(Qt.AlignTop)

        # Create horizontal layout for message and copy button
        message_row_layout = QVBoxLayout()
        message_row_layout.setSpacing(4)

        # Thinking section for assistant messages
        if self.role == "assistant":
            self.thinking_browser = QTextBrowser()
            self.thinking_browser.setOpenExternalLinks(True)
            self.thinking_browser.setReadOnly(True)
            self.thinking_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.thinking_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.thinking_browser.setVisible(False)

            self.show_thinking_btn = QToolButton()
            self.show_thinking_btn.setText("+ Show Thinking")
            self.show_thinking_btn.clicked.connect(self.toggle_thinking)
            self.show_thinking_btn.setVisible(False)  # Hide initially
            self.show_thinking_btn.setMaximumWidth(150)

            # Style the thinking button
            self.style_thinking_button()

            layout.addWidget(self.show_thinking_btn, alignment=Qt.AlignLeft)

            layout.addWidget(self.thinking_browser, alignment=Qt.AlignLeft)

        # Bubble Container
        self.bubble = CodeCopyTextBrowser()
        self.bubble.message_widget = self  # Set reference to parent
        self.bubble.setReadOnly(True)
        self.bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.bubble.setMaximumWidth(600)  # Max width for better messenger-style bubbles
        self.bubble.setSizePolicy(self.bubble.sizePolicy().horizontalPolicy(), self.bubble.sizePolicy().verticalPolicy())

        # Add subtle shadow effect for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.bubble.setGraphicsEffect(shadow)

        # Apply initial styling
        self.apply_theme_styling()

        # Set font with proper point size
        default_font = QFont()
        default_font.setFamily("Segoe UI")
        default_font.setPointSize(10)
        self.bubble.setFont(default_font)
        if self.role == "assistant":
            self.thinking_browser.setFont(default_font)

        # Setup content for display
        self.standard_content = self.content
        self.thinking_initial = self.thinking_content  # Save initial for later

        html_content = mistune.html(self.standard_content)
        enhanced_html = self.enhance_html_with_copy_buttons(html_content)

        # Process LaTeX expressions
        from src.services.settings_manager import settings_manager
        theme = settings_manager.get("theme", "dark")
        enhanced_html = LaTeXProcessor.process_html(enhanced_html, theme=theme)

        self.bubble.setHtml(enhanced_html)

        if self.role == "assistant" and self.thinking_content.strip():
            # Apply theme to thinking_browser and show button
            self.apply_theme_to_thinking()
            self.show_thinking_btn.setVisible(True)

        # Adjust height
        self.adjust_heights()

        # Create copy button
        from PySide6.QtWidgets import QHBoxLayout
        self.copy_button = QToolButton()
        self.copy_button.setText("Copy")
        self.copy_button.clicked.connect(self.copy_message)
        self.copy_button.setMaximumWidth(60)
        self.copy_button.setMaximumHeight(24)
        self.style_copy_button()

        # Create horizontal layout for bubble and copy button
        bubble_container = QHBoxLayout()
        bubble_container.setSpacing(8)
        bubble_container.setContentsMargins(0, 0, 0, 0)

        # Align bubble and copy button based on role
        if self.role == "user":
            bubble_container.addStretch()
            bubble_container.addWidget(self.bubble)
            bubble_container.addWidget(self.copy_button, alignment=Qt.AlignTop)
            layout.addLayout(bubble_container)
        else:
            bubble_container.addWidget(self.copy_button, alignment=Qt.AlignTop)
            bubble_container.addWidget(self.bubble)
            bubble_container.addStretch()
            layout.addLayout(bubble_container)

        # Add image thumbnails if present
        if self.images:
            self.add_image_thumbnails(layout)

    def add_image_thumbnails(self, layout):
        """Add image thumbnails below the message bubble."""
        from config.settings import DATA_DIR

        # Create a horizontal scroll area for images
        images_container = QWidget()
        images_layout = QHBoxLayout(images_container)
        images_layout.setContentsMargins(0, 8, 0, 0)
        images_layout.setSpacing(8)

        # Alignment based on role
        if self.role == "user":
            images_layout.addStretch()

        # Add thumbnail for each image
        for image_data in self.images:
            try:
                # Parse image data (could be string path or JSON)
                if isinstance(image_data, str):
                    image_info = json.loads(image_data) if image_data.startswith('{') else {"path": image_data}
                else:
                    image_info = image_data

                image_path = image_info.get("path", "")

                # Resolve full path if it's relative
                if image_path and not os.path.isabs(image_path):
                    full_path = os.path.join(DATA_DIR, image_path)
                else:
                    full_path = image_path

                # Create thumbnail
                if os.path.exists(full_path):
                    thumbnail = self.create_image_thumbnail(full_path)
                    if thumbnail:
                        images_layout.addWidget(thumbnail)
            except Exception as e:
                print(f"[MessageWidget] Error loading image: {e}")

        if self.role == "assistant":
            images_layout.addStretch()

        layout.addWidget(images_container)

    def create_image_thumbnail(self, image_path):
        """Create a thumbnail widget for an image."""
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                return None

            # Create thumbnail (150x150 max)
            thumbnail_size = 150
            scaled_pixmap = pixmap.scaledToWidth(thumbnail_size, Qt.SmoothTransformation)
            if scaled_pixmap.height() > thumbnail_size:
                scaled_pixmap = pixmap.scaledToHeight(thumbnail_size, Qt.SmoothTransformation)

            # Create label with pixmap
            thumbnail_label = QLabel()
            thumbnail_label.setPixmap(scaled_pixmap)
            thumbnail_label.setFixedSize(thumbnail_size, thumbnail_size)

            # Style with rounded corners and border
            from src.services.settings_manager import settings_manager
            from config.theme import DARK_THEME, LIGHT_THEME

            current_theme = settings_manager.get("theme", "dark")
            colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

            thumbnail_label.setStyleSheet(f"""
                QLabel {{
                    border: 2px solid {colors['border']};
                    border-radius: 8px;
                    background-color: {colors['surface']};
                }}
            """)

            return thumbnail_label
        except Exception as e:
            print(f"[MessageWidget] Error creating thumbnail: {e}")
            return None

    def apply_theme_styling(self):
        """Apply current theme colors to the message bubble."""
        from src.services.settings_manager import settings_manager
        from config.theme import DARK_THEME, LIGHT_THEME

        current_theme = settings_manager.get("theme", "dark")
        colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

        # Styling based on role with enhanced rounded corners
        if self.role == "user":
            bg_color = colors['bubble_user']
            text_color = colors['text_on_primary']
            border_radius = "20px 20px 20px 20px"  # Fully rounded
        else:
            bg_color = colors['bubble_assistant']
            text_color = colors.get('bubble_assistant_text', colors['text_primary'])
            border_radius = "20px 20px 20px 20px"  # Fully rounded

        style = f"""
            QTextBrowser {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: {border_radius};
                padding: 14px 18px;
                border: none;
                font-size: 14px;
                line-height: 1.6;
                font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            }}
        """
        self.bubble.setStyleSheet(style)

    def apply_theme_to_thinking(self):
        """Apply theme to thinking browser."""
        self.thinking_browser.setStyleSheet(self.bubble.styleSheet())

    def enhance_html_with_copy_buttons(self, html_content):
        """Add copy buttons to code blocks in HTML."""
        self.bubble.code_blocks = []  # Reset code blocks

        # Find all code blocks and extract their content
        def replace_code_block(match):
            code_content = match.group(2)
            # Decode HTML entities in code
            code_text = code_content.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')

            # Store the code block
            index = len(self.bubble.code_blocks)
            self.bubble.code_blocks.append(code_text)

            # Get theme colors for copy button
            from src.services.settings_manager import settings_manager
            from config.theme import DARK_THEME, LIGHT_THEME
            current_theme = settings_manager.get("theme", "dark")
            colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

            # Create enhanced code block with copy button
            return f'''<div style="position: relative; margin: 10px 0;">
                <div style="background-color: {colors['surface']}; border-radius: 8px; padding: 12px; overflow-x: auto;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: {colors['text_secondary']}; font-size: 12px;">{match.group(1) if match.group(1) else 'code'}</span>
                        <a href="copy-code://{index}" style="color: {colors['primary']}; text-decoration: none; font-size: 12px; padding: 4px 8px; background-color: {colors['background']}; border-radius: 4px;">Copy</a>
                    </div>
                    <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word; color: {colors['text_primary']}; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px;"><code>{code_content}</code></pre>
                </div>
            </div>'''

        # Pattern to match code blocks with optional language identifier
        # Matches: <pre><code class="language-xxx">...</code></pre> or <pre><code>...</code></pre>
        pattern = r'<pre><code(?:\s+class="language-([^"]*)")?>(.*?)</code></pre>'
        enhanced_html = re.sub(pattern, replace_code_block, html_content, flags=re.DOTALL)

        return enhanced_html

    def style_thinking_button(self):
        """Style the thinking toggle button."""
        from src.services.settings_manager import settings_manager
        from config.theme import DARK_THEME, LIGHT_THEME

        current_theme = settings_manager.get("theme", "dark")
        colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

        button_style = f"""
            QToolButton {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border: 1px solid {colors['border']};
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
                margin: 4px 0px;
            }}
            QToolButton:hover {{
                background-color: {colors['surface_light']};
                color: {colors['text_primary']};
                border-color: {colors['primary']};
            }}
            QToolButton:pressed {{
                background-color: {colors['border']};
            }}
        """
        self.show_thinking_btn.setStyleSheet(button_style)

    def style_copy_button(self):
        """Style the copy button."""
        from src.services.settings_manager import settings_manager
        from config.theme import DARK_THEME, LIGHT_THEME

        current_theme = settings_manager.get("theme", "dark")
        colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

        button_style = f"""
            QToolButton {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: {colors['surface_light']};
                color: {colors['primary']};
                border-color: {colors['primary']};
            }}
            QToolButton:pressed {{
                background-color: {colors['border']};
            }}
        """
        self.copy_button.setStyleSheet(button_style)

    def copy_message(self):
        """Copy message content to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.content)

        # Show feedback
        original_text = self.copy_button.text()
        self.copy_button.setText("Copied!")

        # Reset after 1.5 seconds
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))

    def show_code_copied_feedback(self):
        """Show temporary 'Code copied!' message."""
        # Create a temporary label if it doesn't exist
        if not self.code_copied_label:
            from src.services.settings_manager import settings_manager
            from config.theme import DARK_THEME, LIGHT_THEME

            current_theme = settings_manager.get("theme", "dark")
            colors = DARK_THEME if current_theme == "dark" else LIGHT_THEME

            self.code_copied_label = QLabel("Code copied!")
            self.code_copied_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {colors['success']};
                    color: {colors['text_on_primary']};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)
            self.code_copied_label.setAlignment(Qt.AlignCenter)
            self.code_copied_label.setMaximumWidth(120)
            self.code_copied_label.hide()

            # Add to layout
            main_layout = self.layout()
            if self.role == "user":
                main_layout.addWidget(self.code_copied_label, alignment=Qt.AlignRight)
            else:
                main_layout.addWidget(self.code_copied_label, alignment=Qt.AlignLeft)

        # Show the label
        self.code_copied_label.show()

        # Hide after 1.5 seconds
        QTimer.singleShot(1500, self.code_copied_label.hide)


    def update_thinking(self, thinking):
        """Update the thinking content."""
        try:
            self.thinking_content = thinking.strip()
            if self.role == "assistant":
                self.show_thinking_btn.setVisible(bool(self.thinking_content))
                # Start animation when thinking starts streaming
                if self.thinking_content and not self.is_streaming:
                    self.start_thinking_animation()
                if self.thinking_browser.isVisible():
                    html_thinking = mistune.html(self.thinking_content)
                    from src.services.settings_manager import settings_manager
                    theme = settings_manager.get("theme", "dark")
                    html_thinking = LaTeXProcessor.process_html(html_thinking, theme=theme)
                    self.thinking_browser.setHtml(html_thinking)
                    self.adjust_heights()
        except RuntimeError:
            # Widget has been deleted, silently ignore
            pass

    def update_response(self, response):
        """Update the response content."""
        try:
            self.content = response
            self.standard_content = self.content
            html_content = mistune.html(self.standard_content)
            enhanced_html = self.enhance_html_with_copy_buttons(html_content)

            # Process LaTeX expressions
            from src.services.settings_manager import settings_manager
            theme = settings_manager.get("theme", "dark")
            enhanced_html = LaTeXProcessor.process_html(enhanced_html, theme=theme)

            # Check if widget still exists before updating
            if not self.bubble or not hasattr(self.bubble, 'setHtml'):
                return

            self.bubble.setHtml(enhanced_html)
            self.adjust_heights()
        except RuntimeError:
            # Widget has been deleted, silently ignore
            pass

    def finalize_response(self):
        """Process LaTeX in the final response after streaming is complete."""
        try:
            html_content = mistune.html(self.standard_content)
            enhanced_html = self.enhance_html_with_copy_buttons(html_content)

            # Now process LaTeX on the complete content
            from src.services.settings_manager import settings_manager
            theme = settings_manager.get("theme", "dark")
            enhanced_html = LaTeXProcessor.process_html(enhanced_html, theme=theme)

            # Check if widget still exists before updating
            if not self.bubble or not hasattr(self.bubble, 'setHtml'):
                return

            self.bubble.setHtml(enhanced_html)
            self.adjust_heights()
        except RuntimeError:
            # Widget has been deleted, silently ignore
            pass

    def toggle_thinking(self):
        if self.thinking_browser.isVisible():
            self.thinking_browser.setVisible(False)
            self.show_thinking_btn.setText("+ Show Thinking")
        else:
            self.thinking_browser.setVisible(True)
            self.show_thinking_btn.setText("- Hide Thinking")
            # Update content and adjust size
            html_thinking = mistune.html(self.thinking_content)
            from src.services.settings_manager import settings_manager
            theme = settings_manager.get("theme", "dark")
            html_thinking = LaTeXProcessor.process_html(html_thinking, theme=theme)
            self.thinking_browser.setHtml(html_thinking)
            self.adjust_heights()

    def adjust_heights(self):
        # Size bubble to content with proper width calculation
        max_width = 600
        min_width = 120

        # First, let document calculate its ideal width without constraints
        self.bubble.document().setTextWidth(-1)  # -1 means no wrapping
        ideal_width = self.bubble.document().idealWidth()

        # Determine actual width based on content, respecting min/max
        if ideal_width + 40 > max_width:
            # Content is wider than max, use max width and wrap
            actual_width = max_width
        else:
            # Content fits, use ideal width but respect minimum
            actual_width = max(min_width, ideal_width + 40)

        # Now set the text width for height calculation
        self.bubble.document().setTextWidth(actual_width - 40)  # Subtract padding
        doc_height = self.bubble.document().size().height()

        # Set the final size
        self.bubble.setFixedSize(int(actual_width), int(doc_height + 30))

        # Adjust thinking browser if visible
        if self.role == "assistant" and self.thinking_browser.isVisible():
            # Same logic for thinking browser
            self.thinking_browser.document().setTextWidth(-1)
            think_ideal_width = self.thinking_browser.document().idealWidth()

            if think_ideal_width + 40 > max_width:
                actual_think_width = max_width
            else:
                actual_think_width = max(min_width, think_ideal_width + 40)

            self.thinking_browser.document().setTextWidth(actual_think_width - 40)
            think_height = self.thinking_browser.document().size().height()
            self.thinking_browser.setFixedSize(int(actual_think_width), int(think_height + 30))

    def start_thinking_animation(self):
        """Start pulsing animation on thinking button."""
        if self.role != "assistant" or self.is_streaming:
            return

        self.is_streaming = True

        # Create opacity effect if it doesn't exist
        if not hasattr(self, 'thinking_opacity_effect'):
            self.thinking_opacity_effect = QGraphicsOpacityEffect()
            self.show_thinking_btn.setGraphicsEffect(self.thinking_opacity_effect)

        # Create pulsing animation
        self.thinking_animation = QPropertyAnimation(self.thinking_opacity_effect, b"opacity")
        self.thinking_animation.setDuration(1000)  # 1 second
        self.thinking_animation.setStartValue(0.4)
        self.thinking_animation.setEndValue(1.0)
        self.thinking_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.thinking_animation.setLoopCount(-1)  # Loop forever
        self.thinking_animation.start()

    def stop_thinking_animation(self):
        """Stop the thinking button animation."""
        if self.thinking_animation:
            self.thinking_animation.stop()
            self.is_streaming = False
            # Reset opacity to full
            if hasattr(self, 'thinking_opacity_effect'):
                self.thinking_opacity_effect.setOpacity(1.0)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu, QApplication

        menu = QMenu(self)

        # Copy message action
        copy_action = menu.addAction("Copy Message")

        # Fork action (only if message has an ID)
        fork_action = None
        if self.message_id:
            fork_action = menu.addAction("Fork Chat from Here")

        action = menu.exec(event.globalPos())

        if action == copy_action:
            # Copy the message content to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(self.content)
        elif fork_action and action == fork_action:
            self.fork_requested.emit(self.message_id)
