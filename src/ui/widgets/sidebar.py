from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLineEdit, QListWidget, QListWidgetItem, QLabel)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QIcon
from src.services.chat_manager import chat_manager

class Sidebar(QWidget):
    chat_selected = Signal(int) # Emits chat_id
    new_chat_requested = Signal()
    chat_deleted = Signal(int) # Emits deleted chat_id

    def __init__(self):
        super().__init__()
        self.setObjectName("Sidebar")
        self.setFixedWidth(280)
        self.setup_ui()
        self.load_chats()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header / New Chat
        header_layout = QHBoxLayout()
        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.setObjectName("PrimaryButton")
        self.new_chat_btn.clicked.connect(self.on_new_chat)
        header_layout.addWidget(self.new_chat_btn)
        
        self.import_btn = QPushButton("Import")
        self.import_btn.clicked.connect(self.on_import_chat)
        header_layout.addWidget(self.import_btn)
        
        layout.addLayout(header_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search chats...")
        self.search_input.textChanged.connect(self.filter_chats)
        layout.addWidget(self.search_input)

        # Chat List
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.on_chat_clicked)
        layout.addWidget(self.chat_list)

    def load_chats(self):
        self.chat_list.clear()
        chats = chat_manager.get_all_chats()
        for chat in chats:
            item = QListWidgetItem(chat.title)
            item.setData(Qt.UserRole, chat.id)
            self.chat_list.addItem(item)

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
