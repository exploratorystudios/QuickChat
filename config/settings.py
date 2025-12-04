import os
import sys
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Use platform-appropriate data storage location
if sys.platform == "win32":
    # Windows: Use AppData\Local
    DATA_DIR = Path(os.getenv("APPDATA")) / "QuickChat" if os.getenv("APPDATA") else Path.home() / "AppData" / "Local" / "QuickChat"
else:
    # Linux/macOS: Use ~/.quickchat
    DATA_DIR = Path.home() / ".quickchat"

DB_PATH = DATA_DIR / "quickchat.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True, parents=True)

# Database
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ollama Defaults
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "llama3" # Or whatever is popular/available
REQUEST_TIMEOUT = 30.0

# UI Defaults
WINDOW_TITLE = "QuickChat"
WINDOW_SIZE = (1200, 800)
THEME_MODE = "dark"
