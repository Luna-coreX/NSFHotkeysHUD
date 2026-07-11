import keyboard
import json
import threading
import time
from paths import  CONFIG_FILE

# простой способ связать клавиши с именами
KEY_MAP = {
    "win": "win",
    "ctrl": "ctrl",
    "shift": "shift",
    "numpad 3": "num3",
    "p": "p"
}

def normalize(keys):
    keys = keys.lower()
    parts = keys.split("+")
    return "+".join([p.strip() for p in parts])


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main(hud):
    config = load_config()

    def on_hotkey(hotkey):
        print("Pressed:", hotkey)
        hud.trigger(hotkey)

    for hk in config.keys():
        keyboard.add_hotkey(hk.lower(), lambda hk=hk: on_hotkey(hk))

    keyboard.wait()


def run_listener(hud):
    t = threading.Thread(target=main, args=(hud,), daemon=True)
    t.start()