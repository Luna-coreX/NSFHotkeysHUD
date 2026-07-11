from pathlib import Path
import os

APPDATA_DIR = Path(os.getenv("APPDATA")) / "NSFHotkeysHUD"

APPDATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE = APPDATA_DIR / "hotkeys.json"
THEME_FILE = APPDATA_DIR / "theme.json"
STATE_FILE = APPDATA_DIR / "hud_station.json"
ICONS_DIR = APPDATA_DIR / "icons"
