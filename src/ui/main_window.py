from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtGui import QIcon
import qasync
import os
import json
from config.settings import WINDOW_TITLE, WINDOW_SIZE
from config.theme import get_stylesheet
from src.ui.widgets.sidebar import Sidebar
from src.ui.widgets.chat_area import ChatArea
from src.ui.widgets.input_area import InputArea
from src.ui.widgets.header import Header
from src.ui.dialogs.model_change_notification import ModelChangeNotification
from src.services.chat_manager import chat_manager
from src.services.ollama_client import ollama_service

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuickChat")
        self.setMinimumSize(1200, 800)
        self.current_chat_id = None
        self.streaming_task = None  # Track the current streaming task
        self.stop_requested = False  # Flag to stop streaming
        self.generating_title = False  # Flag to prevent sending while title is being generated
        self.generating_response = False  # Flag to track if model is generating a response

        # Set window class name for Linux WM matching
        self.setObjectName("QuickChat")

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Apply saved theme
        from src.services.settings_manager import settings_manager
        theme_mode = settings_manager.get("theme", "dark")
        self.setStyleSheet(get_stylesheet(theme_mode))

        self.setup_ui()

    def setup_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main Layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.chat_selected.connect(self.load_chat)
        self.sidebar.new_chat_requested.connect(self.create_new_chat)
        self.sidebar.chat_deleted.connect(self.handle_chat_deleted)
        self.sidebar.collapse_state_changed.connect(self.on_sidebar_collapse_state_changed)
        main_layout.addWidget(self.sidebar, stretch=1)
        
        # Right Side (Header + Chat + Input)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.header = Header(on_detection_complete=self._on_detection_complete)
        self.header.settings_requested.connect(self.apply_settings)
        self.header.model_changed.connect(self.on_model_changed)
        self.header.sidebar_toggle_requested.connect(self.toggle_sidebar)
        self.chat_area = ChatArea()
        self.chat_area.fork_requested.connect(self.handle_fork_chat)
        self.input_area = InputArea()
        self.input_area.send_message.connect(self.handle_send_message)
        self.input_area.stop_requested.connect(self.handle_stop_requested)
        
        right_layout.addWidget(self.header)
        right_layout.addWidget(self.chat_area, stretch=1)
        right_layout.addWidget(self.input_area, stretch=0)
        
        main_layout.addWidget(right_widget, stretch=3)

    def _on_detection_complete(self, model_name):
        """Called by header when capabilities are loaded. Update input area button states."""
        print(f"[MainWindow] Updating capabilities for: {model_name}")
        supports_thinking = ollama_service.supports_thinking(model_name)
        supports_vision = ollama_service.supports_vision(model_name)
        self.input_area.set_thinking_supported(supports_thinking)
        self.input_area.set_vision_supported(supports_vision)
        print(f"[MainWindow] Updated thinking button state: {supports_thinking}")
        print(f"[MainWindow] Updated vision button state: {supports_vision}")

    def is_any_generation_active(self):
        """Check if any generation is happening (response or title)."""
        return self.generating_response or self.generating_title

    def set_generating_title(self, is_generating):
        """Disable model selector and sidebar during title generation."""
        self.generating_title = is_generating
        self.input_area.is_generating_title = is_generating
        self.header.model_selector.setEnabled(not is_generating)
        self.update_sidebar_buttons()

    def update_sidebar_buttons(self):
        """Enable/disable sidebar buttons based on generation state."""
        is_generating = self.is_any_generation_active()
        self.sidebar.new_chat_btn.setEnabled(not is_generating)
        self.sidebar.import_btn.setEnabled(not is_generating)
        self.sidebar.chat_list.setEnabled(not is_generating)
        self.header.refresh_btn.setEnabled(not is_generating)

    def on_model_changed(self, model_name):
        """Handle model selection change signal."""
        print(f"[MainWindow] Model changed signal for: {model_name}")

    def toggle_sidebar(self):
        """Toggle sidebar collapse/expand."""
        self.sidebar.toggle_collapse()

    def on_sidebar_collapse_state_changed(self, is_collapsed):
        """Update header button when sidebar collapse state changes."""
        self.header.set_sidebar_collapsed(is_collapsed)

    def apply_settings(self):
        """Apply settings from SettingsManager."""
        from src.services.settings_manager import settings_manager
        theme_mode = settings_manager.get("theme", "dark")
        self.setStyleSheet(get_stylesheet(theme_mode))
        # Reload chat to refresh message colors
        if self.current_chat_id:
            self.load_chat(self.current_chat_id)

    def create_new_chat(self):
        """Create a new chat and select it."""
        # Prevent creating new chat while any generation is happening
        if self.is_any_generation_active():
            print("[MainWindow] Cannot create new chat while generating. Please wait...")
            return

        # Use default model from settings
        from src.services.settings_manager import settings_manager
        default_model = settings_manager.get("default_model", "llama3")

        # Set the header selector to the default model
        index = self.header.model_selector.findText(default_model)
        if index >= 0:
            self.header.model_selector.setCurrentIndex(index)
        else:
            # If default model not found, use current or first available
            default_model = self.header.model_selector.currentText()

        new_chat = chat_manager.create_chat(title="New Chat", model_name=default_model)
        if new_chat:
            self.sidebar.add_chat_to_list(new_chat)
            self.load_chat(new_chat.id)

            # Show notification that default model has been selected
            notification = ModelChangeNotification(default_model, self)
            notification.show()

    def load_chat(self, chat_id):
        """Load messages for a specific chat."""
        # Prevent switching chats while any generation is happening
        if self.is_any_generation_active():
            print("[MainWindow] Cannot switch chats while generating. Please wait...")
            return

        self.current_chat_id = chat_id
        self.chat_area.clear()

        # Get the chat to retrieve the model used
        chat = chat_manager.get_chat(chat_id)
        if chat and chat.model_name:
            # Set the model selector to the chat's model
            index = self.header.model_selector.findText(chat.model_name)
            if index >= 0:
                self.header.model_selector.setCurrentIndex(index)

        messages = chat_manager.get_messages(chat_id)
        for msg in messages:
            thinking = msg.thinking or ""
            # Parse images if present
            images = []
            if msg.images:
                try:
                    images = json.loads(msg.images) if isinstance(msg.images, str) else msg.images
                except Exception as e:
                    print(f"[MainWindow] Error parsing images: {e}")
            self.chat_area.add_message(msg.role, msg.content, thinking, msg.id, images)

        # Scroll to bottom after all messages are loaded
        self.chat_area.scroll_to_bottom()

    def handle_chat_deleted(self, deleted_chat_id):
        """Handle when a chat is deleted."""
        # If the deleted chat was currently displayed, clear the chat area
        if self.current_chat_id == deleted_chat_id:
            self.chat_area.clear()
            self.current_chat_id = None

    def handle_fork_chat(self, message_id):
        """Handle forking a chat from a specific message."""
        # Prevent forking while any generation is happening
        if self.is_any_generation_active():
            print("[MainWindow] Cannot fork chat while generating. Please wait...")
            return

        if not self.current_chat_id:
            return

        new_chat = chat_manager.fork_chat(self.current_chat_id, message_id)
        if new_chat:
            self.sidebar.add_chat_to_list(new_chat)
            self.load_chat(new_chat.id)
            QMessageBox.information(self, "Success", f"Chat forked to '{new_chat.title}'")

    def handle_stop_requested(self):
        """Handle stop button click."""
        self.stop_requested = True

    @qasync.asyncSlot(str, str)
    async def handle_send_message(self, content, image_path=""):
        """Handle sending a message with optional image."""
        # Prevent sending while title is being generated
        if self.generating_title:
            print("[MainWindow] Cannot send message while generating chat title. Please wait...")
            return

        if not self.current_chat_id:
            self.create_new_chat()

        # Process image if provided
        images_json = None
        if image_path:
            import os
            import hashlib
            import json
            from config.settings import DATA_DIR

            # Copy image to images directory with unique name
            image_dir = os.path.join(DATA_DIR, "images")
            os.makedirs(image_dir, exist_ok=True)

            file_ext = os.path.splitext(image_path)[1]
            file_hash = hashlib.md5(open(image_path, 'rb').read()).hexdigest()
            unique_filename = f"{file_hash}{file_ext}"
            dest_path = os.path.join(image_dir, unique_filename)

            # Copy if not already there
            if not os.path.exists(dest_path):
                import shutil
                shutil.copy2(image_path, dest_path)

            # Store relative path in images JSON
            images_json = json.dumps([{"path": f"images/{unique_filename}", "type": file_ext[1:]}])

        # Save User Message
        user_msg = chat_manager.add_message(self.current_chat_id, "user", content, images=images_json)

        # Parse images for display
        display_images = []
        if images_json:
            try:
                display_images = json.loads(images_json)
            except Exception as e:
                print(f"[MainWindow] Error parsing images for display: {e}")

        # Display User Message
        self.chat_area.add_message("user", content, user_msg.id if user_msg else None, images=display_images)

        # Prepare Assistant Message Placeholder
        assistant_widget = self.chat_area.add_message("assistant", "", "", None)
        full_response = ""
        full_thinking = ""
        has_scrolled_for_response = False

        # Set UI to generating state
        self.generating_response = True
        self.update_sidebar_buttons()
        self.input_area.set_generating(True)
        self.header.set_generating(True)
        self.stop_requested = False

        # Stream Response
        model = self.header.model_selector.currentText()
        if not model:
            model = "llama3"

        # Update the chat's model_name to track the last used model
        chat_manager.update_chat_model(self.current_chat_id, model)

        history = chat_manager.get_messages(self.current_chat_id)
        messages_payload = [{'role': msg.role, 'content': msg.content} for msg in history]

        try:
            # Get thinking and vision mode settings from input area
            enable_thinking = self.input_area.is_thinking_enabled()
            # Use image if vision is enabled and we have an image
            # Pass the destination path where we copied the image
            image_to_send = None
            if self.input_area.vision_enabled and image_path:
                from config.settings import DATA_DIR
                import os
                import hashlib
                file_ext = os.path.splitext(image_path)[1]
                file_hash = hashlib.md5(open(image_path, 'rb').read()).hexdigest()
                unique_filename = f"{file_hash}{file_ext}"
                dest_path = os.path.join(DATA_DIR, "images", unique_filename)
                image_to_send = dest_path

            stream = ollama_service.chat_stream(model, messages_payload, enable_thinking=enable_thinking, images=image_to_send)

            async for chunk in stream:
                # Check if stop was requested
                if self.stop_requested:
                    print("Stopping response generation...")
                    break

                thinking_chunk = chunk.get('thinking', '')
                if thinking_chunk:
                    full_thinking += thinking_chunk
                    assistant_widget.update_thinking(full_thinking)
                    # Only scroll if user hasn't manually scrolled up
                    if not self.chat_area.user_scrolled_up:
                        self.chat_area.scroll_to_bottom()

                content_chunk = chunk.get('content', '')
                if content_chunk:
                    full_response += content_chunk
                    assistant_widget.update_response(full_response)
                    # Only scroll if user hasn't manually scrolled up
                    if not self.chat_area.user_scrolled_up:
                        self.chat_area.scroll_to_bottom()
        except RuntimeError as e:
            # Suppress expected httpcore GeneratorExit errors when stopping
            if "async generator ignored GeneratorExit" not in str(e):
                print(f"Error during streaming: {e}")
                # Make sure we have some content to save
                if not full_response:
                    full_response = f"[Error: {str(e)}]"
        except Exception as e:
            print(f"Error during streaming: {e}")
            # Make sure we have some content to save
            if not full_response:
                full_response = f"[Error: {str(e)}]"
        finally:
            # Stop thinking animation when streaming is complete
            assistant_widget.stop_thinking_animation()
            # Reset UI from generating state
            self.generating_response = False
            self.update_sidebar_buttons()
            self.input_area.set_generating(False)
            self.header.set_generating(False)
            # Refocus on input area for immediate typing
            self.input_area.text_input.setFocus()

        # Save Assistant Message
        assistant_msg = chat_manager.add_message(self.current_chat_id, "assistant", full_response, thinking=full_thinking)
        if assistant_msg:
            assistant_widget.message_id = assistant_msg.id

        # Update Chat Title if it's the first message - use AI to generate smart title
        chat = chat_manager.get_chat(self.current_chat_id)
        if chat and chat.title == "New Chat":
            try:
                # Count messages to ensure this is really the first exchange
                message_count = len(chat_manager.get_messages(self.current_chat_id))
                if message_count <= 2:  # User message + assistant message
                    # Only generate title if we have a reasonable response
                    if full_response and len(full_response.strip()) > 10:
                        print(f"Generating smart title for chat {self.current_chat_id}...")
                        self.set_generating_title(True)
                        try:
                            new_title = ""
                            # Buffer the title generation (collect all chunks)
                            async for title_chunk in ollama_service.generate_chat_title(content, full_response, model):
                                new_title += title_chunk

                            # Save the final title to database
                            if new_title and new_title.strip():
                                chat_manager.update_chat_title(self.current_chat_id, new_title)

                            # Animate the title in the sidebar with smooth typing effect
                            self.sidebar.update_chat_title(self.current_chat_id, new_title.strip() if new_title else "", animate=True)

                            if new_title and new_title.strip():
                                print(f"Chat title updated to: {new_title}")
                            else:
                                print("Generated title was empty, using fallback")
                                fallback_title = content[:30] + "..." if len(content) > 30 else content
                                chat_manager.update_chat_title(self.current_chat_id, fallback_title)
                                self.sidebar.load_chats()
                        finally:
                            self.set_generating_title(False)
                    else:
                        # Response too short, use fallback title
                        fallback_title = content[:30] + "..." if len(content) > 30 else content
                        chat_manager.update_chat_title(self.current_chat_id, fallback_title)
                        self.sidebar.load_chats()
            except Exception as e:
                print(f"Error generating chat title: {e}")
                self.set_generating_title(False)
                fallback_title = content[:30] + "..." if len(content) > 30 else content
                chat_manager.update_chat_title(self.current_chat_id, fallback_title)
                self.sidebar.load_chats()
