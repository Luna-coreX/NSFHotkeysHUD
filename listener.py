"""
Global hotkey listener.

Registers every hotkey from the config with the `keyboard` library and
calls hud.trigger() when one fires. The set of hotkeys can be re-registered
at any time via reload_hotkeys() - the HUD calls this after every add / edit /
delete so config changes take effect without restarting the app.
"""

import keyboard
import json
import threading

from paths import CONFIG_FILE

# The HUD instance to notify when a hotkey fires - set once in run_listener().
_hud = None

# Serializes clear + re-register so a reload triggered from the GUI thread
# can't interleave with itself.
_lock = threading.Lock()


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _on_hotkey(hotkey):
    if _hud is not None:
        _hud.trigger(hotkey)


def _register_all():
    """(Re)register every hotkey in the current config. Each registration is
    guarded individually so one unmappable combo (e.g. a key name the
    `keyboard` library doesn't recognize) can't abort the whole set."""
    config = load_config()

    for hk in config.keys():
        try:
            keyboard.add_hotkey(hk.lower(), lambda hk=hk: _on_hotkey(hk))
        except Exception as e:
            print(f"[listener] Could not register hotkey '{hk}': {e}")


def reload_hotkeys():
    """Clear all currently registered hotkeys and re-register from the config
    file on disk. Safe to call from any thread."""
    with _lock:
        try:
            keyboard.clear_all_hotkeys()
        except Exception:
            # Nothing registered yet (or the backend has none) - fine.
            pass
        _register_all()


def _run(hud):
    global _hud
    _hud = hud
    reload_hotkeys()
    keyboard.wait()


def run_listener(hud):
    threading.Thread(target=_run, args=(hud,), daemon=True).start()
