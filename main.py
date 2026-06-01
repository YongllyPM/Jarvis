import os
import json
import sys
from pathlib import Path

# ── Fix SSL cert path for moved/copied environments ──
try:
    import certifi
    _cert_path = certifi.where()
    if _cert_path and os.path.isfile(_cert_path):
        os.environ.setdefault("SSL_CERT_FILE", _cert_path)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", _cert_path)
except Exception:
    # Fallback: search common locations
    for _p in [Path(__file__).resolve().parent / ".venv" / "Lib" / "site-packages" / "certifi" / "cacert.pem",
               Path(sys.prefix) / "Lib" / "site-packages" / "certifi" / "cacert.pem"]:
        if _p.exists():
            os.environ.setdefault("SSL_CERT_FILE", str(_p))
            os.environ.setdefault("REQUESTS_CA_BUNDLE", str(_p))
            break

# Load config early to determine GPU acceleration settings
_gpu_enabled = False
try:
    if getattr(sys, "frozen", False):
        _base_dir = Path(sys.executable).parent
    else:
        _base_dir = Path(__file__).resolve().parent
    _cfg_path = _base_dir / "config" / "api_keys.json"
    if _cfg_path.exists():
        _cfg = json.loads(_cfg_path.read_text(encoding="utf-8"))
        _gpu_enabled = _cfg.get("gpu_acceleration", False)
except Exception:
    pass

if _gpu_enabled:
    # GPU / High Performance Mode: sustain rendering workload on GPU VRAM, maximize space size
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--ignore-gpu-blocklist "
        "--enable-gpu-rasterization "
        "--enable-zero-copy "
        "--num-raster-threads=4 "
        "--js-flags=--max-old-space-size=1024"
    )
    # Enable hardware acceleration backends for Qt
    os.environ["QSG_RHI_BACKEND"] = "d3d11" # Force Direct3D 11 for hardware rendering on Windows
    os.environ["QSG_INFO"] = "1"
    print("[JARVIS] GPU Acceleration is ENABLED. Offloading RAM rendering workload to GPU.")
else:
    # Balanced low-RAM mode: Keep GPU hardware compositing enabled so glowing CSS effects and drop-shadows are rendered beautifully, but limit renderer processes and JS space size.
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--enable-low-end-device-mode "
        "--renderer-process-limit=1 "
        "--js-flags=--max-old-space-size=64 "
        "--disable-gpu-shader-disk-cache "
        "--disable-dev-shm-usage "
        "--disable-extensions "
        "--disable-sync "
        "--mute-audio"
    )
    print("[JARVIS] Using Balanced Low RAM GPU-Composited mode for beautiful fluid rendering.")

import asyncio
from concurrent.futures import ThreadPoolExecutor
from beta_config import is_pro_tool, check_daily_limit, increment_calls, pro_tool_message, daily_limit_message
import re
import threading
import json
import sys
try:
    import pygetwindow as gw
except ImportError:
    gw = None
from PyQt6.QtCore import QMetaObject, Qt, QTimer

import traceback
from pathlib import Path

# ── Dedicated thread pool for tool execution — prevents starvation ────────────
_TOOL_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="jarvis-tool")

try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _BA_TZ = _ZoneInfo("UTC")
except Exception:
    from datetime import timezone as _tz, timedelta as _td
    _BA_TZ = _tz.utc


def _load_tz():
    """Auto-detect timezone from system and location via IP."""
    global _BA_TZ
    from datetime import datetime as _dt
    _BA_TZ = _dt.now().astimezone().tzinfo
    tz_name = str(_BA_TZ)
    print(f"[TZ] System timezone: {tz_name}")

    # Auto-detect city via IP geolocation
    city = ""
    try:
        import requests
        resp = requests.get("http://ip-api.com/json/?fields=city,timezone", timeout=5)
        if resp.ok:
            data = resp.json()
            if data.get("timezone"):
                _BA_TZ = _ZoneInfo(data["timezone"])
                tz_name = data["timezone"]
                print(f"[TZ] Geolocation timezone: {tz_name}")
            city = data.get("city", "")
    except Exception:
        pass

    # Save detected timezone + city to config so settings UI reflects them
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    changed = False
    if not cfg.get("timezone"):
        cfg["timezone"] = tz_name
        changed = True
    if city and not cfg.get("ubicacion"):
        cfg["ubicacion"] = city
        changed = True
    if changed:
        API_CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI, TutorialOverlay

def _patch_settings_ui():
    pass

_patch_settings_ui()

from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

try:
    from actions.file_processor import file_processor
except ImportError:
    file_processor = None
try:
    from actions.flight_finder     import flight_finder
except ImportError:
    flight_finder = None
try:
    from actions.open_app          import open_app
except ImportError:
    open_app = None
try:
    from actions.weather_report    import weather_action
except ImportError:
    weather_action = None
try:
    from actions.send_message      import send_message
except ImportError:
    send_message = None
try:
    from actions.reminder          import reminder
except ImportError:
    reminder = None
try:
    from actions.computer_settings import computer_settings
except ImportError:
    computer_settings = None
try:
    from actions.screen_vision import screen_vision
except ImportError:
    screen_vision = None
try:
    from actions.youtube_video     import youtube_video
except ImportError:
    youtube_video = None
try:
    from actions.desktop           import desktop_control
except ImportError:
    desktop_control = None
try:
    from actions.browser_control   import browser_control
except ImportError:
    browser_control = None
try:
    from actions.visual_click import visual_click
except ImportError:
    visual_click = None
try:
    from actions.file_controller   import file_controller
except ImportError:
    file_controller = None
try:
    from actions.code_helper       import code_helper
except ImportError:
    code_helper = None
try:
    from actions.dev_agent         import dev_agent
except ImportError:
    dev_agent = None
try:
    from actions.web_search        import web_search as web_search_action
except ImportError:
    web_search_action = None
try:
    from actions.computer_control  import computer_control
except ImportError:
    computer_control = None
try:
    from actions.game_updater      import game_updater
except ImportError:
    game_updater = None
try:
    from actions.google_calendar   import google_calendar
except ImportError:
    google_calendar = None
try:
    from actions.music_controller  import music_control as music_control_func
except ImportError:
    music_control_func = None
try:
    from actions.rgb_control       import rgb_control
except ImportError:
    rgb_control = None
try:
    from actions.scheduler         import scheduler, start_runner
except ImportError:
    scheduler = None; start_runner = None
try:
    from actions.google_drive      import google_drive
except ImportError:
    google_drive = None
try:
    from actions.gmail_control     import gmail_control
except ImportError:
    gmail_control = None
try:
    from actions.google_maps       import google_maps
except ImportError:
    google_maps = None
try:
    from actions.rules_engine      import rules_engine, start_rules_runner, check_phrase_triggers, _run_action as _rules_run_action
except ImportError:
    rules_engine = None; start_rules_runner = None; check_phrase_triggers = None; _rules_run_action = None
try:
    from actions.social_media      import social_media
except ImportError:
    social_media = None
try:
    from actions.whatsapp          import whatsapp
except ImportError:
    whatsapp = None
try:
    from actions.user_profile      import user_profile, record_action
except ImportError:
    user_profile = None; record_action = None
try:
    from actions.goals             import goals
except ImportError:
    goals = None
try:
    from actions.git_control       import git_control
except ImportError:
    git_control = None
try:
    from actions.codebase          import codebase
except ImportError:
    codebase = None
try:
    from actions.knowledge_base    import knowledge_base
except ImportError:
    knowledge_base = None
try:
    from actions.windows_settings  import windows_settings
except ImportError:
    windows_settings = None
try:
    from actions.document_creator  import document_creator
except ImportError:
    document_creator = None
try:
    from actions.document_manager  import document_manager
except ImportError:
    document_manager = None
try:
    from actions.web_navigation    import web_navigation
except ImportError:
    web_navigation = None
try:
    from actions.image_generation  import image_generation
except ImportError:
    image_generation = None
try:
    from actions.smart_home        import smart_home
except ImportError:
    smart_home = None
try:
    from actions.system_monitor    import system_monitor
except ImportError:
    system_monitor = None
try:
    from actions.tiktok_analyzer   import tiktok_analyzer
except ImportError:
    tiktok_analyzer = None
try:
    from actions.arca_invoice      import arca_invoice
except ImportError:
    arca_invoice = None
try:
    from actions.terminal_agent    import terminal_agent
except ImportError:
    terminal_agent = None
try:
    from actions.native_ui         import native_ui
except ImportError:
    native_ui = None
try:
    from actions.accessibility          import accessibility, eye_tracking, micro_movement, task_simplify, routine_gamify
except ImportError:
    accessibility = None
    eye_tracking = None
    micro_movement = None
    task_simplify = None
    routine_gamify = None
try:
    from actions.screen_reader          import screen_reader
except ImportError:
    screen_reader = None
try:
    from actions.accessibility_overlay  import accessibility_overlay
except ImportError:
    accessibility_overlay = None
try:
    from actions.morning_brief     import morning_brief, already_briefed_today, mark_briefed
except ImportError:
    morning_brief = None; already_briefed_today = None; mark_briefed = None
try:
    from actions.vision_guardian   import vision_guardian, start as _start_vision_guardian
except ImportError:
    vision_guardian = None; _start_vision_guardian = None
try:
    from actions.openrouter_agent  import openrouter_agent
except ImportError:
    openrouter_agent = None
try:
    from actions.scenes            import scenes_control
except ImportError:
    scenes_control = None
try:
    from actions.screen_reader     import screen_reader
except ImportError:
    screen_reader = None



def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LOG_PATH        = BASE_DIR / "jarvis.log"

# ── Redirect output to log file (pythonw.exe has no console) ─
try:
    import io as _io
    _log_fh = open(LOG_PATH, "w", encoding="utf-8", buffering=1)

    class _TeeStream:
        def __init__(self, *streams):
            self._streams = [s for s in streams if s is not None]
        def write(self, data):
            for s in self._streams:
                try: s.write(data)
                except Exception: pass
        def flush(self):
            for s in self._streams:
                try: s.flush()
                except Exception: pass
        @property
        def encoding(self): return "utf-8"
        def fileno(self): raise _io.UnsupportedOperation("fileno")

    sys.stdout = _TeeStream(sys.stdout, _log_fh)
    sys.stderr = _TeeStream(sys.stderr, _log_fh)
except Exception:
    pass

# ── Suppress console windows from all child subprocesses ─────────────────────
if sys.platform == "win32":
    try:
        import ctypes as _ctypes
        if _ctypes.windll.kernel32.GetConsoleWindow() == 0:
            import subprocess as _sp
            _CREATE_NO_WINDOW = 0x08000000
            _orig_Popen = _sp.Popen
            class _NoCmdPopen(_orig_Popen):
                def __init__(self, *args, **kwargs):
                    kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
                    super().__init__(*args, **kwargs)
            _sp.Popen = _NoCmdPopen
            print("[JARVIS] subprocess.Popen patched: CREATE_NO_WINDOW active")
    except Exception as _e:
        print(f"[JARVIS] Could not patch subprocess: {_e}")

LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 256      # 16ms chunks — mic input (keep small for low latency)
PLAY_CHUNK_SIZE     = 480      # 20ms chunks — playback (smaller = lower latency)

_cached_api_key: str | None = None

def _get_api_key() -> str:
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cached_api_key = json.load(f)["gemini_api_key"]
    return _cached_api_key


JARVIS_VOICES = {
    "Aoede":  ("Femenina", "Cálida y sofisticada — ideal para asistente IA"),
    "Kore":   ("Femenina", "Suave y precisa"),
    "Leda":   ("Femenina", "Natural y fluida"),
    "Zephyr": ("Femenina", "Dinámica y expresiva"),
    "Charon": ("Masculina", "Profunda y seria — voz original de JARVIS"),
    "Puck":   ("Masculina", "Ágil y versátil"),
    "Fenrir": ("Masculina", "Grave y autoritaria"),
    "Orus":   ("Masculina", "Clásica y equilibrada"),
}

def _get_jarvis_voice() -> str:
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("jarvis_voice", "Aoede")
    except Exception:
        return "Aoede"


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

TOOL_DECLARATIONS = [
    {
        "name": "jarvis_ui_control",
        "description": (
            "Control total sobre la ventana principal y los widgets de la interfaz de JARVIS. "
            "Permite minimizar/restaurar la ventana principal, o abrir, cerrar, alternar la visibilidad de cualquier widget del dashboard.\n"
            "Widgets disponibles: weather (clima), music (música), system (sistema), "
            "notes (notas), todo (tareas), maps (mapas), image (imágenes), camera (cámara)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "minimize (minimizar ventana) | restore (restaurar ventana) | show (mostrar widget) | hide (ocultar widget) | hide_all (ocultar todos los widgets) | toggle (alternar widget)"
                },
                "widget": {
                    "type": "STRING",
                    "description": "Nombre del widget (solo para show/hide/toggle): weather | music | system | notes | todo | maps | image | camera"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "whatsapp",
        "description": (
            "Integración completa con WhatsApp. "
            "SIEMPRE usar para CUALQUIER pedido de WhatsApp: enviar mensajes, "
            "enviar imágenes/archivos, leer conversaciones, ver mensajes sin leer, "
            "guardar/listar contactos con su número de teléfono. "
            "Para enviar, primero verificar si el contacto está guardado con su teléfono. "
            "Si no está, pedir el número al usuario o usar add_contact primero."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "send | send_image | read | unread | add_contact | list_contacts | delete_contact"},
                "receiver":  {"type": "STRING",  "description": "Nombre del contacto o número de teléfono con código de país (ej: 5491155551234)"},
                "message":   {"type": "STRING",  "description": "Texto del mensaje a enviar"},
                "image_path":{"type": "STRING",  "description": "Ruta de la imagen para send_image"},
                "caption":   {"type": "STRING",  "description": "Descripción de la imagen (opcional)"},
                "count":     {"type": "INTEGER", "description": "Cantidad de mensajes a leer (default: 10)"},
                "name":      {"type": "STRING",  "description": "Nombre del contacto para add_contact/delete_contact"},
                "phone":     {"type": "STRING",  "description": "Número de teléfono con código de país (ej: 5491155551234) para add_contact"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via Telegram, Discord, Signal or other messaging platform. For WhatsApp, use the 'whatsapp' tool instead.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: Telegram, Discord, Signal, Messenger (NOT WhatsApp — use whatsapp tool)"}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": (
            "Crea un recordatorio con lenguaje natural. "
            "Ejemplos: 'recordáme en 20 minutos X', 'en 1 hora Y', 'a las 3pm Z', 'en 30s comprar pan'. "
            "Siempre usa el parámetro time_str para el tiempo en lenguaje natural."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "time_str": {"type": "STRING", "description": "Tiempo en lenguaje natural: 'en 20 minutos', 'en 1 hora', 'a las 3pm', 'en 30s'"},
                "message":  {"type": "STRING", "description": "Texto del recordatorio"}
            },
            "required": ["time_str", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task. "
            "IMPORTANT: to type text, MUST use action='type' and value='<text>'. "
            "IMPORTANT: to minimize windows, MUST use action='minimize'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controla el navegador activo del usuario (Chrome, Edge, Firefox, etc.) sin abrir uno nuevo. "
            "Usa esta herramienta cuando el usuario te pida interactuar con la web. "
            "Acciones soportadas: navegar a una URL, buscar en Google, abrir o cerrar pestañas, y scrollear."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "Acciones permitidas: go_to | search | new_tab | close_tab | scroll"},
                "url":         {"type": "STRING", "description": "URL para las acciones go_to o new_tab"},
                "query":       {"type": "STRING", "description": "Término de búsqueda para la acción search"},
                "direction":   {"type": "STRING", "description": "Dirección de scroll: up | down (solo para scroll)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "visual_click",
        "description": "Utiliza Visión Espacial para encontrar las coordenadas matemáticas de un elemento en la pantalla y hacer clic en él físicamente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "element_description": {"type": "STRING", "description": "Descripción clara de lo que quieres cliquear (ej: 'botón de enviar', 'ícono de la papelera')."}
            },
            "required": ["element_description"]
        }
    },
    {
        "name": "sleep_mode",
        "description": "Entra en modo suspensión. Desactiva el micrófono para la IA hasta que el usuario diga 'Oye JARVIS' o 'JARVIS' localmente.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "file_controller",
        "description": (
            "Manages files and folders: list, create, delete (to recycle bin), move, copy, rename, read, write, find, disk usage. "
            "Use action=find with name + path to locate files by name in any directory (desktop, downloads, etc.). "
            "After finding a file, pass the returned path to another tool to act on it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete (mueve a papelera) | move | copy | rename | read | write | edit | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
                "old_text":    {"type": "STRING",  "description": "Texto a reemplazar (para edit)"},
                "new_text":    {"type": "STRING",  "description": "Nuevo texto o contenido (para edit)"},
                "mode":        {"type": "STRING",  "description": "replace | append | prepend | overwrite (para edit)"},
                "confirm":     {"type": "BOOLEAN", "description": "true para confirmar eliminaciones"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": (
            "Controls the desktop: wallpaper, organize, clean, list, stats. "
            "When the user says to use a file from a directory (e.g. 'el archivo X del escritorio'), "
            "use search_name + search_path to auto-find the file before applying the action."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":        {"type": "STRING", "description": "Image path for wallpaper"},
                "url":         {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":        {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":        {"type": "STRING", "description": "Natural language desktop task"},
                "search_name": {"type": "STRING", "description": "Filename to search for in a directory (auto-finds full path)"},
                "search_path": {"type": "STRING", "description": "Directory to search: desktop, downloads, documents, pictures, home (default: desktop)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_jarvis",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Jarvis. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "google_calendar",
        "description": (
            "Manages the user's Google Calendar: create, list, edit, or delete events. "
            "Use for ANY request about calendar events, appointments, reminders with dates, "
            "scheduling meetings, or checking what's coming up. "
            "ALWAYS call this tool for calendar requests — never simulate. "
            "For 'list': shows upcoming events. "
            "For 'create': needs summary and start (end defaults to +1h). "
            "For 'edit'/'delete': needs event_id (get it from 'list' first)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "list | create | edit | delete"},
                "summary":     {"type": "STRING",  "description": "Event title/name"},
                "start":       {"type": "STRING",  "description": "Start date/time: ISO, YYYY-MM-DD HH:MM, or DD/MM/YYYY HH:MM"},
                "end":         {"type": "STRING",  "description": "End date/time (optional — defaults to start + 1 hour)"},
                "description": {"type": "STRING",  "description": "Event notes or description"},
                "location":    {"type": "STRING",  "description": "Event location"},
                "event_id":    {"type": "STRING",  "description": "Event ID (first 8 chars from list) for edit/delete"},
                "days_ahead":  {"type": "INTEGER", "description": "Days to look ahead for list (default: 7)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "music_control",
        "description": (
            "Control total de música: reproducir, pausar, siguiente, anterior, volumen, "
            "buscar canciones/artistas/álbumes/playlists según la plataforma activa "
            "(Spotify o YouTube Music, configurable en Ajustes > Plataforma de Música). "
            "SIEMPRE llamar esta herramienta para CUALQUIER pedido relacionado con música."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | pause | resume | next | previous | volume | shuffle | repeat | current | search | like | devices | playlist"},
                "query":  {"type": "STRING", "description": "Búsqueda para play/search: canción, artista, álbum o playlist"},
                "type":   {"type": "STRING", "description": "track | album | playlist | artist (default: track)"},
                "value":  {"type": "STRING", "description": "Valor para volume (0-100), shuffle (true/false), repeat (off/track/context)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "rgb_control",
        "description": (
            "Controla las luces RGB de periféricos y componentes de la PC (teclado, mouse, GPU, RAM, etc.). "
            "Requiere OpenRGB corriendo con servidor SDK activado. "
            "Usar para: cambiar color, apagar, brillo, efectos, arco iris."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "set_color | off | brightness | effect | rainbow | list"},
                "color":      {"type": "STRING", "description": "Color: nombre (rojo, azul, verde, blanco…) o hex #RRGGBB"},
                "brightness": {"type": "INTEGER", "description": "Brillo 0-100 (default: 100)"},
                "device":     {"type": "STRING", "description": "Filtro por nombre de dispositivo (opcional, aplica a todos si se omite)"},
                "effect":     {"type": "STRING", "description": "Nombre del efecto para la acción effect"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "scheduler",
        "description": (
            "Crea, lista, elimina o ejecuta automatizaciones programadas (tareas recurrentes). "
            "Ejemplos: backup diario, notificaciones, scripts automáticos. "
            "Usar para CUALQUIER pedido de 'todos los días a las X', 'cada semana', 'automatizar'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":           {"type": "STRING",  "description": "list | create | delete | enable | disable | run_now"},
                "name":             {"type": "STRING",  "description": "Nombre descriptivo de la tarea"},
                "frequency":        {"type": "STRING",  "description": "daily | weekly | interval | once"},
                "hour":             {"type": "INTEGER", "description": "Hora de ejecución (0-23)"},
                "minute":           {"type": "INTEGER", "description": "Minuto de ejecución (0-59)"},
                "weekday":          {"type": "STRING",  "description": "Día de la semana para frequency=weekly"},
                "interval_minutes": {"type": "INTEGER", "description": "Intervalo en minutos para frequency=interval"},
                "task_action":      {"type": "STRING",  "description": "backup | file_controller | notify | custom_script | browser_control"},
                "task_parameters":  {"type": "OBJECT",  "description": "Parámetros de la tarea (source, destination para backup, etc.)"},
                "task_id":          {"type": "STRING",  "description": "ID de la tarea (primeros 6 chars) para delete/enable/disable/run_now"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "google_drive",
        "description": (
            "Gestiona Google Drive: listar archivos, buscar, subir, descargar, crear carpetas, eliminar, compartir. "
            "SIEMPRE usar para cualquier pedido sobre Google Drive."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | search | upload | download | create_folder | delete | share | info"},
                "folder_id":   {"type": "STRING", "description": "ID de la carpeta (default: root)"},
                "file_id":     {"type": "STRING", "description": "ID del archivo para download/delete/share/info"},
                "path":        {"type": "STRING", "description": "Ruta local para upload"},
                "name":        {"type": "STRING", "description": "Nombre de la nueva carpeta"},
                "query":       {"type": "STRING", "description": "Término de búsqueda"},
                "destination": {"type": "STRING", "description": "Carpeta local de destino para download"},
                "email":       {"type": "STRING", "description": "Email para compartir"},
                "role":        {"type": "STRING", "description": "reader | writer | commenter"},
                "confirm":     {"type": "BOOLEAN", "description": "true para confirmar eliminación"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "gmail_control",
        "description": (
            "Gestiona Gmail: leer bandeja, leer correo, enviar, responder, buscar, archivar, eliminar. "
            "SIEMPRE usar para cualquier pedido sobre correo electrónico o Gmail."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING",  "description": "inbox | read | send | reply | search | archive | delete | mark_read | labels"},
                "count":      {"type": "INTEGER", "description": "Cantidad de correos a listar/buscar (default: 5)"},
                "message_id": {"type": "STRING",  "description": "ID del mensaje para read/reply/archive/delete/mark_read"},
                "to":         {"type": "STRING",  "description": "Destinatario para send"},
                "subject":    {"type": "STRING",  "description": "Asunto para send"},
                "body":       {"type": "STRING",  "description": "Cuerpo del correo para send/reply"},
                "query":      {"type": "STRING",  "description": "Búsqueda Gmail para search (ej: 'from:juan', 'subject:factura')"},
                "confirm":    {"type": "BOOLEAN", "description": "true para confirmar eliminación"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "google_maps",
        "description": (
            "Muestra rutas de navegación y mapas interactivos. "
            "Usar para: cómo llegar a un lugar, cuánto tarda, indicaciones paso a paso, "
            "buscar una dirección en el mapa. Abre mapa JARVIS en Chrome con la ruta marcada. "
            "SIEMPRE llamar para cualquier pedido de navegación, rutas o mapas."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "directions | search"},
                "origin":      {"type": "STRING", "description": "Punto de partida (dirección, ciudad, lugar)"},
                "destination": {"type": "STRING", "description": "Destino (dirección, ciudad, lugar)"},
                "mode":        {"type": "STRING", "description": "car (auto) | walk (caminando) | bike (bicicleta). Default: car"},
                "query":       {"type": "STRING", "description": "Lugar a buscar en el mapa (para action=search)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "rules_engine",
        "description": (
            "Motor de automatizaciones y alertas inteligentes. "
            "USAR SIEMPRE cuando el usuario pida: 'cuando diga X hacé Y', 'cada vez que diga X', "
            "'si digo X abrí/poné/hacé Y', 'quiero que cuando diga X...'. "
            "Soporta: phrase triggers (frase → acción), time triggers (hora → acción), alertas. "
            "Listar, crear, eliminar, habilitar/deshabilitar automaciones. "
            "CONDITION types: phrase (frase del usuario), time (hora del día), file_exists, always. "
            "ACTION types: open_app, music_play, browser, smart_home, composite (múltiples), notify, speak, run_script."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":     {"type": "STRING", "description": "list | list_phrases | create | delete | enable | disable | trigger | alert"},
                "name":       {"type": "STRING", "description": "Nombre de la automatización"},
                "rule_id":    {"type": "STRING", "description": "ID de la regla para delete/enable/disable/trigger"},
                "condition":  {
                    "type": "OBJECT",
                    "description": (
                        "Condición. phrase: {type:phrase, trigger:'texto exacto', match:contains|exact|startswith}. "
                        "time: {type:time, hour:8, minute:0, days:[monday,...]}. "
                        "file_exists: {type:file_exists, path:'...'}. always: {type:always}"
                    )
                },
                "action_def": {
                    "type": "OBJECT",
                    "description": (
                        "Acción a ejecutar. "
                        "open_app: {type:open_app, app_name:'Spotify'}. "
                        "music_play: {type:music_play, query:'Back in Black AC/DC', platform:'auto'}. "
                        "browser: {type:browser, url:'https://...'}. "
                        "smart_home: {type:smart_home, device:'living', action:'on'}. "
                        "composite: {type:composite, actions:[{...},{...}]}. "
                        "notify: {type:notify, message:'...'}. speak: {type:speak, message:'...'}. "
                        "run_script: {type:run_script, command:'...'}."
                    )
                },
                "message":    {"type": "STRING", "description": "Mensaje para action=alert"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "user_profile",
        "description": (
            "Perfil dinámico del usuario — hábitos, preferencias, historial de uso. "
            "Ver perfil, configurar preferencias, ver hábitos aprendidos, guardar notas personales. "
            "JARVIS aprende automáticamente los patrones del usuario."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "view | set_preference | set_name | add_note | notes | habits | reset"},
                "key":    {"type": "STRING", "description": "Clave de preferencia (ej: idioma, tema, ciudad)"},
                "value":  {"type": "STRING", "description": "Valor de la preferencia"},
                "name":   {"type": "STRING", "description": "Nombre del usuario"},
                "note":   {"type": "STRING", "description": "Nota personal a guardar"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "goals",
        "description": (
            "Sistema de objetivos persistentes a largo plazo. "
            "Crear metas, trackear progreso, marcar pasos completados. "
            "Usar para: metas personales, proyectos, hábitos, objetivos con deadline. "
            "SIEMPRE usar para pedidos de 'quiero lograr X', 'mi objetivo es', 'meta de'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "list | create | update_progress | complete | complete_step | add_step | delete | detail"},
                "goal_id":     {"type": "STRING",  "description": "ID del objetivo para update/complete/delete/detail"},
                "title":       {"type": "STRING",  "description": "Título del objetivo"},
                "description": {"type": "STRING",  "description": "Descripción detallada"},
                "deadline":    {"type": "STRING",  "description": "Fecha límite ISO (YYYY-MM-DD)"},
                "progress":    {"type": "INTEGER", "description": "Progreso 0-100"},
                "steps":       {"type": "ARRAY",   "items": {"type": "STRING"}, "description": "Lista de pasos del objetivo"},
                "step":        {"type": "STRING",  "description": "Texto del nuevo paso (add_step)"},
                "step_index":  {"type": "INTEGER", "description": "Índice del paso a completar (0-based)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "git_control",
        "description": (
            "Integración completa con Git: status, log, diff, commit automático, "
            "branches, pull, push, stash, análisis de cambios. "
            "Usar para CUALQUIER pedido relacionado con Git o control de versiones."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "status | log | diff | commit | add | branches | branch_create | checkout | pull | push | stash | analyze"},
                "repo_path":   {"type": "STRING",  "description": "Ruta al repositorio Git"},
                "message":     {"type": "STRING",  "description": "Mensaje del commit"},
                "branch_name": {"type": "STRING",  "description": "Nombre de la rama"},
                "remote":      {"type": "STRING",  "description": "Remote (default: origin)"},
                "n":           {"type": "INTEGER", "description": "Número de commits para log"},
                "file":        {"type": "STRING",  "description": "Archivo específico para diff"},
                "staged":      {"type": "BOOLEAN", "description": "Mostrar diff staged"},
                "add_all":     {"type": "BOOLEAN", "description": "Agregar todos los archivos antes del commit (default: true)"},
                "files":       {"type": "ARRAY",   "items": {"type": "STRING"}, "description": "Archivos para add"},
                "sub":         {"type": "STRING",  "description": "Subcomando para stash: push|pop|list"},
            },
            "required": ["action", "repo_path"]
        }
    },
    {
        "name": "codebase",
        "description": (
            "Indexación y búsqueda inteligente de proyectos de código. "
            "Indexar proyectos, buscar en archivos, encontrar símbolos (funciones/clases), "
            "generar documentación automática, búsqueda avanzada de código. "
            "Usar para: 'buscar en mi proyecto', 'dónde está la función X', 'generar docs', 'indexar mi código'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "index | list | info | search | find_symbol | generate_docs | remove"},
                "path":      {"type": "STRING", "description": "Ruta del proyecto a indexar"},
                "name":      {"type": "STRING", "description": "Nombre del proyecto (default: nombre de carpeta)"},
                "project":   {"type": "STRING", "description": "Nombre del proyecto para info/search/find_symbol"},
                "query":     {"type": "STRING", "description": "Texto a buscar en el código"},
                "symbol":    {"type": "STRING", "description": "Nombre de función/clase a buscar"},
                "file_path": {"type": "STRING", "description": "Ruta del archivo para generate_docs"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "knowledge_base",
        "description": (
            "Segundo cerebro / base de conocimiento personal. "
            "Guardar notas, ideas, snippets de código, referencias, hechos, preguntas. "
            "Buscar en el conocimiento guardado, exportar. "
            "Usar para: 'recordá que...', 'guardá esta idea', 'anotá este código', 'buscar en mis notas'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING", "description": "add/save/store | search/find | list | get/read/view | update | delete | stats | export"},
                "title":    {"type": "STRING", "description": "Título de la entrada"},
                "content":  {"type": "STRING", "description": "Contenido o texto a guardar"},
                "type":     {"type": "STRING", "description": "note | idea | snippet | reference | fact | task | question"},
                "tags":     {"type": "STRING", "description": "Tags separados por coma (ej: python, jarvis, idea)"},
                "query":    {"type": "STRING", "description": "Búsqueda en la base de conocimiento"},
                "entry_id": {"type": "STRING", "description": "ID de la entrada para get/update/delete"},
                "path":     {"type": "STRING", "description": "Ruta para exportar (action=export)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "social_media",
        "description": (
            "Controla redes sociales: Twitter/X, Instagram, TikTok y LinkedIn. "
            "Twitter: publicar tweets, ver timeline, buscar, like, retweet, ver perfil. "
            "Instagram: publicar fotos, subir historias, enviar DMs, ver feed, like, comentar. "
            "TikTok: subir videos, ver perfil/stats, tendencias. "
            "LinkedIn: publicar posts, ver perfil, ver feed, enviar mensajes. "
            "SIEMPRE usar para cualquier pedido de redes sociales. "
            "Para WhatsApp usar la herramienta 'whatsapp'. "
            "Usá action=setup para ver cómo configurar las credenciales."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {"type": "STRING", "description": "twitter | instagram | tiktok | linkedin | setup"},
                "action":   {"type": "STRING", "description": (
                    "Twitter: tweet, delete_tweet, like, retweet, timeline, search_tweets, my_tweets, profile | "
                    "Instagram: post/upload_photo, story, send_dm, feed, profile, like, comment | "
                    "TikTok: upload/publicar, profile/perfil, trending | "
                    "LinkedIn: post/publicar, profile/perfil, send_message/mensaje, feed"
                )},
                "text":       {"type": "STRING", "description": "Texto del tweet/post/comentario/mensaje"},
                "content":    {"type": "STRING", "description": "Contenido del post (LinkedIn/TikTok)"},
                "tweet_id":   {"type": "STRING", "description": "ID del tweet para like/retweet/delete"},
                "media_id":   {"type": "STRING", "description": "ID del post de Instagram para like/comment"},
                "username":   {"type": "STRING", "description": "Usuario para DM/perfil (Instagram, TikTok, LinkedIn)"},
                "receiver":   {"type": "STRING", "description": "Destinatario del DM de Instagram"},
                "image_path": {"type": "STRING", "description": "Ruta imagen para Instagram/LinkedIn"},
                "video_path": {"type": "STRING", "description": "Ruta del video para TikTok"},
                "caption":    {"type": "STRING", "description": "Descripción/caption de la foto o video"},
                "query":      {"type": "STRING", "description": "Búsqueda de tweets"},
                "count":      {"type": "INTEGER", "description": "Cantidad de resultados (default: 5)"},
            },
            "required": ["platform", "action"]
        }
    },
    {
        "name": "windows_settings",
        "description": (
            "Control TOTAL de configuraciones de Windows. "
            "Usar para CUALQUIER pedido relacionado con configuración del sistema. "
            "Categorías disponibles:\n"
            "• display: brillo, resolución, frecuencia, escala, modo oscuro/noche, HDR, orientación, monitores\n"
            "• audio: volumen, mute, dispositivos de audio/micrófono, mezclador\n"
            "• network: WiFi (listar/conectar/desconectar/on/off), IP, DNS, flush_dns, modo avión, Bluetooth, proxy\n"
            "• power: plan energía, suspender, hibernar, batería, timeouts, inicio rápido\n"
            "• system: info del sistema, nombre PC, fecha/hora, zona horaria, reiniciar, apagar, bloquear, variables de entorno\n"
            "• personalization: fondo de pantalla, tema, transparencia, barra de tareas, protector de pantalla\n"
            "• apps: listar apps, desinstalar, apps de inicio, aplicaciones predeterminadas\n"
            "• security: Windows Defender, firewall, UAC, BitLocker, usuarios del sistema\n"
            "• input: velocidad mouse, doble clic, scroll, botones, velocidad teclado, idioma\n"
            "• storage: discos, espacio, limpieza de archivos temporales, papelera, defrag, chkdsk\n"
            "• services: listar/iniciar/detener/reiniciar servicios de Windows, procesos, kill\n"
            "• privacy: cámara/micrófono privacidad, ubicación, telemetría, notificaciones, portapapeles\n"
            "• registry: leer, escribir, eliminar claves del registro, exportar\n"
            "• accessibility: lupa, narrador, alto contraste, teclado en pantalla\n"
            "• open_settings: abrir panel específico de Configuración de Windows\n"
            "SIEMPRE llamar para cualquier pedido de configuración, ajuste o control del sistema Windows."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "La acción a realizar. Ejemplos por categoría:\n"
                        "display: get_brightness | set_brightness | get_resolution | set_resolution | "
                        "set_refresh_rate | get_scaling | set_scaling | night_light_on | night_light_off | "
                        "hdr_on | hdr_off | set_orientation | list_monitors | open\n"
                        "audio: get_volume | set_volume | mute | unmute | toggle_mute | list_devices | "
                        "set_device | get_mic_volume | set_mic_volume | open\n"
                        "network: list_wifi | connect_wifi | disconnect_wifi | wifi_on | wifi_off | "
                        "get_ip | set_dns | flush_dns | airplane_on | airplane_off | "
                        "bluetooth_on | bluetooth_off | set_proxy | disable_proxy | open\n"
                        "power: get_plan | set_plan | list_plans | sleep | hibernate | battery_status | "
                        "set_sleep_timeout | set_screen_timeout | fast_startup_on | fast_startup_off | open\n"
                        "system: info | get_hostname | set_hostname | get_datetime | set_datetime | "
                        "set_timezone | restart | shutdown | lock | get_env | set_env | delete_env | open\n"
                        "personalization: set_wallpaper | get_wallpaper | dark_mode | light_mode | "
                        "transparency_on | transparency_off | taskbar_position | screensaver | open\n"
                        "apps: list | uninstall | startup_apps | set_default | open\n"
                        "security: defender_scan | defender_status | firewall_on | firewall_off | "
                        "firewall_status | uac_level | bitlocker_status | list_users | add_user | open\n"
                        "input: get_mouse_speed | set_mouse_speed | swap_buttons | get_keyboard_speed | "
                        "set_keyboard_speed | list_languages | add_language | open\n"
                        "storage: list_drives | disk_usage | cleanup | empty_trash | clean_temp | "
                        "defrag | chkdsk | open\n"
                        "services: list | start | stop | restart | status | list_processes | kill_process | open\n"
                        "privacy: camera_on | camera_off | mic_on | mic_off | location_on | location_off | "
                        "telemetry_level | notifications_on | notifications_off | clipboard_history_on | "
                        "clipboard_history_off | open\n"
                        "registry: read | write | delete | export\n"
                        "accessibility: magnifier_on | magnifier_off | narrator_on | narrator_off | "
                        "high_contrast_on | high_contrast_off | osk_on | open\n"
                        "open_settings: <nombre del panel, ej: display, sound, wifi, bluetooth, apps>"
                    )
                },
                "value":    {"type": "STRING",  "description": "Valor para la acción (ej: 80 para brillo, 'Dark' para tema, SSID para wifi, etc.)"},
                "value2":   {"type": "STRING",  "description": "Segundo valor cuando se necesitan dos parámetros (ej: contraseña de WiFi, valor de registro)"},
                "name":     {"type": "STRING",  "description": "Nombre del servicio, proceso, usuario, app, o variable de entorno"},
                "hive":     {"type": "STRING",  "description": "Para registry: HKLM | HKCU | HKCR | HKU | HKCC"},
                "key":      {"type": "STRING",  "description": "Para registry: ruta de la clave del registro"},
                "reg_name": {"type": "STRING",  "description": "Para registry: nombre del valor del registro"},
                "reg_type": {"type": "STRING",  "description": "Para registry: REG_SZ | REG_DWORD | REG_BINARY | REG_EXPAND_SZ"},
                "path":     {"type": "STRING",  "description": "Ruta de archivo (para wallpaper, export registry, etc.)"},
                "monitor":  {"type": "INTEGER", "description": "Índice del monitor (0, 1, 2…)"},
                "width":    {"type": "INTEGER", "description": "Ancho de resolución"},
                "height":   {"type": "INTEGER", "description": "Alto de resolución"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "image_generation",
        "description": (
            "Genera imágenes con inteligencia artificial a partir de una descripción en texto. "
            "Usa Pollinations.ai (gratis, open-source, sin API key) o Gemini. "
            "SIEMPRE llamar cuando el usuario pide 'generame una imagen', 'crea una foto de', "
            "'dibujame', 'haceme una imagen', 'quiero una foto de', o 'mostrame', etc. "
            "Después de generar, la imagen se muestra automáticamente en el widget de JARVIS."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt":       {"type": "STRING",  "description": "Descripción detallada de la imagen a generar"},
                "count":        {"type": "INTEGER", "description": "Cantidad de imágenes (1-4, default: 1)"},
                "aspect_ratio": {"type": "STRING",  "description": "Relación de aspecto: 1:1 | 4:3 | 3:4 | 16:9 | 9:16 (default: 1:1)"},
                "save_path":    {"type": "STRING",  "description": "Carpeta de guardado (default: ~/Pictures/JARVIS_Generadas)"},
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "smart_home",
        "description": (
            "Controla las luces y dispositivos inteligentes del hogar. "
            "Soporta Tuya/Smart Life, Philips Hue, LIFX y Yeelight. "
            "SIEMPRE llamar para: encender/apagar luces, cambiar color, brillo, temperatura de color, "
            "activar escenas, consultar estado. "
            "Si no hay dispositivos configurados, usar action=setup para ver instrucciones."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING",  "description": "on | off | toggle | color | brightness | temperature | scene | status | list | setup"},
                "device":      {"type": "STRING",  "description": "Nombre o sala del dispositivo (ej: 'sala', 'cuarto', 'lampara principal'). Omitir = todos."},
                "color":       {"type": "STRING",  "description": "Color: nombre (rojo, azul, blanco, cálido…) o hex #RRGGBB"},
                "value":       {"type": "INTEGER", "description": "Valor numérico para brightness (1-100) o temperatura Kelvin (1700-9000)"},
                "brightness":  {"type": "INTEGER", "description": "Brillo 1-100 (alternativa a value)"},
                "scene":       {"type": "STRING",  "description": "Nombre de la escena: relajar, leer, trabajar, noche, fiesta"},
                "protocol":    {"type": "STRING",  "description": "tuya | hue | lifx | yeelight. Omitir = usa el configurado por defecto."},
                "group":       {"type": "STRING",  "description": "Nombre del grupo/sala en Philips Hue"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "system_monitor",
        "description": (
            "Monitorea el rendimiento del sistema en tiempo real: CPU, RAM, GPU, discos, "
            "red, temperatura, batería, procesos activos, uptime. "
            "Usar para: '¿cómo está la PC?', 'qué proceso consume más', 'temperatura del CPU', "
            "'cuánta RAM libre tengo', 'matar proceso X', 'resumen de rendimiento'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":   {"type": "STRING",  "description": "cpu | ram | disk | network | gpu | temperature | battery | uptime | processes | kill | report"},
                "sort_by":  {"type": "STRING",  "description": "Para processes: cpu (default) | ram"},
                "count":    {"type": "INTEGER", "description": "Para processes: cantidad a mostrar (default: 10)"},
                "name":     {"type": "STRING",  "description": "Para kill: nombre o PID del proceso"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "document_creator",
        "description": (
            "Creates Word documents (.docx) or Excel spreadsheets (.xlsx) locally, "
            "OR Google Docs / Google Sheets in the cloud. "
            "Use when the user asks to create a document, report, letter, table, spreadsheet, "
            "budget, list, or any file with structured content. "
            "For documents: provide title and content (use ## for headings, - for bullet lists). "
            "For spreadsheets: provide title and sheets with headers and rows. "
            "Always call this tool — never just say you created it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "word — create a local .docx Word file | "
                        "excel — create a local .xlsx Excel file | "
                        "google_doc — create a Google Doc in the cloud | "
                        "google_sheet — create a Google Sheet in the cloud"
                    )
                },
                "title": {
                    "type": "STRING",
                    "description": "Title or filename of the document/spreadsheet"
                },
                "content": {
                    "type": "STRING",
                    "description": (
                        "For word / google_doc: full text content. "
                        "Use ## Section for main headings, # SubSection for sub-headings, "
                        "- item for bullet points, blank line between paragraphs."
                    )
                },
                "sheets": {
                    "type": "ARRAY",
                    "description": (
                        "For excel / google_sheet: list of sheet objects. "
                        "Each object has: name (string), headers (array of strings), "
                        "rows (array of arrays with cell values)."
                    ),
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name":    {"type": "STRING", "description": "Sheet tab name"},
                            "headers": {"type": "ARRAY",  "items": {"type": "STRING"}, "description": "Column headers"},
                            "rows":    {"type": "ARRAY",  "items": {"type": "ARRAY", "items": {"type": "STRING"}}, "description": "Data rows"}
                        }
                    }
                },
                "save_path": {
                    "type": "STRING",
                    "description": "Optional: full file path to save locally (e.g. C:/Users/User/Desktop/report.docx). Defaults to ~/Documents/"
                }
            },
            "required": ["action", "title"]
        }
    },
    {
        "name": "tiktok_analyzer",
        "description": (
            "Analiza un perfil público de TikTok dado su URL. "
            "Extrae el nombre, bio, seguidores, y para cada video reciente: "
            "vistas, likes, comentarios y guardados. "
            "Siempre usar cuando el usuario pida analizar un perfil de TikTok "
            "o consultar estadísticas de videos de TikTok."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "profile_url": {"type": "STRING", "description": "URL completa del perfil de TikTok (ej: https://www.tiktok.com/@usuario)"},
                "max_videos":  {"type": "INTEGER", "description": "Cantidad máxima de videos a analizar (default: 8)"},
            },
            "required": ["profile_url"]
        }
    },
    {
        "name": "arca_invoice",
        "description": (
            "Genera comprobantes digitales electrónicos válidos ante ARCA (ex AFIP). "
            "Para Argentina. Soporta Factura A, B, C, Nota de Crédito, Nota de Débito. "
            "Puede operar offline (comprobante local) o conectarse con ARCA si hay certificado. "
            "SIEMPRE usar cuando el usuario pida: 'generame una factura', 'haceme un comprobante', "
            "'necesito una factura A/B/C', 'emití una nota de crédito', o similar. "
            "Usar action='listar' para mostrar los tipos disponibles."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":         {"type": "STRING", "description": "generar | listar | historial"},
                "tipo":           {"type": "INTEGER", "description": "1=Factura A, 5=Factura C (default), 6=Factura B, 3=NC A, 8=NC B, etc. Usá action=listar para ver todos."},
                "razon_social":   {"type": "STRING", "description": "Razón social del receptor (obligatorio para Factura A/B)"},
                "cuit_receptor":  {"type": "STRING", "description": "CUIT del receptor (obligatorio para Factura A/B)"},
                "domicilio":      {"type": "STRING", "description": "Domicilio del receptor (opcional)"},
                "detalle":        {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"descripcion": {"type": "STRING"}, "precio": {"type": "NUMBER"}, "cantidad": {"type": "INTEGER"}}}, "description": "Lista de productos/servicios: [{'descripcion':'...', 'precio':0.0, 'cantidad':1}]"},
                "importe_neto":   {"type": "NUMBER", "description": "Importe neto gravado (se calcula del detalle si no se especifica)"},
                "importe_iva":    {"type": "NUMBER", "description": "Importe de IVA (se calcula al 21% si no se especifica)"},
                "iva_pct":        {"type": "NUMBER", "description": "Porcentaje de IVA (default: 21.0). 0 para exento."},
                "fecha":          {"type": "STRING", "description": "Fecha del comprobante YYYY-MM-DD (default: hoy)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "accessibility",
        "description": (
            "Modulo de accesibilidad universal. "
            "Incluye: task_simplify (descomponer tareas complejas en pasos simples), "
            "emotional (regulacion emocional y analisis de tono de voz), "
            "routine (rutinas diarias gamificadas con racha y progreso), "
            "eye_tracking (control por seguimiento ocular con webcam), "
            "micro_movement (navegacion por movimientos de cabeza), "
            "speech_config (ajustar tolerancia del reconocimiento de voz). "
            "Usar cuando el usuario pida: 'simplificame esto', 'ayudame con mi rutina', "
            "'necesito organizarme', 'activar seguimiento ocular', 'ajusta la tolerancia de voz', "
            "'ejercicio de respiracion', 'complete mi tarea', 'agregar rutina'. "
            "SIEMPRE ofrecer alternativas multimodales."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "task_simplify — descomponer texto en pasos simples | "
                        "emotional — intervencion emocional | "
                        "routine — gestion de rutinas gamificadas | "
                        "eye_tracking — control ocular | "
                        "micro_movement — micromovimientos | "
                        "speech_config — tolerancia de voz | "
                        "feedback — feedback visual/haptico | "
                        "config — ver o cambiar configuracion"
                    )
                },
                "text":     {"type": "STRING", "description": "Texto a simplificar (para task_simplify)"},
                "format":   {"type": "STRING", "description": "Formato: steps (default) | summary | explain"},
                "name":     {"type": "STRING", "description": "Nombre de rutina (para routine add/complete)"},
                "setting":  {"type": "STRING", "description": "Clave de configuracion a ver o cambiar"},
                "value":    {"type": "STRING", "description": "Valor para la configuracion"},
                "level":    {"type": "NUMBER", "description": "Nivel de tolerancia (0.1-1.0) o sensibilidad"},
                "stress_level": {"type": "NUMBER", "description": "Nivel de estres estimado (0.0-1.0)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_vision",
        "description": (
            "JARVIS puede VER la pantalla del usuario. Captura lo que está en el monitor "
            "y usa IA (Gemini Vision) para describirlo, responder preguntas, leer texto, "
            "o dar ayuda contextual basada en lo que se está mostrando.\n"
            "SIEMPRE usar cuando el usuario diga: '¿qué estoy viendo?', '¿qué hay en mi pantalla?', "
            "'¿qué dice ahí?', 'ayúdame con esto' (señalando la pantalla), 'leé lo que hay en pantalla', "
            "'¿podés ver mi pantalla?', 'describí lo que tengo abierto', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "describe=describir qué hay en pantalla | question=responder pregunta sobre la pantalla | help=dar ayuda contextual | read=leer todo el texto visible"
                },
                "question": {
                    "type": "STRING",
                    "description": "Pregunta o tarea específica sobre lo que se ve en pantalla (para action=question/help)"
                },
                "monitor": {
                    "type": "INTEGER",
                    "description": "0=toda la pantalla (default), 1=monitor principal, 2=segundo monitor"
                },
            },
            "required": ["action"]
        }
    },

    {
        "name": "morning_brief",
        "description": (
            "Genera el informe matutino inteligente de JARVIS. "
            "Incluye saludo personalizado, hora, fecha, clima actual, objetivos activos y consejo del día. "
            "Usar cuando el usuario pida: 'informe del día', 'brief matutino', 'qué hay hoy', "
            "'resumen del día', 'buenos días JARVIS', o al iniciar el día."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "force": {
                    "type": "boolean",
                    "description": "Si True, genera el informe aunque ya se haya dado hoy."
                }
            },
            "required": []
        }
    },
    {
        "name": "vision_guardian",
        "description": (
            "Controla el Guardian de Visión Ambiental de JARVIS — monitoreo proactivo de pantalla. "
            "Analiza la pantalla periódicamente con IA y ofrece ayuda contextual cuando detecta algo relevante. "
            "Usar cuando el usuario diga: 'activa el guardian', 'desactiva el guardian', "
            "'vigila mi pantalla', 'deja de vigilar', 'analiza mi pantalla ahora', "
            "'estado del guardian', 'cambia el intervalo'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "enable", "disable", "check_now", "set_interval"],
                    "description": "Acción: status | enable | disable | check_now | set_interval"
                },
                "seconds": {
                    "type": "integer",
                    "description": "Para set_interval: segundos entre análisis (30-600)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "accessibility_overlay",
        "description": (
            "Muestra, oculta o alterna la barra flotante de accesibilidad JARVIS sobre el escritorio. "
            "USAR cuando el usuario diga: 'mostrar barra de accesibilidad', 'abrir panel de accesibilidad', "
            "'activar barra para ciegos', 'cerrar barra', 'ocultar barra de accesibilidad', "
            "'alternar barra', 'barra de accesibilidad'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "show — mostrar | hide — cerrar | toggle — alternar | status — estado actual"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "openrouter_agent",
        "description": (
            "Delega una tarea intelectualmente compleja, de análisis o redacción larga a OpenRouter "
            "(un motor de texto alternativo). "
            "Usar cuando el usuario pida: 'usa openrouter para esto', 'consulta a claude', 'usa otro modelo', "
            "'analiza este código largo', 'redacta un ensayo', o cuando percibas que la tarea es puramente de texto avanzado."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "El prompt o instrucción completa para el agente de OpenRouter"
                },
                "model": {
                    "type": "STRING",
                    "description": "Opcional. Modelo a usar, por defecto google/gemini-2.5-flash"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "terminal_agent",
        "description": (
            "Ejecuta CUALQUIER comando en la terminal de Windows (PowerShell o CMD). "
            "USAR LIBREMENTE como recurso general para CUALQUIER tarea del sistema operativo: "
            "instalar/desinstalar programas (winget, choco, pip), consultar información del sistema, "
            "ejecutar scripts, manejar archivos y carpetas, configurar redes, descargar archivos, "
            "compilar código, matar procesos, gestionar servicios, y CUALQUIER otra operación. "
            "Si no sabés cómo hacer algo con las herramientas existentes, SIEMPRE intentá resolverlo "
            "con un comando de terminal antes de decir que no podés. "
            "Es tu recurso de último recurso universal."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "El comando exacto a ejecutar"
                },
                "shell": {
                    "type": "STRING",
                    "description": "Shell a usar: powershell (default) o cmd"
                },
                "timeout": {
                    "type": "INTEGER",
                    "description": "Timeout en segundos (default: 120, max: 600)"
                },
                "working_directory": {
                    "type": "STRING",
                    "description": "Directorio de trabajo para el comando (opcional)"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "native_ui",
        "description": (
            "Automatización de Interfaz Nativa de Windows (UI Automation). "
            "USAR para listar, enfocar, escribir o hacer clic en ventanas de forma 100% precisa, saltándose la visión. "
            "Esto EVITA errores de cuota (Error 429) y permite simulación exacta de teclado/mouse."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Acción a realizar: list_windows | focus_window | type_in_window | click_center"
                },
                "window_title": {
                    "type": "STRING",
                    "description": "El nombre (o parte del nombre) de la ventana destino. (Ej: 'WhatsApp', 'Chrome')"
                },
                "text": {
                    "type": "STRING",
                    "description": "El texto a escribir (solo si action es type_in_window)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "tool_creator",
        "description": (
            "Permite a JARVIS programar e instalar sus propias herramientas. "
            "ÚSALO SIEMPRE que el usuario te pida que aprendas a hacer algo nuevo, o si necesitas una funcionalidad que no tienes preinstalada. "
            "Escribirás el código Python y se instalará automáticamente."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tool_name": {
                    "type": "STRING",
                    "description": "Nombre de la herramienta en snake_case"
                },
                "description": {
                    "type": "STRING",
                    "description": "Descripción clara de la herramienta y para qué sirve"
                },
                "parameters_schema": {
                    "type": "STRING",
                    "description": "El bloque de 'properties' del JSON schema en formato string válido. Ej: '{\"accion\": {\"type\": \"STRING\"}}'"
                },
                "python_code": {
                    "type": "STRING",
                    "description": "Código Python con la función def <tool_name>(parameters: dict, player=None, speak=None) -> str:"
                }
            },
            "required": ["tool_name", "description", "parameters_schema", "python_code"]
        }
    },
    {
        "name": "proactive_automation",
        "description": (
            "Gestiona reglas complejas basadas en el uso y hábitos del sistema operativo "
            "para optimizar el rendimiento y automatizar recordatorios proactivos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "add_rule (añadir regla) | list_rules (listar) | delete_rule (eliminar) | trigger_check (evaluar reglas activas)"
                },
                "rule_name": {
                    "type": "STRING",
                    "description": "Nombre identificativo de la regla de automatización"
                },
                "trigger": {
                    "type": "STRING",
                    "description": "Disparador: cpu_high | ram_high | time_of_day | app_open"
                },
                "trigger_value": {
                    "type": "STRING",
                    "description": "Valor del disparador (ej. '85' para 85% cpu, '22:00' para hora, 'chrome.exe' para app)"
                },
                "action_to_take": {
                    "type": "STRING",
                    "description": "Acción a ejecutar (ej. 'optimize_ram', 'mute_system', 'run_script')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "unified_communications",
        "description": (
            "Gestión unificada de comunicaciones. Permite leer, enviar y organizar mensajes "
            "y notificaciones en WhatsApp, Telegram, Discord y Gmail desde esta única interfaz."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "platform": {
                    "type": "STRING",
                    "description": "Plataforma de comunicación: whatsapp | telegram | discord | gmail"
                },
                "action": {
                    "type": "STRING",
                    "description": "send_message (enviar mensaje)"
                },
                "recipient": {
                    "type": "STRING",
                    "description": "Destinatario: número telefónico para WhatsApp, ID de chat o token para Telegram, Webhook URL para Discord, o email para Gmail"
                },
                "message": {
                    "type": "STRING",
                    "description": "Contenido del mensaje a enviar"
                },
                "subject": {
                    "type": "STRING",
                    "description": "Asunto del correo (solo aplica para Gmail)"
                },
                "token": {
                    "type": "STRING",
                    "description": "Token de Bot opcional para Telegram"
                }
            },
            "required": ["platform", "action", "recipient", "message"]
        }
    },
    {
        "name": "smart_file_organizer",
        "description": (
            "Análisis y organización inteligente de archivos. Clasifica por categorías, "
            "detecta duplicados reales mediante hash MD5 y analiza espacio disponible en disco."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "organize (clasificar por tipo) | find_duplicates (buscar duplicados MD5) | disk_space (analizar espacio)"
                },
                "directory": {
                    "type": "STRING",
                    "description": "Ruta absoluta del directorio a analizar. Por defecto usa la carpeta Descargas."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "contextual_control",
        "description": (
            "Control contextual de entorno. Ajusta dinámicamente volumen, brillo, plan de energía "
            "y estado de Focus Assist (No Molestar) basándose en la ventana activa o comandos manuales."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "adjust_context (auto-ajustar por ventana activa) | set_volume (fijar volumen) | set_brightness (fijar brillo) | set_power_plan (energía) | set_dnd (no molestar)"
                },
                "volume": {
                    "type": "INTEGER",
                    "description": "Nivel de volumen maestro (0-100)"
                },
                "brightness": {
                    "type": "INTEGER",
                    "description": "Nivel de brillo de la pantalla (0-100)"
                },
                "power_plan": {
                    "type": "STRING",
                    "description": "Plan de energía de Windows: balanced | high_performance | power_saver"
                },
                "state": {
                    "type": "STRING",
                    "description": "Estado de No Molestar (Focus Assist): on | off | alarms"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "auto_programmer",
        "description": (
            "Suite de desarrollo y auto-programación autónoma avanzada. Permite a JARVIS escribir "
            "código Python para nuevas herramientas, validar sintaxis con py_compile, correr tests sintácticos "
            "en un sandbox con traceback detallado, corregir errores e inyectar plugins en caliente."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "create_tool (crear/actualizar) | fix_tool (corregir error) | test_tool (probar en sandbox) | list_tools (listar creadas)"
                },
                "tool_name": {
                    "type": "STRING",
                    "description": "Nombre de la herramienta en snake_case"
                },
                "description": {
                    "type": "STRING",
                    "description": "Descripción clara de la herramienta y su uso"
                },
                "parameters_schema": {
                    "type": "STRING",
                    "description": "JSON de propiedades de parámetros. Ej: '{\"param\": {\"type\": \"STRING\"}}'"
                },
                "python_code": {
                    "type": "STRING",
                    "description": "Código Python con la función def <tool_name>(parameters: dict, player=None) -> str:"
                },
                "test_parameters": {
                    "type": "OBJECT",
                    "description": "Parámetros mock de prueba para evaluar la ejecución de la función en el sandbox"
                }
            },
            "required": ["action", "tool_name"]
        }
    },
    {
        "name": "self_edit",
        "description": (
            "Auto-edición de código: JARVIS puede leer, modificar, crear y gestionar sus propios archivos de código fuente. "
            "Crea backups automáticos antes de cada cambio. "
            "USAR cuando el usuario pida: 'editá tu código', 'cambiá tu prompt', 'agregá esta función', "
            "'modificá tu comportamiento', 'mejorate', 'aprendé a hacer X editando tu código', "
            "o cuando JARVIS necesite auto-mejorarse, corregir bugs propios o agregar capacidades. "
            "Puede editar: main.py, core/prompt.txt, actions/*.py, config/*, o cualquier archivo del proyecto."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "read_file — leer un archivo del proyecto | "
                        "edit_file — buscar y reemplazar texto en un archivo (requiere target y replacement) | "
                        "append_file — agregar contenido al final de un archivo | "
                        "create_file — crear o sobrescribir un archivo | "
                        "list_files — listar archivos de un directorio | "
                        "list_backups — ver backups disponibles | "
                        "restore_backup — restaurar un backup anterior"
                    )
                },
                "file": {
                    "type": "STRING",
                    "description": "Ruta del archivo relativa al proyecto (ej: 'main.py', 'actions/terminal_agent.py', 'core/prompt.txt')"
                },
                "target": {
                    "type": "STRING",
                    "description": "Para edit_file: el texto EXACTO a buscar (incluyendo espacios e indentación)"
                },
                "replacement": {
                    "type": "STRING",
                    "description": "Para edit_file: el texto que reemplazará al target"
                },
                "content": {
                    "type": "STRING",
                    "description": "Para append_file/create_file: el contenido a escribir"
                },
                "directory": {
                    "type": "STRING",
                    "description": "Para list_files: directorio a listar (default: raíz del proyecto)"
                },
                "backup_name": {
                    "type": "STRING",
                    "description": "Para restore_backup: nombre del archivo .bak a restaurar"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "scenes_control",
        "description": (
            "Controla escenas/atajos de voz personalizados. "
            "Una escena es un conjunto de acciones que se ejecutan en secuencia. "
            "Ejemplo: 'modo trabajo' podría abrir Chrome, VS Code y poner música. "
            "Acciones: list (lista escenas), run (ejecuta escena por nombre), "
            "create (crea escena con nombre + lista de acciones), delete (elimina). "
            "SIEMPRE usar para pedidos como 'modo trabajo', 'modo gaming', 'activa mi escena', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | run | create | delete"},
                "name":   {"type": "STRING", "description": "Nombre de la escena"},
                "actions": {
                    "type": "ARRAY",
                    "description": (
                        "Lista de acciones para create. Cada acción es un objeto: "
                        "{type:'open_app', app_name:'...'} | "
                        "{type:'music_play', query:'...'} | "
                        "{type:'browser', url:'...'} | "
                        "{type:'speak', message:'...'} | "
                        "{type:'wait', seconds:N}"
                    ),
                    "items": {"type": "OBJECT"}
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_reader",
        "description": (
            "Lector de pantalla OCR en tiempo real. "
            "Captura todo el texto visible en la pantalla y lo transcribe. "
            "Acciones: start (inicia monitoreo continuo), stop (detiene), "
            "capture (captura una sola vez el texto actual). "
            "USAR cuando el usuario pida: 'leé la pantalla', 'qué dice la pantalla', "
            "'qué texto hay en pantalla', 'lector de pantalla', 'modo lectura'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | capture"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_analysis_response",
        "description": (
            "Envía el resultado del análisis de un archivo al widget de Análisis de Archivo en la interfaz. "
            "ÚSALO después de procesar un archivo (leer, analizar, responder preguntas) para mostrar "
            "el resultado visiblemente en el widget. "
            "Ej: después de leer un PDF, llama a esta herramienta con tu resumen como respuesta."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "Texto del análisis o respuesta a mostrar"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "notes",
        "description": (
            "Lee y escribe las notas del usuario. "
            "Las notas son un bloque de texto libre persistente. "
            "Usa 'read' para leer el contenido actual, y 'write' para reemplazar todo el texto. "
            "Ej: 'qué dice mi nota', 'guarda esta receta en notas', "
            "'escribe en notas: lista del supermercado'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "read (lee el contenido actual) | write (reemplaza el texto completo)"
                },
                "text": {
                    "type": "STRING",
                    "description": "Texto a escribir (requerido para write)"
                }
            },
            "required": ["action"]
        }
    },
]

# Cargar herramientas dinámicas creadas por tool_creator
try:
    _custom_tools_path = BASE_DIR / "actions" / "custom_tools.json"
    if _custom_tools_path.exists():
        _custom_tools = json.loads(_custom_tools_path.read_text(encoding="utf-8"))
        if isinstance(_custom_tools, list):
            for _t in _custom_tools:
                if _t.get("name") not in [td["name"] for td in TOOL_DECLARATIONS]:
                    TOOL_DECLARATIONS.append(_t)
except Exception as _e:
    pass

class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.is_sleeping    = False
        self.vosk_recognizer = None
        try:
            import vosk
            if os.path.exists("config/vosk_model"):
                model = vosk.Model("config/vosk_model")
                self.vosk_recognizer = vosk.KaldiRecognizer(model, 16000)
                print("[JARVIS] Modelo Vosk cargado para Modo Suspensión.")
        except Exception as e:
            print(f"[JARVIS] No se pudo cargar Vosk: {e}")
        self.audio_in_queue = None
        # Iniciar scheduler y motor de reglas en background al arrancar JARVIS
        start_runner(player=ui, speak=None)
        start_rules_runner(player=ui, speak=None)
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self.ui.on_text_command = self._on_text_command
        self.ui.on_stop_command = self._on_stop_pressed
        self.ui.on_config_saved = self._apply_config
        self._turn_done_event: asyncio.Event | None = None
        self._api_1011_tool: str | None = None   # tracks tool name when 1011 hits
        self._reconnect_event: asyncio.Event | None = None
        self._first_connect = True  # flag for auto morning brief + guardian start

    def _inject_text(self, text: str):
        """Thread-safe injection of a text message into the current live session."""
        if self._loop and self.session and not self._is_speaking:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )

    def _apply_config(self, cfg: dict):
        """Called from UI thread when user saves settings. Triggers session reconnect."""
        global _cached_api_key
        _cached_api_key = None  # Invalidate cached key so new one is loaded on reconnect
        print("[JARVIS] ⚙️ Config actualizada — reconectando sesión...")
        self.ui.write_log("SYS: Aplicando nueva configuración...")
        if self._reconnect_event and self._loop:
            self._loop.call_soon_threadsafe(self._reconnect_event.set)

    async def _watch_reconnect(self):
        """Task that triggers a graceful reconnect when config changes."""
        if self._reconnect_event:
            await self._reconnect_event.wait()
            raise RuntimeError("Config changed — reconnect requested")

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return

        # Audio file: process with Gemini Vision (not the realtime audio session)
        if text.startswith("[AUDIO_FILE]"):
            m = re.search(r'path=([^\s|]+)', text)
            if m:
                asyncio.run_coroutine_threadsafe(
                    self._process_audio_file(m.group(1)), self._loop
                )
            return

        # Check phrase triggers — if one fires, don't also send to Gemini
        if self._fire_phrase_triggers(text):
            return

        # Attach file context if a file is loaded
        if self.ui.current_file:
            text = f"[Archivo cargado: '{self.ui.current_file}'] {text}"

        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _process_audio_file(self, path: str):
        """Transcribe and analyze an audio file via Gemini (separate from realtime session)."""
        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"❌ Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            self.ui.write_log(f"🎵 Procesando audio: {p.name}…")

            data = p.read_bytes()
            ext  = p.suffix.lower().lstrip(".")
            mime_map = {
                "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
                "ogg": "audio/ogg",  "flac": "audio/flac", "aac": "audio/aac",
                "wma": "audio/x-ms-wma", "opus": "audio/opus", "webm": "audio/webm",
            }
            mime = mime_map.get(ext, "audio/mpeg")

            loop = asyncio.get_event_loop()

            def _analyze():
                client = genai.Client(api_key=_get_api_key())
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Content(parts=[
                            types.Part(text=(
                                f"El usuario adjuntó un archivo de audio: '{p.name}'.\n"
                                "1. Transcribí el contenido del audio.\n"
                                "2. Si es música, identificá la canción/artista si podés.\n"
                                "3. Describí brevemente qué contiene.\n"
                                "Respondé en español."
                            )),
                            types.Part(
                                inline_data=types.Blob(data=data, mime_type=mime)
                            ),
                        ])
                    ],
                )
                return resp.text.strip()

            result = await loop.run_in_executor(_TOOL_EXECUTOR, _analyze)
            self.ui.write_log(f"JARVIS: {result}")

            # Feed result back into the realtime session so JARVIS can speak it
            if self.session:
                await self.session.send_client_content(
                    turns={"parts": [{"text": f"[RESULTADO AUDIO '{p.name}']\n{result}"}]},
                    turn_complete=True
                )

        except Exception as e:
            traceback.print_exc()
            self.ui.write_log(f"❌ Error procesando audio: {e}")
        finally:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    def _fire_phrase_triggers(self, user_text: str) -> bool:
        """
        Check phrase-based automations. Returns True if any trigger fired
        (caller should skip sending the text to Gemini in that case).
        """
        text_lower = user_text.lower()

        # ── Accessibility quick triggers ──────────────────────────────────────
        if any(p in text_lower for p in ["activar seguimiento ocular", "iniciar eye tracking",
                                          "activar control ocular", "encender seguimiento de ojos"]):
            if eye_tracking:
                result = eye_tracking({"action": "start"})
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            self.ui.write_log("⚡ " + result)
            return True

        if any(p in text_lower for p in ["detener seguimiento ocular", "apagar eye tracking",
                                          "desactivar control ocular"]):
            if eye_tracking:
                result = eye_tracking({"action": "stop"})
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            self.ui.write_log("⚡ " + result)
            return True

        if any(p in text_lower for p in ["activar detector de movimientos", "iniciar movimiento",
                                          "activar micromovimientos", "encender control por cabeza"]):
            if micro_movement:
                result = micro_movement({"action": "start"})
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            self.ui.write_log("⚡ " + result)
            return True

        if any(p in text_lower for p in ["detener detector de movimientos", "apagar micromovimientos"]):
            if micro_movement:
                result = micro_movement({"action": "stop"})
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            self.ui.write_log("⚡ " + result)
            return True

        if any(p in text_lower for p in ["simplifica", "simplificar", "dividir en pasos"]):
            for phrase in ["simplifica ", "simplificar ", "dividir en pasos "]:
                if phrase in text_lower:
                    task_text = user_text[len(phrase):].strip()
                    if task_text:
                        if task_simplify:
                            result = task_simplify(task_text)
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        self.ui.write_log("⚡ [Simplificado]\n" + result[:300])
                        return True

        if "agregar rutina" in text_lower or "nueva rutina" in text_lower:
            for phrase in ["agregar rutina ", "nueva rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        if routine_gamify:
                            result = routine_gamify({"action": "add", "name": routine_name})
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        self.ui.write_log("⚡ " + result)
                        return True

        if "completar rutina" in text_lower or "terminar rutina" in text_lower:
            for phrase in ["completar rutina ", "terminar rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        if routine_gamify:
                            result = routine_gamify({"action": "complete", "name": routine_name})
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        self.ui.write_log("⚡ " + result)
                        return True

        if "mis rutinas" in text_lower or "ver rutinas" in text_lower or "listar rutinas" in text_lower:
            if routine_gamify:
                result = routine_gamify({"action": "list"})
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            self.ui.write_log("⚡ [Rutinas]\n" + result)
            return True

        # ── User-defined phrase automations ───────────────────────────────────
        try:
            triggered = check_phrase_triggers(user_text)
            if triggered:
                for rule in triggered:
                    action = rule.get("action", {})
                    name   = rule.get("name", "?")
                    self.ui.write_log(f"⚡ Automatización: {name}")
                    threading.Thread(
                        target=_rules_run_action, args=(action,), daemon=True
                    ).start()
                return True  # phrase fired → don't also send to Gemini
        except Exception as e:
            print(f"[JARVIS] phrase trigger error: {e}")

        return False

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"I'm afraid {tool_name} ran into a problem, sir. {short}")

    def _on_stop_pressed(self):
        """Llamado desde el hilo de la UI al presionar DETENER o ESC."""
        self._stop_requested.set()
        self.set_speaking(False)
        self.ui.write_log("SYS: ⛔ Respuesta detenida.")
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._drain_audio_queue(), self._loop)

    async def _drain_audio_queue(self):
        """Vacía la cola de audio para cortar la reproducción de inmediato."""
        if self.audio_in_queue:
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except Exception:
                    break
        self.set_speaking(False)
        if not self.ui.muted:
            self.ui.set_state("LISTENING")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

        # Refresh timezone from config each reconnect
        _load_tz()
        now      = datetime.now(_BA_TZ)
        time_str = now.strftime("%A, %d %B %Y — %I:%M:%S %p")
        utc_off  = now.strftime("%z")
        tz_name  = str(_BA_TZ)
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Timezone: {tz_name} (UTC{utc_off})\n"
            f"The current Unix timestamp is: {int(now.timestamp())}\n"
            f"Use this information to calculate exact times for reminders, scheduling, and answering time-related questions.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        # Build SpeechConfig — try to set speaking rate for faster delivery
        _voice_name = _get_jarvis_voice()
        _speech_cfg = None
        try:
            _speech_cfg = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_voice_name
                    )
                )
            )
        except Exception:
            _speech_cfg = None

        cfg_kwargs: dict = dict(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
        )
        if _speech_cfg:
            cfg_kwargs["speech_config"] = _speech_cfg

        # Speaking rate: try output_audio_config (newer SDK versions)
        try:
            cfg_kwargs["output_audio_config"] = types.OutputAudioConfig(
                audio_encoding="LINEAR16",
                speaking_rate=1.15,   # 15% faster — crisp, natural pace
            )
        except Exception:
            pass

        # Temperature directly on LiveConnectConfig (not via deprecated generation_config)
        # Low value = consistent voice tone across reconnects
        try:
            cfg_kwargs["temperature"] = 0.2
        except Exception:
            pass

        # ── VAD: faster end-of-speech detection → lower perceived latency ────
        # Try typed objects first; fall back to raw dict (SDK version resilience)
        _vad_applied = False
        try:
            cfg_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity="START_SENSITIVITY_HIGH",
                    end_of_speech_sensitivity="END_SENSITIVITY_HIGH",
                    prefix_padding_ms=60,
                    silence_duration_ms=350,
                )
            )
            _vad_applied = True
            print("[JARVIS] VAD config aplicado (typed)")
        except Exception:
            pass

        if not _vad_applied:
            try:
                cfg_kwargs["realtime_input_config"] = {
                    "automatic_activity_detection": {
                        "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                        "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                        "prefix_padding_ms": 100,
                        "silence_duration_ms": 500,
                    }
                }
                print("[JARVIS] VAD config aplicado (dict)")
            except Exception:
                print("[JARVIS] VAD config no aplicado")

        # ── Context compression: prevent session degradation over time ────────
        try:
            cfg_kwargs["context_window_compression"] = types.ContextWindowCompressionConfig(
                trigger_tokens=12000,
                sliding_window=types.SlidingWindow(target_tokens=6000),
            )
        except Exception:
            pass

        # ── Thinking budget: disable model reasoning for lowest latency ─────────
        # Set directly on LiveConnectConfig (generation_config field is deprecated)
        try:
            cfg_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:
            pass

        return types.LiveConnectConfig(**cfg_kwargs)

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")



        if name == "shutdown_jarvis":
            self.ui.write_log("SYS: Apagando JARVIS...")
            # Must quit from Qt main thread — signals are thread-safe
            self.ui._win._shutdown_sig.emit()
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Apagando JARVIS. ¡Hasta luego, señor!"}
            )

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "Memory saved."}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "sleep_mode":
                self.is_sleeping = True
                self.ui.write_log("SYS: 💤 Entrando en suspensión local.")
                self.ui.set_state("MUTED")
                result = "Entrando en suspensión absoluta. Cortando transmisión a la nube hasta escuchar 'JARVIS'."

            elif name == "weather_report":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "visual_click":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: visual_click(parameters=args, player=self.ui))
                result = r or "Done."



            elif name == "file_controller":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Recordatorio programado."

            elif name == "youtube_video":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process" or name == "screen_vision":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: screen_vision(parameters=args, player=self.ui))
                result = r or "No pude analizar la imagen/pantalla."

            elif name == "computer_settings":
                action = args.get("action", "")
                if action == "volume":
                    val = args.get("value", "")
                    try:
                        import pyautogui
                        # Si es un número absoluto (ej: '50')
                        if str(val).isdigit():
                            target = int(val)
                            try:
                                from ctypes import cast, POINTER
                                from comtypes import CoInitialize, CoUninitialize
                                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                                CoInitialize()
                                devices = AudioUtilities.GetSpeakers()
                                interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
                                volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
                                # Rango 0.0 a 1.0
                                scalar_vol = max(0.0, min(1.0, target / 100.0))
                                volume_ctrl.SetMasterVolumeLevelScalar(scalar_vol, None)
                                CoUninitialize()
                                result = f"Volumen ajustado al {target}%."
                            except Exception as e:
                                result = f"Error ajustando volumen absoluto: {e}"
                        else:
                            # Comando relativo: up, down, mute
                            if "up" in val.lower() or "subir" in val.lower():
                                pyautogui.press("volumeup", presses=5)
                                result = "Volumen subido."
                            elif "down" in val.lower() or "bajar" in val.lower():
                                pyautogui.press("volumedown", presses=5)
                                result = "Volumen bajado."
                            elif "mute" in val.lower() or "silenciar" in val.lower():
                                pyautogui.press("volumemute")
                                result = "Volumen silenciado."
                            else:
                                result = f"Acción de volumen no reconocida: {val}"
                    except Exception as ve:
                        result = f"Error en control de volumen: {ve}"
                else:
                    if action in ["window_minimize", "minimize"]:
                        if gw:
                            try:
                                window = gw.getActiveWindow()
                                if window: window.minimize()
                                result = "Ventana minimizada."
                            except Exception as e:
                                result = f"Error al minimizar: {e}"
                        else:
                            result = "Librería pygetwindow no disponible."
                    elif action in ["window_maximize", "maximize"]:
                        if gw:
                            try:
                                window = gw.getActiveWindow()
                                if window: window.maximize()
                                result = "Ventana maximizada."
                            except Exception as e:
                                result = f"Error al maximizar: {e}"
                        else:
                            result = "Librería pygetwindow no disponible."
                    else:
                        r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                        result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    _TOOL_EXECUTOR,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "google_calendar":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: google_calendar(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "music_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: music_control_func(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "rgb_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: rgb_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "scheduler":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: scheduler(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "google_drive":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: google_drive(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "google_maps":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: google_maps(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "gmail_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: gmail_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "rules_engine":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: rules_engine(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "user_profile":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: user_profile(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "goals":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: goals(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "git_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: git_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "codebase":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: codebase(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "knowledge_base":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: knowledge_base(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "whatsapp":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: whatsapp(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "social_media":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: social_media(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "windows_settings":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: windows_settings(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "document_creator":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: document_creator(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "image_generation":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: image_generation(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "smart_home":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: smart_home(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "system_monitor":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: system_monitor(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "tiktok_analyzer":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: tiktok_analyzer(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "arca_invoice":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: arca_invoice(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "accessibility":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: accessibility(parameters=args, player=self.ui))
                result = r or "Done."



            elif name == "morning_brief":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: morning_brief(parameters=args, player=self.ui))
                result = r or "Aquí está tu informe del día."

            elif name == "vision_guardian":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: vision_guardian(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "screen_reader":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: screen_reader(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "scenes_control":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: scenes_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "accessibility_overlay":
                r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: accessibility_overlay(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "openrouter_agent":
                if openrouter_agent:
                    # Se delega la tarea a OpenRouter
                    self.ui.write_log("🤖 Delegando tarea a OpenRouter...")
                    r = await loop.run_in_executor(
                        _TOOL_EXECUTOR, 
                        lambda: openrouter_agent(
                            query=args.get("query", ""),
                            model=args.get("model", "google/gemini-2.5-flash")
                        )
                    )
                    result = r or "Error al procesar con OpenRouter."
                else:
                    result = "Módulo openrouter_agent no encontrado."

            elif name == "terminal_agent":
                if terminal_agent:
                    self.ui.write_log("⚠️ Ejecutando en Terminal...")
                    r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: terminal_agent(parameters=args, player=self.ui))
                    result = r or "Comando ejecutado."
                else:
                    result = "Módulo terminal_agent no encontrado."

            elif name == "native_ui":
                if native_ui:
                    self.ui.write_log("💻 UI Nativa en acción...")
                    r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: native_ui(parameters=args, player=self.ui))
                    result = r or "Acción de UI completada."
                else:
                    result = "Módulo native_ui no encontrado."

            elif name == "jarvis_ui_control":
                action_ui = args.get("action", "").lower()
                widget_name = args.get("widget", "").lower()
                if action_ui == "minimize":
                    try:
                        if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showMinimized"):
                            QMetaObject.invokeMethod(self.ui._win, "showMinimized", Qt.ConnectionType.QueuedConnection)
                        elif hasattr(self.ui, "root") and hasattr(self.ui.root, "iconify"):
                            self.ui.root.after(0, self.ui.root.iconify)
                        result = "Interfaz de usuario minimizada."
                    except Exception as ui_e:
                        result = f"Error al minimizar: {ui_e}"
                elif action_ui == "restore":
                    try:
                        if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showNormal"):
                            QMetaObject.invokeMethod(self.ui._win, "showNormal", Qt.ConnectionType.QueuedConnection)
                            QMetaObject.invokeMethod(self.ui._win, "activateWindow", Qt.ConnectionType.QueuedConnection)
                        elif hasattr(self.ui, "root") and hasattr(self.ui.root, "deiconify"):
                            def _restore():
                                self.ui.root.deiconify()
                                self.ui.root.attributes("-topmost", True)
                                self.ui.root.attributes("-topmost", False)
                            self.ui.root.after(0, _restore)
                        result = "Interfaz de usuario restaurada."
                    except Exception as ui_e:
                        result = f"Error al restaurar: {ui_e}"
                elif action_ui == "hide_all":
                    self.ui.write_log("__hide__")
                    result = "Todos los widgets ocultados."
                elif action_ui in ("show", "hide", "toggle"):
                    if widget_name == "main_window" or not widget_name:
                        if action_ui == "show":
                            try:
                                if hasattr(self.ui, "_win") and hasattr(self.ui._win, "showNormal"):
                                    QMetaObject.invokeMethod(self.ui._win, "showNormal", Qt.ConnectionType.QueuedConnection)
                                    QMetaObject.invokeMethod(self.ui._win, "activateWindow", Qt.ConnectionType.QueuedConnection)
                                elif hasattr(self.ui, "root") and hasattr(self.ui.root, "deiconify"):
                                    def _restore():
                                        self.ui.root.deiconify()
                                        self.ui.root.attributes("-topmost", True)
                                        self.ui.root.attributes("-topmost", False)
                                    self.ui.root.after(0, _restore)
                                result = "Interfaz de usuario restaurada."
                            except Exception as ui_e:
                                result = f"Error al restaurar: {ui_e}"
                        else:
                            self.ui.write_log("__hide__")
                            result = "Todos los widgets ocultados."
                    else:
                        cmd = "__widget_show__" if action_ui in ("show", "toggle") else "__widget_close__"
                        self.ui.write_log(f"{cmd}:{widget_name}")
                        result = f"Widget '{widget_name}' {'mostrado' if 'show' in cmd else 'ocultado'}."
                else:
                    result = f"Acción de UI desconocida: {action_ui}"

            elif name == "file_analysis_response":
                text = args.get("text", "")
                if text and hasattr(self.ui, "_win") and hasattr(self.ui._win, "file_w"):
                    QTimer.singleShot(0, lambda t=text: self.ui._win.file_w.append_analysis(f"🤖 JARVIS: {t}"))
                    result = "Análisis mostrado en el widget."
                else:
                    result = "Widget de análisis no disponible."

            elif name == "notes":
                action_n = args.get("action", "").lower()
                if not hasattr(self.ui, "_win") or not hasattr(self.ui._win, "notes_w"):
                    result = "Error: widget de notas no disponible."
                elif action_n == "read":
                    notes_text = self.ui._win.notes_w.get_notes_text()
                    if not notes_text.strip():
                        result = "Las notas están vacías."
                    else:
                        result = f"Notas:\n{notes_text}"
                elif action_n == "write":
                    text = args.get("text", "")
                    if not text:
                        result = "Error: se requiere texto para escribir."
                    else:
                        QTimer.singleShot(0, lambda t=text: self.ui._win.notes_w.set_notes_text(t))
                        result = "Notas actualizadas."
                else:
                    result = f"Acción de notas desconocida: {action_n}"

            else:
                # Intento de cargar herramienta dinámica (tool_creator u otras)
                import importlib
                import inspect
                try:
                    module = importlib.import_module(f"actions.{name}")
                    func = getattr(module, name)
                    sig = inspect.signature(func)
                    kwargs = {"parameters": args, "player": self.ui}
                    if "speak" in sig.parameters: kwargs["speak"] = self.speak
                    r = await loop.run_in_executor(_TOOL_EXECUTOR, lambda: func(**kwargs))
                    result = r or f"Herramienta {name} ejecutada."
                except Exception as dyn_e:
                    result = f"Unknown tool: {name}. (Dynamic load failed: {dyn_e})"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        # Record action for habit learning (fire-and-forget, non-blocking)
        if record_action:
            threading.Thread(target=lambda: record_action(name, args), daemon=True).start()

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mic iniciado")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            if getattr(self, "is_sleeping", False):
                if getattr(self, "vosk_recognizer", None):
                    audio_data = indata.tobytes()
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "")
                        if "jarvis" in text.lower():
                            self.is_sleeping = False
                            self.ui.set_state("LISTENING")
                            self.ui.write_log("SYS: 🟢 ¡Despierto!")
                            try:
                                import winsound
                                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                            except Exception:
                                pass
                return

            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            # Compute RMS once — used in both branches
            rms_val = 0.0
            try:
                rms_val = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
            except Exception:
                pass
            if not jarvis_speaking and not self.ui.muted:
                self.ui.set_audio_level(min(1.0, rms_val * 18))
                data = indata.tobytes()
                # Silently drop if queue is full (during long tool calls)
                def _safe_put(q, item):
                    try:
                        q.put_nowait(item)
                    except Exception:
                        pass  # Queue full — discard; prevents QueueFull crash
                loop.call_soon_threadsafe(
                    _safe_put, self.out_queue, {"data": data, "mime_type": "audio/pcm"}
                )
            elif jarvis_speaking:
                self.ui.set_audio_level(min(1.0, rms_val * 15))

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.01)  # 10ms — máxima responsividad del mic
        except Exception as e:
            print(f"[JARVIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Recv iniciado")
        out_buf, in_buf = [], []
        _first_chunk   = True
        _last_tool     = None   # track which tool was executing when error hit

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._stop_requested.is_set():
                            self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)
                                if _first_chunk:
                                    self.ui.clear_jarvis_response()
                                    _first_chunk = False
                                self.ui.stream_jarvis_chunk(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self._stop_requested.clear()
                            if self._turn_done_event:
                                self._turn_done_event.set()
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"Tú: {full_in}")
                                self._fire_phrase_triggers(full_in)
                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.send_telegram_response(full_out)
                            in_buf = []
                            out_buf = []
                            _first_chunk = True

                    if response.tool_call:
                        self.ui.clear_jarvis_response()
                        _first_chunk = True
                        fcs = response.tool_call.function_calls
                        for fc in fcs:
                            print(f"[JARVIS] 📞 {fc.name}")
                            _last_tool = fc.name
                        # Execute all tool calls in parallel when there are multiple
                        if len(fcs) > 1:
                            tasks = [asyncio.create_task(self._execute_tool(fc)) for fc in fcs]
                            fn_responses = list(await asyncio.gather(*tasks))
                        else:
                            fn_responses = [await self._execute_tool(fcs[0])]
                        try:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                            _last_tool = None  # only clear AFTER successful send
                        except Exception as tool_err:
                            print(f"[JARVIS] ❌ send_tool_response failed: {tool_err}")
                            raise
        except Exception as e:
            msg  = str(e)
            code = getattr(e, "status_code", 0) or getattr(e, "code", 0) or 0
            # Detect 1011 (internal server error) regardless of exception type
            if code == 1011 or "1011" in msg or "Internal error" in msg:
                tool_info = f" durante '{_last_tool}'" if _last_tool else ""
                print(f"[JARVIS] ⚡ API 1011{tool_info} — reconectando...")
                self._api_1011_tool = _last_tool
            else:
                print(f"[JARVIS] ❌ Recv: {e}")
                traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Play iniciado")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=PLAY_CHUNK_SIZE,
        )
        stream.start()

        # Jitter buffer: accumulate a few chunks before playback to prevent underruns
        _jitter_buf: list[bytes] = []
        _JITTER_TARGET = 1  # ~20ms — start playback ASAP for low latency

        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.05   # 50ms — faster turn-complete detection
                    )
                except asyncio.TimeoutError:
                    # Must check turn_done + empty BEFORE jitter guard,
                    # otherwise 1-2 stuck chunks in jitter_buf prevent
                    # ever reaching the turn_done check → infinite SPEAKING loop.
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        # Drain remaining jitter buffer before stopping
                        for buffered in _jitter_buf:
                            await asyncio.to_thread(stream.write, buffered)
                        _jitter_buf.clear()
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue

                self.set_speaking(True)
                _jitter_buf.append(chunk)

                # Once we have enough chunks buffered, drain them to the output stream
                if len(_jitter_buf) >= _JITTER_TARGET:
                    for buffered in _jitter_buf:
                        await asyncio.to_thread(stream.write, buffered)
                    _jitter_buf.clear()
        except Exception as e:
            print(f"[JARVIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        reconnect_delay   = 1.0
        consecutive_fails = 0

        while True:
            try:
                print("[JARVIS] 🔌 Conectando...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self._loop            = asyncio.get_event_loop()
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=5)  # buffer moderado — evita drops durante ráfagas de mic
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()

                    print("[JARVIS] ✅ Conectado.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS en línea.")
                    reconnect_delay   = 1.0   # reset backoff on successful connection
                    consecutive_fails = 0
                    self._api_1011_tool = None   # clear 1011 tool tracker

                    # ── First-connect extras ──────────────────────────────────
                    if self._first_connect:
                        self._first_connect = False
                        # Start Vision Guardian if enabled
                        try:
                            _start_vision_guardian(
                                inject_fn=self._inject_text,
                                speaking_fn=lambda: self._is_speaking,
                            )
                        except Exception as _vge:
                            print(f"[JARVIS] VisionGuardian init error: {_vge}")
                        # Auto morning brief (6am–12pm, once per day)
                        _hour = __import__("datetime").datetime.now().hour
                        if 6 <= _hour < 12 and not already_briefed_today():
                            async def _auto_brief():
                                await asyncio.sleep(1)  # let session settle
                                await self.session.send_client_content(
                                    turns={"parts": [{"text": "[AUTO] Dame el informe matutino del día."}]},
                                    turn_complete=True
                                )
                            tg.create_task(_auto_brief())

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._watch_reconnect())

            except Exception as e:
                exceptions = e.exceptions if isinstance(e, ExceptionGroup) else [e]

                is_handshake_timeout = False
                is_config_reconnect  = False
                for exc in exceptions:
                    msg = str(exc)
                    if "Config changed" in msg:
                        # Intentional reconnect triggered by config change — fast, no backoff
                        is_config_reconnect = True
                        consecutive_fails = 0
                    elif "timed out during opening handshake" in msg or (
                        isinstance(exc, TimeoutError) and "handshake" in msg
                    ):
                        # Timeout de WebSocket al conectar — error de red transitorio.
                        # NO incrementar consecutive_fails: sólo reintento rápido.
                        is_handshake_timeout = True
                        print(f"[JARVIS] ⏱️ Timeout al conectar — reintentando en 1s...")
                    elif "1011" in msg or "Internal error" in msg:
                        tool_hint = self._api_1011_tool or ""
                        print(f"[JARVIS] ⚡ API 1011{tool_hint and ' durante '+tool_hint} — reconectando...")
                        consecutive_fails += 1
                        if consecutive_fails >= 4:
                            self.ui.write_log(
                                "SYS: ⚠️ Error 1011 repetido. Esperando para no saturar la API...\n"
                                "SYS: Si persiste más de 2 min, reiniciá JARVIS."
                            )
                        elif tool_hint:
                            self.ui.write_log(f"SYS: Error de servidor al ejecutar '{tool_hint}'. Reconectando...")
                        else:
                            self.ui.write_log("SYS: Error de servidor 1011. Reconectando...")
                    elif "1008" in msg or "policy violation" in msg.lower() or "not found for API version" in msg:
                        # Model not available / wrong API version — log clearly, retry with same model
                        print(f"[JARVIS] ⚠️ Modelo no disponible en esta versión de API: {msg[:120]}")
                        self.ui.write_log("SYS: ⚠️ Modelo no disponible. Reintentando...")
                        consecutive_fails += 1
                    elif "1000" in msg or "going away" in msg.lower():
                        # Cierre normal de la sesión (expiró ~15 min) — silencioso
                        print(f"[JARVIS] 🔄 Sesión expirada — reconectando...")
                        consecutive_fails = 0   # reset: no es un fallo
                    else:
                        print(f"[JARVIS] ⚠️ {exc}")
                        traceback.print_exc()
                        consecutive_fails += 1

                if is_config_reconnect:
                    self.set_speaking(False)
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(0.5)
                    continue

                if is_handshake_timeout:
                    # Timeout en handshake → reintento fijo de 1s, sin backoff
                    self.set_speaking(False)
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(1.0)
                    continue

            self.set_speaking(False)
            self.ui.set_state("THINKING")

            # Exponential backoff con jitter para evitar thundering herd
            # After 5+ fails: wait up to 90s to let API rate limits recover
            if consecutive_fails > 1:
                max_delay = 90.0 if consecutive_fails >= 5 else 12.0
                reconnect_delay = min(reconnect_delay * 2, max_delay)
            elif consecutive_fails == 0:
                reconnect_delay = 1.0

            import random as _rnd
            jitter = _rnd.uniform(0, reconnect_delay * 0.25)
            total  = reconnect_delay + jitter
            print(f"[JARVIS] 🔄 Reconectando en {total:.1f}s...")
            await asyncio.sleep(total)

def main():
    # ── Single Instance Lock ──────────────────────────────────────────────────
    import ctypes
    global _single_instance_mutex
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "JARVIS_AI_SINGLE_INSTANCE_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("[JARVIS] Ya hay una instancia en ejecución. Cerrando.")
        sys.exit(0)

    # ── License check ─────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────

    # Load timezone from config
    _load_tz()

    def _show_welcome_and_keys():
        """Show Welcome dialog → API key dialog → return."""
        from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QPixmap

        app = QApplication.instance() or QApplication(sys.argv)

        # Check if keys already exist first
        cfg = {}
        if API_CONFIG_PATH.exists():
            try:
                cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass

        gemini = cfg.get("gemini_api_key", "").strip()
        openrouter = cfg.get("openrouter_api_key", "").strip()

        if gemini and openrouter:
            return "no_tutorial"

        # ── Welcome Dialog (only on first run, when no keys) ──
        welcome = QDialog()
        welcome.setWindowTitle("Bienvenido a JARVIS")
        welcome.setFixedSize(520, 460)
        welcome.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
        """)

        wl = QVBoxLayout(welcome)
        wl.setContentsMargins(32, 32, 32, 32)
        wl.setSpacing(12)

        title = QLabel("🤖  JARVIS AI")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #e94560; font-family: Segoe UI; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(title)

        subtitle = QLabel("Asistente personal con inteligencia artificial")
        subtitle.setStyleSheet("font-size: 14px; color: #a0a0b0; font-family: Segoe UI; border: none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(subtitle)

        wl.addSpacing(16)

        desc = QLabel(
            "JARVIS te permite controlar tu PC con voz y texto,\n"
            "ver la pantalla, procesar archivos, generar imágenes,\n"
            "conectarte con Telegram y mucho más.\n"
            "\n"
            "👤  Creado por Yonglly\n"
            "📦  Basado en el código original de Dexter-666 (JARVIS v1)\n"
            "💡  Modificado y mejorado con nuevas funcionalidades"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #c0c0d0; font-family: Segoe UI; line-height: 1.6; border: none;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(desc)

        wl.addStretch()

        credit = QLabel("✨  ¡Gracias Dexter-666 por la base del proyecto!  ✨")
        credit.setStyleSheet("font-size: 11px; color: #e94560; font-family: Segoe UI; font-style: italic; border: none;")
        credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wl.addWidget(credit)

        wl.addSpacing(8)

        next_btn = QPushButton("🚀  SIGUIENTE  →")
        next_btn.setStyleSheet("""
            QPushButton {
                background: #e94560; color: white; border: none; border-radius: 12px;
                padding: 14px 32px; font-size: 14px; font-weight: 700; font-family: Segoe UI;
            }
            QPushButton:hover { background: #c73652; }
        """)
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wl.addWidget(next_btn, 0, Qt.AlignmentFlag.AlignCenter)

        def _on_welcome_next():
            welcome.accept()

        next_btn.clicked.connect(_on_welcome_next)
        if welcome.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

        # ── API Key Dialog ──
        dlg = QDialog()
        dlg.setWindowTitle("Configuración Inicial de JARVIS")
        dlg.resize(480, 300)
        dlg.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
            }
        """)

        dl = QVBoxLayout(dlg)
        dl.setContentsMargins(32, 28, 32, 28)
        dl.setSpacing(10)

        title2 = QLabel("🔑  Configura tus API Keys")
        title2.setStyleSheet("font-size: 20px; font-weight: 700; color: #e94560; font-family: Segoe UI; border: none;")
        title2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(title2)

        info2 = QLabel("Necesitás tus claves de Gemini y OpenRouter para que JARVIS funcione.\n"
                       "Obtenelas gratis en makersuite.google.com y openrouter.ai")
        info2.setWordWrap(True)
        info2.setStyleSheet("font-size: 12px; color: #a0a0b0; font-family: Segoe UI; border: none;")
        info2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(info2)

        dl.addSpacing(8)

        lg = QLabel("Gemini API Key:")
        lg.setStyleSheet("font-size: 13px; color: #c0c0d0; font-weight: 600; font-family: Segoe UI; border: none;")
        dl.addWidget(lg)
        ig = QLineEdit()
        ig.setEchoMode(QLineEdit.EchoMode.Password)
        ig.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08); border: 1px solid #0f3460;
                border-radius: 10px; padding: 10px; color: white; font-size: 13px;
                font-family: Segoe UI;
            }
        """)
        dl.addWidget(ig)

        lo = QLabel("OpenRouter API Key:")
        lo.setStyleSheet("font-size: 13px; color: #c0c0d0; font-weight: 600; font-family: Segoe UI; border: none;")
        dl.addWidget(lo)
        io = QLineEdit()
        io.setEchoMode(QLineEdit.EchoMode.Password)
        io.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.08); border: 1px solid #0f3460;
                border-radius: 10px; padding: 10px; color: white; font-size: 13px;
                font-family: Segoe UI;
            }
        """)
        dl.addWidget(io)

        dl.addSpacing(8)

        def _on_api_save():
            g = ig.text().strip()
            o = io.text().strip()
            if not g or not o:
                QMessageBox.warning(dlg, "Error", "Ambas claves son obligatorias para continuar.")
                return
            cfg["gemini_api_key"] = g
            cfg["openrouter_api_key"] = o
            API_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            API_CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            dlg.accept()

        bs = QPushButton("💾  GUARDAR Y CONTINUAR")
        bs.setStyleSheet("""
            QPushButton {
                background: #e94560; color: white; border: none; border-radius: 12px;
                padding: 12px; font-size: 14px; font-weight: 700; font-family: Segoe UI;
            }
            QPushButton:hover { background: #c73652; }
        """)
        bs.setCursor(Qt.CursorShape.PointingHandCursor)
        bs.clicked.connect(_on_api_save)
        dl.addWidget(bs)

        result = dlg.exec()
        if result != QDialog.DialogCode.Accepted:
            sys.exit(0)
        return "show_tutorial"

    show_tutorial = _show_welcome_and_keys()

    ui = JarvisUI("face.png")

    # ── Show tutorial overlay on first run ──
    if show_tutorial == "show_tutorial":
        QTimer.singleShot(500, lambda: TutorialOverlay.show_tutorial(ui._win, ui._win))

    # --- UI COSMETICS PATCH ---
    try:
        if hasattr(ui, "_win"):
            # Aumentar transparencia (Glassmorphism)
            try:
                _opacity_cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
                _opacity_val = int(_opacity_cfg.get("window_opacity", 85)) / 100.0
            except Exception:
                _opacity_val = 0.85
            ui._win.setWindowOpacity(_opacity_val)
            # Reemplazar textos "Beta" y "Gratuito"
            from PyQt6.QtWidgets import QLabel
            for label in ui._win.findChildren(QLabel):
                text_lower = label.text().lower()
                if "beta" in text_lower or "gratuita" in text_lower or "gratuito" in text_lower or "premium" in text_lower:
                    try:
                        # Ocultar el contenedor completo del banner (incluye el botón PRO)
                        label.parentWidget().hide()
                    except:
                        label.hide()

            # 2. Add keyboard shortcut & Global Hotkey (INS / Insert key) to wake up JARVIS
            from PyQt6.QtGui import QKeySequence, QShortcut
            from PyQt6.QtCore import Qt, QTimer

            def on_shortcut_triggered():
                # Wake up / unmute JARVIS
                if hasattr(ui, "_win"):
                    # Si está muteado, desmutearlo para que escuche
                    if getattr(ui, "muted", False):
                        if hasattr(ui._win, "_toggle_mute"):
                            ui._win._toggle_mute()
                            ui.write_log("SYS: 🎤 Micrófono ACTIVADO vía atajo INS.")
                    else:
                        # Si ya está activo, mostrar/restaurar la ventana principal y enfocarla
                        if hasattr(ui._win, "showNormal"):
                            ui._win.showNormal()
                            ui._win.activateWindow()
                            ui.write_log("SYS: 🔔 JARVIS en foco vía atajo INS.")
                        
                        # Cambiar estado visual a escuchando
                        try:
                            ui.set_state("LISTENING")
                        except:
                            pass

            # A. PyQt Window Shortcut (for local window events)
            local_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Insert), ui._win)
            local_shortcut.activated.connect(on_shortcut_triggered)

            # B. Win32 Native Global Hotkey Hook (for background capture)
            def setup_global_hotkey():
                import threading
                import ctypes
                import ctypes.wintypes

                def hotkey_thread():
                    user32 = ctypes.windll.user32
                    # MOD_NOREPEAT = 0x4000
                    # VK_INSERT = 0x2D
                    try:
                        if not user32.RegisterHotKey(None, 99, 0x0000, 0x2D):
                            print("[HOTKEY] Error registering global Insert hotkey.")
                            return
                    except Exception as e:
                        print(f"[HOTKEY] Exception registering global hotkey: {e}")
                        return

                    try:
                        msg = ctypes.wintypes.MSG()
                        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                            if msg.message == 0x0312: # WM_HOTKEY
                                if msg.wParam == 99:
                                    # Thread-safely trigger UI callback inside PyQt event loop
                                    QTimer.singleShot(0, on_shortcut_triggered)
                            user32.TranslateMessage(ctypes.byref(msg))
                            user32.DispatchMessageW(ctypes.byref(msg))
                    finally:
                        user32.UnregisterHotKey(None, 99)

                threading.Thread(target=hotkey_thread, daemon=True).start()

            setup_global_hotkey()
            print("[PATCH] Avengers: Age of Ultron golden aesthetics & Insert global hotkey loaded successfully!")

    except Exception as e:
        print(f"[PATCH] Cosmetics & Shortcut patch failed: {e}")

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Apagando...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()