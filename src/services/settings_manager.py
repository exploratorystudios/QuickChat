import json
from pathlib import Path
from config.settings import DATA_DIR

SETTINGS_FILE = DATA_DIR / "user_settings.json"

DEFAULT_SETTINGS = {
    "theme": "dark",
    "default_model": "llama3",
    "font_size": 14,
    "enter_to_send": True
}

class SettingsManager:
    def __init__(self):
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from JSON file or return defaults."""
        if not SETTINGS_FILE.exists():
            return DEFAULT_SETTINGS.copy()
        
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save current settings to JSON file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value and save."""
        self.settings[key] = value
        self.save_settings()

# Global instance
settings_manager = SettingsManager()
