"""config_manager.py — API key configuration, tasks & notes persistence manager."""
import sys
import json
import time
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"
MEMORY_DIR = BASE_DIR / "memory"

def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def is_configured() -> bool:
    try:
        if not config_exists():
            return False
        keys = load_api_keys()
        return bool(keys.get("gemini_api_key"))
    except Exception:
        return False

def load_api_keys() -> dict[str, str]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_api_keys(keys: dict[str, str]) -> None:
    ensure_config_dir()
    CONFIG_FILE.write_text(json.dumps(keys, indent=2), encoding="utf-8")

def get_gemini_key() -> str:
    return load_api_keys().get("gemini_api_key", "")

_TASKS_FILE = MEMORY_DIR / "tasks.json"
_NOTES_FILE = MEMORY_DIR / "notes.json"

def ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

def load_tasks() -> list[dict]:
    if not _TASKS_FILE.exists():
        return []
    try:
        return json.loads(_TASKS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_tasks(tasks: list[dict]) -> None:
    ensure_memory_dir()
    _TASKS_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

def load_notes_text() -> str:
    if not _NOTES_FILE.exists():
        return ""
    try:
        return _NOTES_FILE.read_text(encoding="utf-8")
    except Exception:
        return ""

def save_notes_text(text: str) -> None:
    ensure_memory_dir()
    _NOTES_FILE.write_text(text, encoding="utf-8")


# ── Agent configs (API keys + models per provider) ────────────────────────────
_AGENTS_FILE = CONFIG_DIR / "agents.json"

def load_agent_configs() -> dict:
    """Returns {provider_key: {"api_key": str, "model": str}, ...}"""
    if not _AGENTS_FILE.exists():
        return {}
    try:
        return json.loads(_AGENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_agent_configs(configs: dict) -> None:
    ensure_config_dir()
    _AGENTS_FILE.write_text(json.dumps(configs, indent=2), encoding="utf-8")
