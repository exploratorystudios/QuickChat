# QuickChat

> A sleek, feature-rich chat interface for local LLM inference with Ollama on Windows or GNOME Linux environments.

**QuickChat** is a powerful desktop application that provides a professional, user-friendly interface for interacting with large language models running locally on your machine via Ollama. Built with PySide6 and designed for optimal performance and responsiveness, QuickChat brings the sophistication of commercial chat interfaces to your local LLM setup.

<img src="icon.png" alt="QuickChat" width="200" height="200">

## ✨ Features

### 🧠 Advanced Thinking Support

- **Dual Thinking Modes**: Automatically detects and supports both:
  - **Parameter-based thinking** (native Ollama `think=True/False` API)
  - **Directive-based thinking** (GGUF quantizations with `/think` and `/no_think` text directives)
- **Smart Detection**: Automatically determines which thinking method to use based on model capabilities
- **Thinking Visualization**: Dedicated thinking bubbles show model reasoning process in real-time
- **Thinking Control**: Enable/disable thinking per-message with model capability awareness

### 👁️ Vision & Image Support

- **Multi-format image support**: Upload PNG, JPG, and other common formats
- **Vision-aware models**: Automatically detects vision capabilities and enables image features
- **Smart image handling**: Only sends the most recent image to avoid redundant encoding
- **Image preservation**: Chat history maintains image thumbnails and metadata

### 💬 Intelligent Conversation Management

- **Smart chat naming**: AI-generated titles for new conversations (without slowing down responses as it avoids thinking when doing so)
- **Fork conversations**: Branch off from any message point to explore alternative paths
- **Conversation history**: Full chat persistence with SQLite backend
- **Export options**: Save chats as:
  - Markdown (human-readable format)
  - JSON (complete metadata preservation)
- **Import chats**: Restore previously exported conversations
- **Search conversations**: Quick lookup of past chats

### 🎨 Professional UI/UX

- **Dark & Light themes**: Toggle between themes with automatic persistence
- **Model change notifications**: Professional animated popup confirms model selection
- **Real-time streaming**: Watch responses generate character-by-character
- **Thinking visualization**: Collapsible thinking bubbles for each message
- **Smooth animations**: Professional slide-in/slide-out effects
- **Responsive design**: Adapts gracefully to different window sizes
- **Keyboard shortcuts**: Efficient keyboard-first workflow (Enter to send, Ctrl+Enter for newline)

### 🛡️ Smart Generation Safeguards

- **Comprehensive protection during generation**:
  - Can't switch chats while generating
  - Can't create new chats during generation
  - Can't import chats during generation
  - Can't change models during generation
  - Can't refresh model list during generation
  - Can still type next message (text input remains enabled)
  - Stop button always clickable to interrupt generation
- **Thinking generation protection**: Additional safeguards during AI-powered chat naming
- **User-friendly notifications**: Clear feedback about why actions are disabled

### ⚙️ Advanced Configuration

- **Model selector**: Dropdown with all available Ollama models
- **Refresh models**: Dynamically update model list with model persistence
- **Default model selection**: Configure which model loads on startup
- **Settings panel**: Persistent user preferences
- **Theme persistence**: Your theme choice is remembered

## 🚀 Quick Start

### Installation

The easiest way to install QuickChat is with the provided installation script:

```bash
# Clone or download QuickChat
cd QuickChat

# Run the installer (works on fresh systems too)
bash ./install.sh
```

That's it! QuickChat will be installed and ready to launch.

### Launching QuickChat

After installation, launch QuickChat by:

```bash
# From command line
quickchat

# Or find it in your applications menu as "QuickChat"
```

### First Run

1. **Ensure Ollama is running** - QuickChat needs Ollama to be accessible locally
2. **Select a model** - Choose from your available Ollama models in the dropdown
3. **Start chatting** - Type your message and press Enter or click Send
4. **Explore features**:
   - Click 🧠 for thinking mode
   - Click 🖼️ and attach an image for vision models
   - Right-click any message to fork conversations or copy message

## 📋 System Requirements

### Minimum Requirements

- **OS**: Linux with GNOME desktop environment (Ubuntu 20.04+, Fedora 33+, Debian 11+, etc.)
- **Python**: 3.8 or higher
- **RAM**: 4GB (recommended 8GB+)
- **Ollama**: Running locally with at least one model loaded

### Dependencies (Auto-installed)

```
PySide6>=6.6.0        # GUI framework
ollama>=0.1.6         # Ollama client library
SQLAlchemy>=2.0.0     # Database ORM
qasync>=0.27.1        # Async event loop integration
mistune>=3.0.0        # Markdown rendering
pygments>=2.17.0      # Syntax highlighting
aiohttp>=3.9.0        # Async HTTP client
Pillow>=10.0.0        # Image processing
matplotlib>=3.7.0     # For visualization
```

## 📦 Installation Methods

### Method 1: Automated Installation (Recommended)

```bash
bash ./install.sh
```

The installer handles everything:
- ✅ Creates Python virtual environment
- ✅ Installs all dependencies
- ✅ Sets up application directories
- ✅ Creates GNOME desktop entry
- ✅ Makes `quickchat` command available

### Method 2: Manual Installation

```bash
# Create installation directory
mkdir -p ~/.local/share/quickchat/app
cd ~/.local/share/quickchat/app

# Copy project files
cp -r /path/to/QuickChat/src .
cp /path/to/QuickChat/main.py .
cp /path/to/QuickChat/config .
cp /path/to/QuickChat/icon.png .
cp /path/to/QuickChat/requirements.txt .

# Create virtual environment
python3 -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Create launcher
mkdir -p ~/.local/bin
cat > ~/.local/bin/quickchat << 'EOF'
#!/bin/bash
cd ~/.local/share/quickchat/app
./venv/bin/python3 main.py "$@"
EOF
chmod +x ~/.local/bin/quickchat

# Add to PATH if needed
export PATH="$HOME/.local/bin:$PATH"
```

### Method 3: Development Installation

```bash
# Clone the repository
git clone <repository-url>
cd QuickChat

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run directly
python3 main.py
```

### Windows Installation 🪟

QuickChat includes batch scripts for quick setup and running on Windows:

#### Using Batch Scripts (Easiest)

1. **Double-click `setup.bat`** to set up the environment
   - Creates Python virtual environment
   - Installs all dependencies
   - Checks for Python installation
   - Handles errors with clear messages

2. **Double-click `run.bat`** to launch QuickChat
   - Activates virtual environment
   - Starts the application
   - Automatically cleans up on exit

#### Manual Setup on Windows

If you prefer not to use batch scripts or need troubleshooting:

```cmd
# Open Command Prompt or PowerShell in the QuickChat directory

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run QuickChat
python main.py
```

#### Troubleshooting Windows Installation

**"Python is not installed or not in PATH"**
- Download Python from https://python.org
- During installation, **check "Add Python to PATH"**
- Restart your computer
- Try again

**"Virtual environment not found"**
- Run `setup.bat` first to create it
- Make sure you're in the QuickChat directory

**"Permission denied" or script execution errors**
- Right-click `setup.bat` → "Run as administrator"
- Or use Command Prompt/PowerShell as administrator

**Ollama not connecting**
- Ensure Ollama is running: `ollama serve`
- Verify it's running on `http://localhost:11434`

## 🎮 Usage Guide

### Basic Chatting

1. **Select a model** using the dropdown in the header
2. **Type your message** in the input area at the bottom
3. **Press Enter** or click the **Send** button
4. **Watch it stream** - Responses appear in real-time
5. **Continue the conversation** - Your full chat history is maintained

### Using Thinking Mode

Thinking mode allows models to "reason through" complex problems before responding:

- **Enable thinking**: Click the 🧠 **Thinking** button to toggle thinking mode
- **View reasoning**: Click the thinking bubble to expand and see the model's internal reasoning
- **Better responses**: Thinking helps models provide more accurate, well-reasoned answers

Thinking is automatically enabled for models that support it. Models are detected automatically:
- **Ollama native thinking** (qwen3, deepseek-r1, etc.): Uses API-level thinking parameters
- **GGUF quantizations** (with `/think` support via the "Thinking" button): Uses text directives for thinking

### Using Vision Mode

Send images to vision-capable models for analysis:

1. **Enable vision**: Click the 🖼️ **Vision** button
2. **Attach image**: The attachment button appears - click to select an image
3. **Send with context**: Type your question and send - the image is included
4. **View history**: Image thumbnails appear in chat history

**Supported formats**: PNG, JPG, WebP, and other common image formats

**Smart image handling**: Only the most recent image is sent to the model, avoiding redundant re-encoding while maintaining full conversation context.

### Conversation Management

#### Creating & Switching Chats

- **New Chat**: Click "New Chat" button to create a conversation
  - Default model is automatically selected
  - Chat is named "New Chat" initially
  - Smart title is generated after the first response
- **Switch Chats**: Click any chat in the sidebar to load it
- **Disabled during generation**: Can't switch chats while model is generating

#### Forking Conversations

Branch off from any point in a conversation:

1. **Right-click any message** to open the context menu
   - Shows "Copy Message" and "Fork Chat from Here" options
2. **Select "Fork Chat from Here"** to create a branch
3. **New chat is created** with all messages up to that point
4. **Continue separately**: The fork is independent from the original chat

This is useful for exploring alternative conversation paths without losing your original discussion.

#### Searching Chats

1. **Use the search box** at the top of the sidebar
2. **Type keywords** to filter chat titles
3. **Clear search** to see all chats again

#### Exporting & Importing

**Export a chat** for backup or sharing:
- Right-click a chat → "Export as Markdown" or "Export as JSON"
- **Markdown**: Human-readable format, good for sharing
- **JSON**: Complete metadata, good for backups

**Import previously exported chats**:
- Click "Import" button
- Select the exported JSON file
- Chat is restored with full history

### Customization

#### Theme Switching

- Click **Settings** button in the header
- Toggle between **Dark** and **Light** themes
- Your choice is saved and persists across sessions

#### Model Selection

- **Current model**: Shown in the dropdown at the top right
- **Change model**: Select any available model from the dropdown
- **Refresh list**: Click 🔄 **Refresh** to update available models
- **Default model**: Set in Settings for new chats

#### Settings

Open the Settings dialog to:
- ✅ Change theme (Dark/Light)
- ✅ Set default model for new chats
- ✅ View application information

## 🏗️ Architecture

### Project Structure

```
QuickChat/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── icon.png               # Application icon
├── config/                # Configuration files
│   ├── settings.py        # Settings constants
│   └── theme.py           # Theme definitions
├── src/                   # Source code
│   ├── core/              # Core functionality
│   │   ├── database.py    # SQLite ORM setup
│   │   └── models.py      # SQLAlchemy models (Chat, Message)
│   ├── services/          # Business logic
│   │   ├── chat_manager.py        # Chat CRUD operations
│   │   ├── ollama_client.py       # Ollama API integration
│   │   ├── settings_manager.py    # Settings persistence
│   │   └── markdown_processor.py  # Markdown rendering
│   └── ui/                # User interface
│       ├── main_window.py # Main window orchestration
│       ├── widgets/       # UI components
│       │   ├── header.py          # Header with model selector
│       │   ├── sidebar.py         # Chat list sidebar
│       │   ├── chat_area.py       # Message display area
│       │   ├── input_area.py      # Message input & controls
│       │   └── message_widget.py  # Individual message display
│       └── dialogs/       # Dialog windows
│           ├── settings_dialog.py
│           └── model_change_notification.py
└── install.sh / uninstall.sh    # Installation scripts
```

### Key Components

#### **OllamaClient** (`src/services/ollama_client.py`)
Handles all Ollama interactions:
- Model capability detection (thinking, vision)
- Smart thinking method determination (parameter vs directive)
- Streaming chat responses with thinking extraction
- Intelligent message preparation with directives
- Chat title generation

#### **ChatManager** (`src/services/chat_manager.py`)
Manages conversation data:
- Create, read, update, delete chats
- Message persistence
- Chat forking
- Export/import functionality
- Thinking and image metadata preservation

#### **MainWindow** (`src/ui/main_window.py`)
Application orchestration:
- Generation state management (response, thinking, title)
- UI safeguards during generation
- Chat switching and loading
- Message streaming and display
- Title generation with auto-completion

#### **Database** (`src/core/`)
SQLAlchemy-based persistence:
- **Chat model**: Stores conversation metadata
- **Message model**: Stores individual messages with thinking and images

## 🔧 Advanced Features

### Model Capability Detection

QuickChat automatically detects model capabilities through two methods:

**1. API-based detection** (Primary)
- Uses Ollama's `show()` API to get model capabilities
- Checks for "thinking" or "reasoning" in capabilities field
- Sets `thinking_method='parameter'` for native Ollama support
- Instant and reliable

**2. Keyword-based detection** (Fallback)
- Used when API detection fails (offline Ollama)
- Recognizes model names: `qwen3`, `qwen2.5`, `deepseek-r1`, `deepseek-v3`, `qwq`
- Sets `thinking_method='directive'` for GGUF support
- Allows `/think` and `/no_think` directives

### Smart Message Preparation

Depending on detected thinking method:

**Parameter-based models** (e.g., Ollama native):
```python
# Sends think=True/False as API parameter
chat_stream(model, messages, think=True)
```

**Directive-based models** (e.g., GGUF):
```python
# Prepends /think directive to first user message
messages[0]['content'] = "/think\n" + original_content
```

### Thinking Tag Extraction

For directive-based models, thinking is embedded in response:
```
<think>
Model's internal reasoning here...
</think>
Actual response text here...
```

QuickChat intelligently:
- ✅ Extracts `<think>...</think>` tags while streaming
- ✅ Displays thinking in separate bubble
- ✅ Keeps response clean without tags
- ✅ Buffers content to handle split tags across chunks

### Vision Model Optimization

When sending images with vision models:
- **Only current image sent** to model (avoids re-encoding)
- **Full conversation context maintained** (previous messages preserved)
- **Images cached** (reused across messages if unchanged)
- **Metadata preserved** (image paths stored in chat history)

### Generation State Management

Comprehensive safeguards prevent UI corruption during any generation:

**Protected operations** (disabled during generation):
- Chat switching
- New chat creation
- Chat importing
- Model changing
- Model list refreshing

**Allowed operations** (during generation):
- Typing (for next message)
- Viewing previous messages
- Reading chat history
- Stopping generation (Stop button)

## 🐛 Troubleshooting

### QuickChat Won't Start

**Problem**: "Python executable not found"
```
Error: Python executable not found at ~/.local/share/quickchat/app/venv/bin/python3
```

**Solution**:
1. Reinstall QuickChat: `bash ./uninstall.sh` then `bash ./install.sh`
2. Verify venv was created: `ls ~/.local/share/quickchat/app/venv/bin/`
3. Check Python installation: `python3 --version`

**Problem**: "Ollama connection refused"
```
Error: Connection refused - is Ollama running?
```

**Solution**:
1. Start Ollama: `ollama serve` (in another terminal)
2. Verify connection: `curl http://localhost:11434/api/tags`
3. Change host in config if using non-default Ollama location

### Thinking Not Working

**Problem**: Thinking button is disabled for a model

**Causes**:
- Model doesn't support thinking (most don't)
- Ollama API couldn't detect capabilities
- Model name doesn't match known thinking models

**Solution**:
- Use a known thinking model: `qwen3`, `deepseek-r1`, `qwq`
- Check Ollama model capabilities: `ollama show <model>`
- Refresh model list: Click 🔄 **Refresh** button

### Images Not Showing

**Problem**: Vision button is disabled or images don't upload

**Solutions**:
- Verify model supports vision: `ollama show <model>`
- Check supported formats: PNG, JPG (WebP varies by model)
- Verify file is readable and not corrupted
- Check disk space: `df -h ~/.local/share/quickchat/data/`

### Dropdown Scrollbar Not Showing

**Problem**: Many models but can't see scrollbar

**Solution**:
- This is automatic - dropdown shows first 6 items
- Scroll with mouse wheel or arrow keys to see more
- Model selection is preserved after refresh

### Chats Disappeared

**Problem**: Chats were deleted accidentally

**Solutions**:
- Check recovery: `~/.local/share/quickchat/data/quickchat.db` (if not deleted)
- Restore from backup: `~/.local/share/quickchat/data_backup/`
- Re-import from exported JSON: Click Import button

## 📊 Performance Tips

### Optimize Response Speed

1. **Smaller models**: Use 7B/8B parameters for faster responses
2. **Quantization**: Use 4-bit or 8-bit quantized models
3. **System resources**: Close other applications, especially browsers
4. **SSD**: Store Ollama models on fast SSD if possible

### Image Processing

- Smaller images process faster
- Vision models are inherently slower - expect 30-60s responses
- Only the latest image is sent to model (auto-optimized)

### Database Performance

- Large chat histories might slow sidebar loading
- Archive old chats periodically
- Export chats to JSON for permanent storage

## 🔒 Privacy & Security

- ✅ **Fully local**: All data stays on your machine
- ✅ **No cloud sync**: No data sent to external servers
- ✅ **No telemetry**: Zero tracking or analytics
- ✅ **Open source**: Code is transparent and auditable
- ✅ **Ollama required**: Uses local Ollama instance only

**Data locations**:
- Chats: `~/.local/share/quickchat/data/quickchat.db`
- Settings: `~/.config/QuickChat/`
- Images: `~/.local/share/quickchat/data/images/`

## 🗑️ Uninstallation

To remove QuickChat:

```bash
bash ./uninstall.sh
```

Choose whether to keep or remove your chat history. You can also manually remove it:

```bash
# Remove application
rm -rf ~/.local/share/quickchat/app
rm ~/.local/bin/quickchat
rm ~/.local/share/applications/quickchat.desktop

# Remove data (optional)
rm -rf ~/.local/share/quickchat/data
rm -rf ~/.config/QuickChat
```

## 🤝 Contributing

Contributions are welcome! Areas that could use help:

- **UI improvements**: Better layouts, themes, icons
- **Performance**: Streaming optimization, caching
- **Features**: New model support, export formats, plugins
- **Documentation**: Guides, examples, tutorials
- **Bug fixes**: Issue reports with details

## 🙏 Acknowledgments

- **Ollama**: For the amazing local LLM inference platform
- **PySide6**: For the excellent Qt bindings
- **Mistune**: For markdown rendering
- **SQLAlchemy**: For database ORM

## 📝 Changelog

### v1.0.0 (Current)
- ✨ Initial release
- 🧠 Smart thinking detection and handling (parameter + directive modes)
- 👁️ Vision model support with image handling
- 💬 Full conversation management (create, fork, export, import)
- 🎨 Professional UI with dark/light themes
- 🛡️ Comprehensive generation safeguards
- 📱 Responsive design
- 🚀 Real-time streaming responses
- 🔍 Chat search and filtering
- 💾 SQLite persistence

---

**Made with ❤️ for the local LLM community**

Happy chatting! 🚀
