import json
import os
import locale
from .config_manager import ConfigManager

class TranslationManager:
    _instance = None
    _translations = {}
    _language = "it"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if TranslationManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            TranslationManager._instance = self
            self.load_language()

    def load_language(self):
        config_mgr = ConfigManager()
        
        # Check if language is explicitly set in config
        if "language" in config_mgr.config:
            self._language = config_mgr.config["language"]
        else:
            # Auto-detect from system
            try:
                sys_lang, _ = locale.getdefaultlocale()
                # If system is English (en_US, en_GB, etc.), default to 'en'
                if sys_lang and sys_lang.lower().startswith("en"):
                    self._language = "en"
                else:
                    self._language = "it"
            except:
                self._language = "it" # Fallback
        
        # Load JSON
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_path, "i18n", f"{self._language}.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self._translations = json.load(f)
            except Exception as e:
                print(f"Error loading translations for {self._language}: {e}")
                self._translations = {}
        else:
            print(f"Translation file not found: {json_path}")
            # Fallback to empty, user will see keys if we don't handle missing gracefully
            self._translations = {}

    def tr(self, key):
        """Returns the translated string for the given key, or the key itself if not found."""
        return self._translations.get(key, key)

# Global helper
_tm = None
def tr(key):
    global _tm
    if _tm is None:
        _tm = TranslationManager.get_instance()
    return _tm.tr(key)
