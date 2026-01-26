import json
import os
import threading
import time

STATE_FILE = "system_state.json"
LOCK = threading.Lock()

# Global in-memory state for fast access, synced to disk on change
_STATE = {
    "is_running": False,
    "log_history": "",
    "progress": 0,
    "status_message": "",
    "gallery_files": [],
    "stop_requested": False
}

def load_state():
    """Loads state from disk if exists, else returns default"""
    global _STATE
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Merge with default to ensure all keys exist
                for k, v in loaded.items():
                    _STATE[k] = v
        except Exception as e:
            print(f"Erro ao carregar estado: {e}")
    return _STATE

def save_state():
    """Saves current state to disk"""
    with LOCK:
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(_STATE, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Erro ao salvar estado: {e}")

def get_state():
    """Returns a copy of the current state"""
    with LOCK:
        return _STATE.copy()

def update_state(key, value):
    """Updates a specific key in the state and saves to disk"""
    with LOCK:
        _STATE[key] = value
    save_state()

def append_log(message):
    """Appends a message to the log history"""
    with LOCK:
        _STATE["log_history"] = message + "\n" + _STATE["log_history"]
    save_state()

def set_running(running):
    update_state("is_running", running)
    if not running:
        update_state("stop_requested", False) # Reset stop flag when stopped

def request_stop():
    update_state("stop_requested", True)

def check_stop_requested():
    with LOCK:
        return _STATE.get("stop_requested", False)

def clear_state():
    """Resets the state to default"""
    global _STATE
    with LOCK:
        _STATE = {
            "is_running": False,
            "log_history": "",
            "progress": 0,
            "status_message": "",
            "gallery_files": [],
            "stop_requested": False
        }
    save_state()

# Initialize on load
load_state()

# Safety Check: If app restarted but state says running, it means it crashed/stopped previously.
# We must reset the running flag because the thread is definitely dead now.
if _STATE["is_running"]:
    _STATE["is_running"] = False
    _STATE["log_history"] += "\n⚠️ [SISTEMA REINICIADO] O processo anterior foi interrompido.\n"
    save_state()
