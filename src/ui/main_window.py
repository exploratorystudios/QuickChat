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

from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtGui import QIcon
import asyncio
import qasync
import os
import json
import time
from config.settings import WINDOW_TITLE, WINDOW_SIZE
from config.theme import get_stylesheet
from src.ui.widgets.sidebar import Sidebar
from src.ui.widgets.chat_area import ChatArea
from src.ui.widgets.context_bar import ContextBar
from src.ui.widgets.input_area import InputArea
from src.ui.widgets.header import Header
from src.ui.dialogs.model_change_notification import ModelChangeNotification
from src.services.chat_manager import chat_manager
from src.services.ollama_client import ollama_service

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QuickChat")
        self.setMinimumSize(1200, 848)
        self.current_chat_id = None
        self.streaming_task = None  # Track the current streaming task
        self.stop_requested = False  # Flag to stop streaming
        self.generating_title = False  # Flag to prevent sending while title is being generated
        self.generating_response = False  # Flag to track if model is generating a response
        self.streaming_chat_id = None  # Chat ID of the chat currently streaming
        self.background_chat_widgets = None  # Widget snapshot when streaming chat is backgrounded
        self._title_gen_task = None           # asyncio.Task for background title generation
        self._title_gen_for_chat_id = None    # Which chat the active title task belongs to

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
        self.context_bar = ContextBar()
        self.chat_area = ChatArea()
        self.chat_area.fork_requested.connect(self.handle_fork_chat)
        self.input_area = InputArea()
        self.input_area.send_message.connect(self.handle_send_message)
        self.input_area.stop_requested.connect(self.handle_stop_requested)

        right_layout.addWidget(self.header)
        right_layout.addWidget(self.context_bar)
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
        # Model max context is now cached — refresh the bar
        self.update_context_bar()

    def update_context_bar(self):
        """Recompute estimated token usage and refresh the context bar display."""
        from src.services.settings_manager import settings_manager
        ctx_size = settings_manager.get("context_size", 8192)
        model = self.header.model_selector.currentText()
        model_max = ollama_service.get_model_max_context(model)

        if self.current_chat_id is None:
            self.context_bar.clear()
            return

        messages = chat_manager.get_messages(self.current_chat_id)
        # Rough estimate: 4 chars ≈ 1 token, plus ~4 tokens per message for role/formatting
        total_chars = sum(len(msg.content or '') + len(msg.thinking or '') for msg in messages)
        overhead = len(messages) * 4
        used_tokens = max(0, total_chars // 4 + overhead)

        self.context_bar.update_display(used_tokens, ctx_size, model_max)

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
        """Enable/disable sidebar buttons based on generation state.

        Only response generation (not title generation) locks down navigation.
        Title generation is safe to run while switching chats, importing, or
        creating new chats because it uses captured local variables and writes
        results back via streaming_for_chat_id regardless of current_chat_id.
        Sending new messages stays blocked during both via input_area.on_send.
        """
        streaming = self.generating_response
        self.sidebar.new_chat_btn.setEnabled(not streaming)
        self.sidebar.import_btn.setEnabled(True)  # Always — sidebar has no guard now
        self.sidebar.chat_list.setEnabled(True)    # Always allow chat switching
        self.header.refresh_btn.setEnabled(not streaming)

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
        # Force-reload current chat to repaint message bubbles with new theme colors.
        # Must null current_chat_id first to bypass the early-return guard in load_chat.
        if self.current_chat_id:
            chat_id = self.current_chat_id
            self.current_chat_id = None
            self.load_chat(chat_id)
        # Context size may have changed — refresh the bar regardless
        self.update_context_bar()

    def create_new_chat(self):
        """Create a new chat and select it."""
        # Block only during active response streaming, not title generation
        if self.generating_response:
            print("[MainWindow] Cannot create new chat while streaming a response.")
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
        """Load messages for a specific chat.

        Chat switching is always allowed, even during streaming.  When switching
        away from a streaming chat its widgets are detached (not destroyed) so
        the background stream can keep writing to them.  Switching back restores
        those widgets instantly without a DB reload.
        """
        if chat_id == self.current_chat_id:
            return

        # ── Switching BACK to the chat that's streaming in the background ──
        if chat_id == self.streaming_chat_id and self.background_chat_widgets is not None:
            self.chat_area.restore_widgets(self.background_chat_widgets)
            self.background_chat_widgets = None
            self.current_chat_id = chat_id
            chat = chat_manager.get_chat(chat_id)
            if chat and chat.model_name:
                index = self.header.model_selector.findText(chat.model_name)
                if index >= 0:
                    self.header.model_selector.setCurrentIndex(index)
            self.update_context_bar()
            return

        # ── Switching AWAY from the chat that's currently streaming ──
        # Detach its widgets instead of destroying them so the stream continues.
        if self.streaming_chat_id is not None and self.current_chat_id == self.streaming_chat_id:
            self.background_chat_widgets = self.chat_area.detach_widgets()
        else:
            self.chat_area.clear()

        self.current_chat_id = chat_id

        chat = chat_manager.get_chat(chat_id)
        if chat and chat.model_name:
            index = self.header.model_selector.findText(chat.model_name)
            if index >= 0:
                self.header.model_selector.setCurrentIndex(index)

        messages = chat_manager.get_messages(chat_id)
        for msg in messages:
            thinking = msg.thinking or ""
            images = []
            if msg.images:
                try:
                    images = json.loads(msg.images) if isinstance(msg.images, str) else msg.images
                except Exception as e:
                    print(f"[MainWindow] Error parsing images: {e}")
            self.chat_area.add_message(msg.role, msg.content, thinking, msg.id, images)

        self.chat_area.scroll_to_bottom()
        self.update_context_bar()

    def handle_chat_deleted(self, deleted_chat_id):
        """Handle when a chat is deleted."""
        # If the deleted chat was currently displayed, clear the chat area
        if self.current_chat_id == deleted_chat_id:
            self.chat_area.clear()
            self.current_chat_id = None
            self.context_bar.clear()

        # If response streaming is running for this chat, stop it.
        # This covers both the foreground case and the background-stream case
        # (where the user switched away but the stream kept going).
        if self.streaming_chat_id == deleted_chat_id and self.generating_response:
            self.stop_requested = True
            # Discard any detached background widgets for this chat
            if self.background_chat_widgets is not None:
                for w in self.background_chat_widgets:
                    w.deleteLater()
                self.background_chat_widgets = None

        # If title generation is running for this chat, cancel it immediately.
        # This aborts the Ollama read and unlocks the UI without waiting for the
        # request to finish.
        if (self._title_gen_for_chat_id == deleted_chat_id
                and self._title_gen_task is not None
                and not self._title_gen_task.done()):
            self._title_gen_task.cancel()

    def handle_fork_chat(self, message_id):
        """Handle forking a chat from a specific message."""
        # Block only during active response streaming, not title generation
        if self.generating_response:
            print("[MainWindow] Cannot fork chat while streaming a response.")
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

    def _on_stream_content_updated(self):
        """Scroll to bottom when smooth streaming reveals new content.

        Only scrolls if the user is currently viewing the streaming chat —
        not when the stream is running in the background.
        """
        if self.current_chat_id == self.streaming_chat_id:
            if not self.chat_area.user_scrolled_up:
                self.chat_area.scroll_to_bottom()

    async def _run_title_generation(self, streaming_for_chat_id, content, full_response, model):
        """Background asyncio.Task that generates and saves a chat title.

        Runs as a Task so it can be cancelled instantly (via _title_gen_task.cancel())
        when the originating chat is deleted, without waiting for Ollama to finish.
        """
        try:
            new_title = ""
            async for title_chunk in ollama_service.generate_chat_title(content, full_response, model):
                new_title += title_chunk

            # Chat may have been deleted while we were generating — check before saving.
            if not chat_manager.get_chat(streaming_for_chat_id):
                print(f"[TitleGen] Chat {streaming_for_chat_id} gone; discarding title.")
            else:
                if new_title and new_title.strip():
                    chat_manager.update_chat_title(streaming_for_chat_id, new_title)
                    self.sidebar.update_chat_title(streaming_for_chat_id, new_title.strip(), animate=True)
                    print(f"[TitleGen] Title updated: {new_title}")
                else:
                    print("[TitleGen] Empty title; using fallback.")
                    fallback = content[:30] + "..." if len(content) > 30 else content
                    chat_manager.update_chat_title(streaming_for_chat_id, fallback)
                    self.sidebar.load_chats()

        except asyncio.CancelledError:
            # Chat was deleted — abort silently. finally still runs.
            print(f"[TitleGen] Cancelled for chat {streaming_for_chat_id}.")

        except Exception as e:
            print(f"[TitleGen] Error: {e}")
            fallback = content[:30] + "..." if len(content) > 30 else content
            if chat_manager.get_chat(streaming_for_chat_id):
                chat_manager.update_chat_title(streaming_for_chat_id, fallback)
                self.sidebar.load_chats()

        finally:
            self.set_generating_title(False)
            self._title_gen_task = None
            self._title_gen_for_chat_id = None

    @qasync.asyncSlot(str, str)
    async def handle_send_message(self, content, image_path=""):
        """Handle sending a message with optional image."""
        # Prevent sending while title is being generated
        if self.generating_title:
            print("[MainWindow] Cannot send message while generating chat title. Please wait...")
            return

        if not self.current_chat_id:
            self.create_new_chat()

        # Capture the chat this message belongs to.  The user may switch to
        # another chat mid-stream, so self.current_chat_id can change; all DB
        # writes after the stream must use this captured value instead.
        streaming_for_chat_id = self.current_chat_id

        # Discard any widget snapshot left over from a *completed* background
        # stream (content already saved to DB; load_chat will reload if needed).
        if self.background_chat_widgets is not None:
            for w in self.background_chat_widgets:
                w.deleteLater()
            self.background_chat_widgets = None

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
        self.update_context_bar()

        # Move chat to top of unpinned section now that it has a new message
        self.sidebar.bump_chat_to_top(streaming_for_chat_id)

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
        assistant_widget.start_streaming()
        assistant_widget.stream_updated.connect(self._on_stream_content_updated)
        full_response = ""
        full_thinking = ""
        has_scrolled_for_response = False
        _toks_start: float | None = None   # time of first content token
        _toks_chars: int = 0               # total content chars received
        _think_toks_start: float | None = None  # time of first thinking token
        _think_toks_chars: int = 0              # total thinking chars received

        # Set UI to generating state
        self.generating_response = True
        self.update_sidebar_buttons()
        self.input_area.set_generating(True)
        self.header.set_generating(True)
        self.stop_requested = False
        self.streaming_chat_id = streaming_for_chat_id

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

            # Determine effective context size, clamped to the model's max
            from src.services.settings_manager import settings_manager as _sm
            ctx_size = _sm.get("context_size", 8192)
            model_max = ollama_service.get_model_max_context(model)
            if model_max and ctx_size > model_max:
                print(f"[MainWindow] context_size {ctx_size} exceeds model max {model_max}; clamping.")
                ctx_size = model_max

            stream = ollama_service.chat_stream(model, messages_payload, enable_thinking=enable_thinking, images=image_to_send, num_ctx=ctx_size)

            async for chunk in stream:
                # Check if stop was requested
                if self.stop_requested:
                    print("Stopping response generation...")
                    break

                thinking_chunk = chunk.get('thinking', '')
                if thinking_chunk:
                    full_thinking += thinking_chunk
                    assistant_widget.stream_thinking(full_thinking)
                    # Scrolling handled by stream_updated signal

                    # Tok/s tracking for thinking phase
                    if _think_toks_start is None:
                        _think_toks_start = time.monotonic()
                    _think_toks_chars += len(thinking_chunk)
                    elapsed = time.monotonic() - _think_toks_start
                    if elapsed >= 0.75:
                        self.input_area.show_toks((_think_toks_chars / 4.0) / elapsed)

                content_chunk = chunk.get('content', '')
                if content_chunk:
                    full_response += content_chunk
                    assistant_widget.stream_token(full_response)
                    # Scrolling handled by stream_updated signal

                    # Tok/s tracking — start timer on the first content token to
                    # measure decode speed only (excludes prefill / first-token latency)
                    if _toks_start is None:
                        _toks_start = time.monotonic()
                    _toks_chars += len(content_chunk)
                    elapsed = time.monotonic() - _toks_start
                    if elapsed >= 0.75:  # wait for a stable sample before showing
                        self.input_area.show_toks((_toks_chars / 4.0) / elapsed)
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
            # Flush remaining buffered text and do full render with LaTeX
            assistant_widget.finish_streaming()
            # Stop thinking animation when streaming is complete
            assistant_widget.stop_thinking_animation()
            # Hide tok/s overlay
            self.input_area.hide_toks()
            # Reset UI from generating state
            self.streaming_chat_id = None
            self.generating_response = False
            self.update_sidebar_buttons()
            self.input_area.set_generating(False)
            self.header.set_generating(False)
            # Refocus on input area for immediate typing
            self.input_area.text_input.setFocus()

        # Save Assistant Message — use streaming_for_chat_id, not self.current_chat_id,
        # because the user may have switched to a different chat during streaming.
        assistant_msg = chat_manager.add_message(streaming_for_chat_id, "assistant", full_response, thinking=full_thinking)
        if assistant_msg:
            assistant_widget.message_id = assistant_msg.id
        self.update_context_bar()

        # Update Chat Title if it's the first message - use AI to generate smart title
        chat = chat_manager.get_chat(streaming_for_chat_id)
        if chat and chat.title == "New Chat":
            message_count = len(chat_manager.get_messages(streaming_for_chat_id))
            if message_count <= 2:  # User message + assistant message
                if full_response and len(full_response.strip()) > 10:
                    print(f"Generating smart title for chat {streaming_for_chat_id}...")
                    self.set_generating_title(True)
                    self._title_gen_for_chat_id = streaming_for_chat_id
                    self._title_gen_task = asyncio.create_task(
                        self._run_title_generation(streaming_for_chat_id, content, full_response, model)
                    )
                else:
                    # Response too short — use a simple fallback immediately
                    fallback_title = content[:30] + "..." if len(content) > 30 else content
                    chat_manager.update_chat_title(streaming_for_chat_id, fallback_title)
                    self.sidebar.load_chats()
