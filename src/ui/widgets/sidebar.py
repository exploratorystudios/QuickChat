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

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLineEdit, QListWidget, QListWidgetItem, QLabel, QGraphicsOpacityEffect)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
from PySide6.QtGui import QIcon
from src.services.chat_manager import chat_manager

class Sidebar(QWidget):
    chat_selected = Signal(int) # Emits chat_id
    new_chat_requested = Signal()
    chat_deleted = Signal(int) # Emits deleted chat_id
    collapse_state_changed = Signal(bool)  # Emits True when collapsed, False when expanded

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.min_width = 280
        self.collapsed_width = 60
        self.is_collapsed = False
        self.animation_group = None
        self.fade_animation_group = None
        self._fade_timer = None

        # Store effects to prevent garbage collection during animation
        self._element_effects = {}  # {element: QGraphicsOpacityEffect}
        self._animation_pool = []  # Keep all animations alive

        # Typing animation tracking
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self._on_typing_tick)
        self.typing_queue = {}  # {chat_id: {'full_text': str, 'displayed': int, 'item': QListWidgetItem}}
        self.typing_speed = 25  # milliseconds per character (40 chars/sec)

        self.setup_ui()
        self.load_chats()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header / New Chat
        self.header_layout = QHBoxLayout()
        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.setObjectName("PrimaryButton")
        self.new_chat_btn.clicked.connect(self.on_new_chat)
        self.header_layout.addWidget(self.new_chat_btn)

        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.on_import_chat)
        self.header_layout.addWidget(self.import_btn)

        layout.addLayout(self.header_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search chats...")
        self.search_input.textChanged.connect(self.filter_chats)
        layout.addWidget(self.search_input)

        # Chat List
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.on_chat_clicked)
        layout.addWidget(self.chat_list)

        # Set initial width
        self.setMinimumWidth(self.min_width)
        self.setMaximumWidth(self.min_width)


    def load_chats(self):
        self.chat_list.clear()
        chats = chat_manager.get_all_chats()
        for chat in chats:
            item = QListWidgetItem(chat.title)
            item.setData(Qt.UserRole, chat.id)
            self.chat_list.addItem(item)

    def update_chat_title(self, chat_id, new_title, animate=True):
        """
        Update the title of a specific chat in the list.

        Args:
            chat_id: The ID of the chat to update
            new_title: The new title text
            animate: If True, use smooth typing animation. If False, update immediately.
        """
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.UserRole) == chat_id:
                if animate and new_title:
                    # Queue this chat for typing animation
                    self.typing_queue[chat_id] = {
                        'full_text': new_title,
                        'displayed': 0,
                        'item': item
                    }
                    # Start the animation timer if not already running
                    if not self.typing_timer.isActive():
                        self.typing_timer.start(self.typing_speed)
                else:
                    # Immediate update
                    item.setText(new_title)
                    # Remove from typing queue if present
                    if chat_id in self.typing_queue:
                        del self.typing_queue[chat_id]
                break

    def _on_typing_tick(self):
        """Called by timer to advance typing animation for all queued chats."""
        completed_chats = []

        for chat_id, animation_data in self.typing_queue.items():
            full_text = animation_data['full_text']
            displayed = animation_data['displayed']
            item = animation_data['item']

            # Advance by 1 character
            if displayed < len(full_text):
                displayed += 1
                animation_data['displayed'] = displayed
                # Update item with partial text
                item.setText(full_text[:displayed])
            else:
                # Animation complete
                completed_chats.append(chat_id)

        # Remove completed animations from queue
        for chat_id in completed_chats:
            del self.typing_queue[chat_id]

        # Stop timer if no more animations
        if not self.typing_queue:
            self.typing_timer.stop()

    def on_new_chat(self):
        self.new_chat_requested.emit()

    def on_import_chat(self):
        # Get main window to check generation state
        main_window = self.window()
        if hasattr(main_window, 'is_any_generation_active') and main_window.is_any_generation_active():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Generation in Progress", "Cannot import chat while generating. Please wait...")
            return

        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Chat", "", "JSON (*.json)")
        if file_path:
            new_chat = chat_manager.import_chat(file_path)
            if new_chat:
                self.add_chat_to_list(new_chat)
                self.chat_selected.emit(new_chat.id)
                QMessageBox.information(self, "Success", "Chat imported successfully.")
            else:
                QMessageBox.warning(self, "Error", "Failed to import chat.")

    def on_chat_clicked(self, item):
        chat_id = item.data(Qt.UserRole)
        self.chat_selected.emit(chat_id)

    def contextMenuEvent(self, event):
        # Map the position to the chat_list widget's coordinate system
        list_pos = self.chat_list.mapFromGlobal(event.globalPos())
        item = self.chat_list.itemAt(list_pos)
        
        if item:
            from PySide6.QtWidgets import QMenu, QInputDialog
            menu = QMenu(self)
            rename_action = menu.addAction("Rename Chat")
            export_action = menu.addAction("Export Chat")
            delete_action = menu.addAction("Delete Chat")
            
            action = menu.exec(event.globalPos())
            
            if action:  # Check if an action was selected
                chat_id = item.data(Qt.UserRole)
                if action == rename_action:
                    new_title, ok = QInputDialog.getText(self, "Rename Chat", "New Title:", text=item.text())
                    if ok and new_title:
                        if chat_manager.rename_chat(chat_id, new_title):
                            item.setText(new_title)
                elif action == export_action:
                    self.handle_export(chat_id)
                elif action == delete_action:
                    self.handle_delete(chat_id, item)

    def handle_export(self, chat_id):
        import os
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, filter_selected = QFileDialog.getSaveFileName(self, "Export Chat", "", "Markdown (*.md);;JSON (*.json)")
        if file_path:
            # Determine format based on selected filter or file extension
            if filter_selected and "JSON" in filter_selected:
                fmt = 'json'
                # Ensure .json extension
                if not file_path.endswith('.json'):
                    file_path += '.json'
            else:
                fmt = 'markdown'
                # Ensure .md extension
                if not file_path.endswith('.md'):
                    file_path += '.md'

            content = chat_manager.export_chat(chat_id, fmt)
            with open(file_path, 'w') as f:
                f.write(content)
            QMessageBox.information(self, "Success", f"Chat exported successfully to {os.path.basename(file_path)}.")

    def handle_delete(self, chat_id, item):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Delete Chat", "Are you sure you want to delete this chat?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if chat_manager.delete_chat(chat_id):
                self.chat_list.takeItem(self.chat_list.row(item))
                self.chat_list.clearSelection()
                # Emit signal to notify main window to clear chat area
                self.chat_deleted.emit(chat_id)

    def add_chat_to_list(self, chat):
        """Add a single chat to the top of the list."""
        item = QListWidgetItem(chat.title)
        item.setData(Qt.UserRole, chat.id)
        self.chat_list.insertItem(0, item)
        self.chat_list.setCurrentItem(item)

    def filter_chats(self, text):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())


    def toggle_collapse(self):
        """Toggle sidebar collapse/expand state with smooth animation."""
        if self.is_collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self):
        """Collapse the sidebar with smooth animation."""
        if self.is_collapsed:
            return

        self.is_collapsed = True

        # Fade out elements while animating width
        self._animate_fade_out()
        self._animate_width(self.min_width, self.collapsed_width)

        self.collapse_state_changed.emit(True)

    def expand(self):
        """Expand the sidebar with smooth animation."""
        if not self.is_collapsed:
            return

        self.is_collapsed = False

        # Prevent widgets from being visible during width animation
        # Set max size to 0 so layout doesn't render them
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]
        for element in elements:
            element.setMaximumHeight(0)

        # Animate width first
        self._animate_width(self.collapsed_width, self.min_width)

        # Start fade in after width animation completes
        self._start_fade_in_timer()

        self.collapse_state_changed.emit(False)

    def _animate_width(self, start_width, end_width):
        """Animate sidebar width smoothly using geometry."""
        if self.animation_group:
            self.animation_group.stop()

        self.animation_group = QParallelAnimationGroup()

        # Animate minimum width
        min_width_anim = QPropertyAnimation(self, b"minimumWidth")
        min_width_anim.setDuration(300)
        min_width_anim.setStartValue(start_width)
        min_width_anim.setEndValue(end_width)
        min_width_anim.setEasingCurve(QEasingCurve.InOutCubic)

        # Animate maximum width
        max_width_anim = QPropertyAnimation(self, b"maximumWidth")
        max_width_anim.setDuration(300)
        max_width_anim.setStartValue(start_width)
        max_width_anim.setEndValue(end_width)
        max_width_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.animation_group.addAnimation(min_width_anim)
        self.animation_group.addAnimation(max_width_anim)
        self.animation_group.start()

    def _animate_fade_out(self):
        """Fade out UI elements smoothly."""
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]

        # Stop any existing fade animation ONLY if it's running
        if self.fade_animation_group and self.fade_animation_group.state() == QAbstractAnimation.Running:
            self.fade_animation_group.stop()

        # Create new animation group
        self.fade_animation_group = QParallelAnimationGroup()

        for element in elements:
            # Create fresh effect for this fade out
            effect = QGraphicsOpacityEffect()
            element.setGraphicsEffect(effect)
            effect.setOpacity(1.0)

            # Store in pool to keep alive
            self._element_effects[element] = effect

            fade_anim = QPropertyAnimation(effect, b"opacity")
            fade_anim.setDuration(300)  # Match width animation duration for synchronized fade
            fade_anim.setStartValue(1.0)
            fade_anim.setEndValue(0.0)
            fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

            self.fade_animation_group.addAnimation(fade_anim)

        # Keep animation group alive to prevent garbage collection of effects
        self._animation_pool.append(self.fade_animation_group)
        # Cleanup old animation groups to prevent memory leak (keep last 10)
        if len(self._animation_pool) > 10:
            self._animation_pool.pop(0)

        self.fade_animation_group.start()

    def _hide_fade_elements(self):
        """Hide elements after fade out completes."""
        # Elements are now invisible (opacity 0) but still exist
        # No need to hide or disable - they're invisible and won't respond to clicks
        pass

    def _start_fade_in_timer(self):
        """Start fade in after width animation completes (300ms)."""
        # Use a timer to start fade in when width animation finishes
        fade_start_timer = QTimer()
        fade_start_timer.setSingleShot(True)
        fade_start_timer.timeout.connect(self._animate_fade_in)
        fade_start_timer.start(300)  # Match width animation duration
        # Store timer reference to prevent garbage collection
        self._fade_timer = fade_start_timer

    def _animate_fade_in(self):
        """Fade in UI elements smoothly."""
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]

        # Stop any existing fade animation ONLY if it's running
        if self.fade_animation_group and self.fade_animation_group.state() == QAbstractAnimation.Running:
            self.fade_animation_group.stop()

        self.fade_animation_group = QParallelAnimationGroup()

        # FIRST: Set up all effects and properties BEFORE showing or starting animation
        for element in elements:
            # Restore max height that was set to 0 during expand
            element.setMaximumHeight(16777215)  # Qt's default max height

            # Create fresh effect for this fade in
            effect = QGraphicsOpacityEffect()
            element.setGraphicsEffect(effect)
            effect.setOpacity(0.0)  # Start invisible

            # Store in pool to keep alive
            self._element_effects[element] = effect

            fade_anim = QPropertyAnimation(effect, b"opacity")
            fade_anim.setDuration(200)
            fade_anim.setStartValue(0.0)
            fade_anim.setEndValue(1.0)
            fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

            self.fade_animation_group.addAnimation(fade_anim)

        # ONLY NOW show the widgets (after effects are applied and opacity set to 0)
        for element in elements:
            element.show()

        # Keep animation group alive to prevent garbage collection of effects
        self._animation_pool.append(self.fade_animation_group)
        # Cleanup old animation groups to prevent memory leak (keep last 10)
        if len(self._animation_pool) > 10:
            self._animation_pool.pop(0)

        # THEN: Start the animation
        self.fade_animation_group.start()
