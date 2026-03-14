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
                               QLineEdit, QListWidget, QListWidgetItem, QLabel,
                               QGraphicsOpacityEffect, QStyledItemDelegate, QStyle)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
from PySide6.QtGui import QIcon, QColor, QBrush, QFont, QPainter
from src.services.chat_manager import chat_manager


class ChatItemDelegate(QStyledItemDelegate):
    """Custom delegate that paints chat list items, bypassing stylesheet overrides."""

    def paint(self, painter, option, index):
        from src.services.settings_manager import settings_manager
        from config.theme import DARK_THEME, LIGHT_THEME
        colors = DARK_THEME if settings_manager.get("theme", "dark") == "dark" else LIGHT_THEME

        is_pinned  = bool(index.data(Qt.UserRole + 1))
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered  = bool(option.state & QStyle.State_MouseOver)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # ── Background ────────────────────────────────────────────────────────
        rect = option.rect.adjusted(2, 2, -2, -2)
        if is_selected:
            bg = QColor(colors['surface_light'])
        elif is_hovered and is_pinned:
            # Slightly brighter tint on hover for pinned
            bg = QColor(59, 130, 246, 70)
        elif is_hovered:
            bg = QColor(colors['surface'])
        elif is_pinned:
            bg = QColor(59, 130, 246, 45)
        else:
            bg = QColor(0, 0, 0, 0)

        painter.setBrush(bg)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # ── Text ──────────────────────────────────────────────────────────────
        text = index.data(Qt.DisplayRole) or ""
        text_color = QColor(147, 197, 253, 230) if is_pinned else QColor(colors['text_primary'])
        painter.setPen(text_color)

        font = painter.font()
        font.setBold(is_pinned)
        painter.setFont(font)

        text_rect = option.rect.adjusted(12, 0, -12, 0)
        elided = painter.fontMetrics().elidedText(text, Qt.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        return QSize(hint.width(), 38)

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

        # Typing animation tracking (keyed by chat_id, not item reference)
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self._on_typing_tick)
        self.typing_queue = {}  # {chat_id: {'full_text': str, 'displayed': int}}
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
        self.chat_list.setItemDelegate(ChatItemDelegate(self.chat_list))
        self.chat_list.itemClicked.connect(self.on_chat_clicked)
        layout.addWidget(self.chat_list)

        # Set initial width
        self.setMinimumWidth(self.min_width)
        self.setMaximumWidth(self.min_width)

    # ── Helpers ───────────────────────────────────────────────────────────────

    # _style_item is intentionally absent — ChatItemDelegate reads UserRole+1
    # and handles all visual styling (background, text color, bold) directly.

    def _pinned_count(self):
        """Count pinned items currently at the top of the list."""
        count = 0
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.UserRole + 1):  # is_pinned stored in UserRole+1
                count += 1
            else:
                break
        return count

    def _is_item_pinned(self, item):
        return bool(item.data(Qt.UserRole + 1))

    # ── Chat list management ──────────────────────────────────────────────────

    def load_chats(self):
        self.chat_list.clear()
        chats = chat_manager.get_all_chats()
        for chat in chats:
            self._append_item(chat)

    def _append_item(self, chat):
        """Append a chat item to the end of the list."""
        is_pinned = getattr(chat, 'is_pinned', False) or False
        item = QListWidgetItem(chat.title)
        item.setData(Qt.UserRole, chat.id)
        item.setData(Qt.UserRole + 1, is_pinned)
        self.chat_list.addItem(item)
        return item

    def add_chat_to_list(self, chat):
        """Add a single chat to the top of the unpinned section."""
        is_pinned = getattr(chat, 'is_pinned', False) or False
        item = QListWidgetItem(chat.title)
        item.setData(Qt.UserRole, chat.id)
        item.setData(Qt.UserRole + 1, is_pinned)
        pinned_count = self._pinned_count()
        self.chat_list.insertItem(pinned_count, item)
        self.chat_list.setCurrentItem(item)
        return item

    def bump_chat_to_top(self, chat_id):
        """Move a chat to the top of the unpinned section when it gets a new message."""
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.UserRole) == chat_id:
                # Don't move pinned chats
                if self._is_item_pinned(item):
                    return
                # Already at the top of unpinned
                if i == self._pinned_count():
                    return
                was_selected = (self.chat_list.currentItem() == item)
                self.chat_list.takeItem(i)
                pinned_count = self._pinned_count()
                self.chat_list.insertItem(pinned_count, item)
                if was_selected:
                    self.chat_list.setCurrentItem(item)
                return

    def update_chat_title(self, chat_id, new_title, animate=True):
        """Update the title of a specific chat in the list."""
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            if item.data(Qt.UserRole) == chat_id:
                if animate and new_title:
                    self.typing_queue[chat_id] = {
                        'full_text': new_title,
                        'displayed': 0,
                    }
                    if not self.typing_timer.isActive():
                        self.typing_timer.start(self.typing_speed)
                else:
                    item.setText(new_title)
                    if chat_id in self.typing_queue:
                        del self.typing_queue[chat_id]
                break

    def _on_typing_tick(self):
        """Called by timer to advance typing animation for all queued chats."""
        completed_chats = []

        for chat_id, animation_data in self.typing_queue.items():
            full_text = animation_data['full_text']
            displayed = animation_data['displayed']

            if displayed < len(full_text):
                displayed += 1
                animation_data['displayed'] = displayed
                partial = full_text[:displayed]
                # Look up item by chat_id each tick (item may have moved)
                for i in range(self.chat_list.count()):
                    item = self.chat_list.item(i)
                    if item.data(Qt.UserRole) == chat_id:
                        item.setText(partial)
                        break
            else:
                completed_chats.append(chat_id)

        for chat_id in completed_chats:
            del self.typing_queue[chat_id]

        if not self.typing_queue:
            self.typing_timer.stop()

    # ── Slot / event handlers ─────────────────────────────────────────────────

    def on_new_chat(self):
        self.new_chat_requested.emit()

    def on_import_chat(self):
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
        list_pos = self.chat_list.mapFromGlobal(event.globalPos())
        item = self.chat_list.itemAt(list_pos)

        if item:
            from PySide6.QtWidgets import QMenu, QInputDialog
            menu = QMenu(self)
            rename_action = menu.addAction("Rename Chat")

            is_pinned = self._is_item_pinned(item)
            pin_action = menu.addAction("Unpin Chat" if is_pinned else "Pin Chat")

            export_action = menu.addAction("Export Chat")
            delete_action = menu.addAction("Delete Chat")

            action = menu.exec(event.globalPos())

            if action:
                chat_id = item.data(Qt.UserRole)
                if action == rename_action:
                    new_title, ok = QInputDialog.getText(self, "Rename Chat", "New Title:", text=item.text())
                    if ok and new_title:
                        if chat_manager.rename_chat(chat_id, new_title):
                            item.setText(new_title)
                elif action == pin_action:
                    self._toggle_pin(item, chat_id, not is_pinned)
                elif action == export_action:
                    self.handle_export(chat_id)
                elif action == delete_action:
                    self.handle_delete(chat_id, item)

    def _toggle_pin(self, item, chat_id, new_is_pinned):
        """Pin or unpin a chat and re-sort the list."""
        chat_manager.set_chat_pinned(chat_id, new_is_pinned)

        # Remember selection
        current_item = self.chat_list.currentItem()
        current_chat_id = current_item.data(Qt.UserRole) if current_item else None

        self.load_chats()

        # Restore selection
        if current_chat_id is not None:
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.UserRole) == current_chat_id:
                    self.chat_list.setCurrentItem(item)
                    break

    def handle_export(self, chat_id):
        import os
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Chat", "", "Chat Export (*)")
        if file_path:
            base = file_path
            for ext in ('.md', '.json'):
                if base.endswith(ext):
                    base = base[:-len(ext)]
                    break

            md_path   = base + '.md'
            json_path = base + '.json'

            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(chat_manager.export_chat(chat_id, 'markdown'))
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(chat_manager.export_chat(chat_id, 'json'))

            name = os.path.basename(base)
            QMessageBox.information(self, "Success",
                f"Chat exported as:\n  {name}.md\n  {name}.json")

    def handle_delete(self, chat_id, item):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(self, "Delete Chat", "Are you sure you want to delete this chat?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if chat_manager.delete_chat(chat_id):
                self.chat_list.takeItem(self.chat_list.row(item))
                self.chat_list.clearSelection()
                self.chat_deleted.emit(chat_id)

    def filter_chats(self, text):
        for i in range(self.chat_list.count()):
            item = self.chat_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    # ── Collapse / expand animation ───────────────────────────────────────────

    def toggle_collapse(self):
        if self.is_collapsed:
            self.expand()
        else:
            self.collapse()

    def collapse(self):
        if self.is_collapsed:
            return
        self.is_collapsed = True
        self._animate_fade_out()
        self._animate_width(self.min_width, self.collapsed_width)
        self.collapse_state_changed.emit(True)

    def expand(self):
        if not self.is_collapsed:
            return
        self.is_collapsed = False
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]
        for element in elements:
            element.setMaximumHeight(0)
        self._animate_width(self.collapsed_width, self.min_width)
        self._start_fade_in_timer()
        self.collapse_state_changed.emit(False)

    def _animate_width(self, start_width, end_width):
        if self.animation_group:
            self.animation_group.stop()

        self.animation_group = QParallelAnimationGroup()

        min_width_anim = QPropertyAnimation(self, b"minimumWidth")
        min_width_anim.setDuration(300)
        min_width_anim.setStartValue(start_width)
        min_width_anim.setEndValue(end_width)
        min_width_anim.setEasingCurve(QEasingCurve.InOutCubic)

        max_width_anim = QPropertyAnimation(self, b"maximumWidth")
        max_width_anim.setDuration(300)
        max_width_anim.setStartValue(start_width)
        max_width_anim.setEndValue(end_width)
        max_width_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.animation_group.addAnimation(min_width_anim)
        self.animation_group.addAnimation(max_width_anim)
        self.animation_group.start()

    def _animate_fade_out(self):
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]

        if self.fade_animation_group and self.fade_animation_group.state() == QAbstractAnimation.Running:
            self.fade_animation_group.stop()

        self.fade_animation_group = QParallelAnimationGroup()

        for element in elements:
            effect = QGraphicsOpacityEffect()
            element.setGraphicsEffect(effect)
            effect.setOpacity(1.0)
            self._element_effects[element] = effect

            fade_anim = QPropertyAnimation(effect, b"opacity")
            fade_anim.setDuration(300)
            fade_anim.setStartValue(1.0)
            fade_anim.setEndValue(0.0)
            fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
            self.fade_animation_group.addAnimation(fade_anim)

        self._animation_pool.append(self.fade_animation_group)
        if len(self._animation_pool) > 10:
            self._animation_pool.pop(0)

        self.fade_animation_group.start()

    def _hide_fade_elements(self):
        pass

    def _start_fade_in_timer(self):
        fade_start_timer = QTimer()
        fade_start_timer.setSingleShot(True)
        fade_start_timer.timeout.connect(self._animate_fade_in)
        fade_start_timer.start(300)
        self._fade_timer = fade_start_timer

    def _animate_fade_in(self):
        elements = [self.new_chat_btn, self.import_btn, self.search_input, self.chat_list]

        if self.fade_animation_group and self.fade_animation_group.state() == QAbstractAnimation.Running:
            self.fade_animation_group.stop()

        self.fade_animation_group = QParallelAnimationGroup()

        for element in elements:
            element.setMaximumHeight(16777215)

            effect = QGraphicsOpacityEffect()
            element.setGraphicsEffect(effect)
            effect.setOpacity(0.0)
            self._element_effects[element] = effect

            fade_anim = QPropertyAnimation(effect, b"opacity")
            fade_anim.setDuration(200)
            fade_anim.setStartValue(0.0)
            fade_anim.setEndValue(1.0)
            fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
            self.fade_animation_group.addAnimation(fade_anim)

        for element in elements:
            element.show()

        self._animation_pool.append(self.fade_animation_group)
        if len(self._animation_pool) > 10:
            self._animation_pool.pop(0)

        self.fade_animation_group.start()
