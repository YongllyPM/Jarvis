"""habits_tracker.py — Monitor de actividad en segundo plano + sugerencias.

Captura periódicamente la ventana activa, registra los hábitos del usuario
y sugiere automatizaciones cuando detecta patrones repetitivos.
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIVITY_FILE = BASE_DIR / "config" / "activity_log.json"
SUGGESTIONS_FILE = BASE_DIR / "config" / "suggested_automations.json"

_TRACKER_THREAD = None
_STOP_EVENT = threading.Event()
_PLAYER = None
_SPEAK = None

_POLL_INTERVAL = 8        # segundos entre capturas
_SUGGEST_INTERVAL = 3600  # segundos entre análisis de sugerencias (1 hora)
_MIN_PATTERN_DAYS = 2     # mínimo de días con el mismo patrón para sugerir
_ACTIVITY_RETENTION = 14  # días a conservar

# ── API Windows para obtener ventana activa ─────────────────────────────────

def _get_active_window_info() -> dict:
    """Devuelve {title, app} de la ventana activa en Windows."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return {"title": "", "app": ""}

    # Obtener título
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value

    # Obtener PID y nombre del proceso
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    try:
        # Abrir proceso para obtener el nombre
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if h_process:
            buf2 = ctypes.create_unicode_buffer(260)
            size = ctypes.c_ulong(260)
            kernel32.QueryFullProcessImageNameW(h_process, 0, buf2, ctypes.byref(size))
            kernel32.CloseHandle(h_process)
            app_path = buf2.value
            app = Path(app_path).stem if app_path else ""
        else:
            app = ""
    except Exception:
        app = ""

    # Categorización simple
    category = _categorize_app(app, title)

    return {"title": title, "app": app, "category": category, "hwnd": hwnd}


def _categorize_app(app: str, title: str) -> str:
    """Clasifica la aplicación en una categoría."""
    app_lower = app.lower()
    title_lower = title.lower()

    if app_lower in ("chrome", "firefox", "edge", "opera", "brave", "msedge"):
        return "navegador"
    if app_lower in ("outlook", " thunderbird", "mail"):
        return "correo"
    if app_lower in ("spotify", "yt music", "wmplayer", "vlc"):
        return "musica"
    if app_lower in ("code", "cursor", "webstorm", "pycharm", "vscodium"):
        return "desarrollo"
    if app_lower in ("winword", "excel", "powerpnt", "word", "excel", "powerpoint"):
        return "oficina"
    if app_lower in ("slack", "discord", "telegram", "whatsapp", "teams"):
        return "comunicacion"
    if app_lower in ("explorer",):
        return "explorador"
    if app_lower == "":
        return "desconocido"
    return "app"


# ── Registro de actividad ───────────────────────────────────────────────────

def _load_activity() -> list[dict]:
    if not ACTIVITY_FILE.exists():
        return []
    try:
        return json.loads(ACTIVITY_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_activity(log: list[dict]):
    ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Limpiar registros viejos
    cutoff = datetime.now(timezone.utc) - timedelta(days=_ACTIVITY_RETENTION)
    log = [e for e in log if datetime.fromisoformat(e["ts"]).replace(tzinfo=timezone.utc) > cutoff]
    ACTIVITY_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), "utf-8")


def _record_activity(info: dict):
    """Guarda una entrada de actividad."""
    log = _load_activity()
    log.append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "app": info.get("app", ""),
        "title": info.get("title", "")[:120],
        "category": info.get("category", ""),
    })
    _save_activity(log)


# ── Detección de patrones ───────────────────────────────────────────────────

def _detect_patterns(activity: list[dict]) -> list[dict]:
    """Analiza la actividad y devuelve patrones detectados."""
    if len(activity) < 20:
        return []

    patterns = []

    # 1. Apps más usadas por franja horaria
    hourly = defaultdict(lambda: defaultdict(int))
    for e in activity:
        try:
            hour = datetime.fromisoformat(e["ts"]).hour
        except Exception:
            continue
        app = e.get("app", "")
        if app:
            hourly[hour][app] += 1

    for hour, apps in hourly.items():
        total = sum(apps.values())
        for app, count in apps.items():
            if count > total * 0.6 and count >= 5:
                patterns.append({
                    "type": "app_hour",
                    "app": app,
                    "hour": hour,
                    "confidence": round(count / total, 2),
                })

    # 2. Secuencias de apps (ej: abrir Chrome → abrir Gmail)
    session_seq = _build_daily_sequences(activity)
    seq_counts = defaultdict(int)
    for seq in session_seq:
        key = " → ".join(seq[:4])
        seq_counts[key] += 1

    for seq_str, count in seq_counts.items():
        if count >= _MIN_PATTERN_DAYS:
            parts = seq_str.split(" → ")
            patterns.append({
                "type": "sequence",
                "steps": parts,
                "days_repeated": count,
                "confidence": min(count / 7, 0.95),
            })

    return patterns


def _build_daily_sequences(activity: list[dict]) -> list[list[str]]:
    """Agrupa actividad por día y extrae secuencias de apps."""
    days = defaultdict(list)
    for e in activity:
        try:
            day = datetime.fromisoformat(e["ts"]).strftime("%Y-%m-%d")
        except Exception:
            continue
        days[day].append(e)

    sequences = []
    for day, entries in sorted(days.items()):
        seen = set()
        seq = []
        for e in entries:
            app = e.get("app", "")
            if app and app not in seen:
                seq.append(app)
                seen.add(app)
        if len(seq) >= 2:
            sequences.append(seq)
    return sequences


# ── Motor de sugerencias ────────────────────────────────────────────────────

def _load_suggestions() -> list[dict]:
    if not SUGGESTIONS_FILE.exists():
        return []
    try:
        return json.loads(SUGGESTIONS_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_suggestions(suggestions: list[dict]):
    SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SUGGESTIONS_FILE.write_text(json.dumps(suggestions, indent=2, ensure_ascii=False), "utf-8")


def _get_suggestions() -> list[str]:
    """Genera sugerencias de automatización basadas en patrones detectados."""
    activity = _load_activity()
    patterns = _detect_patterns(activity)
    already = {s.get("rule_name") for s in _load_suggestions()}
    new_suggestions = []

    for p in patterns:
        if p["type"] == "app_hour":
            rule_name = f"Abrir {p['app']} a las {p['hour']}:00"
            if rule_name in already:
                continue
            new_suggestions.append({
                "rule_name": rule_name,
                "description": (f"Todos los días a las {p['hour']}:00 abrís {p['app']}. "
                                f"¿Querés que lo haga automáticamente?"),
                "condition": {"type": "time", "hour": p["hour"]},
                "action": {
                    "actions": [{"type": "open_app", "app": p["app"]}]
                },
                "confidence": p["confidence"],
            })

        elif p["type"] == "sequence":
            rule_name = " → ".join(p["steps"])
            if rule_name in already:
                continue
            actions = []
            for step in p["steps"]:
                if step in ("chrome", "firefox", "edge", "brave"):
                    actions.append({"type": "open_browser", "app": step})
                else:
                    actions.append({"type": "open_app", "app": step})
            new_suggestions.append({
                "rule_name": rule_name,
                "description": (f"Noté que seguís esta rutina: {' → '.join(p['steps'])}. "
                                f"¿Querés que la automatice?"),
                "condition": {"type": "startup"},
                "action": {"actions": actions},
                "confidence": p["confidence"],
            })

    if new_suggestions:
        all_suggestions = _load_suggestions() + new_suggestions
        _save_suggestions(all_suggestions)

    return [s["description"] for s in new_suggestions]


def _suggestion_loop():
    """Ciclo periódico de sugerencias."""
    last_check = 0
    while not _STOP_EVENT.is_set():
        now = time.time()
        if now - last_check >= _SUGGEST_INTERVAL:
            last_check = now
            try:
                suggestions = _get_suggestions()
                for msg in suggestions:
                    if _PLAYER:
                        _PLAYER.write_log(f"💡 Sugerencia: {msg}")
            except Exception as e:
                if _PLAYER:
                    _PLAYER.write_log(f"⚠️ Error en análisis de hábitos: {e}")
        _STOP_EVENT.wait(60)


# ── Monitor de ventana activa ──────────────────────────────────────────────

def _monitor_loop():
    """Ciclo principal: captura ventana activa cada N segundos."""
    from actions.habit_learner import record_app_focus

    last_info = {}
    idle_count = 0

    while not _STOP_EVENT.is_set():
        try:
            info = _get_active_window_info()
            app = info.get("app", "")
            title = info.get("title", "")

            # Si cambió de app o pasaron varios ciclos, registrar
            if app and (app != last_info.get("app") or idle_count >= 5):
                record_app_focus(app, title, player=_PLAYER)
                _record_activity(info)
                last_info = info
                idle_count = 0

                if _PLAYER and info.get("app"):
                    pass  # logging silencioso para no saturar

            elif app:
                idle_count += 1

        except Exception as e:
            if _PLAYER:
                _PLAYER.write_log(f"⚠️ Error en monitor: {e}")

        _STOP_EVENT.wait(_POLL_INTERVAL)


# ── API pública ─────────────────────────────────────────────────────────────

def start_tracker(player=None, speak=None):
    """Inicia el monitor de actividad en segundo plano."""
    global _TRACKER_THREAD, _PLAYER, _SPEAK, _STOP_EVENT

    if _TRACKER_THREAD and _TRACKER_THREAD.is_alive():
        return  # ya está corriendo

    _STOP_EVENT.clear()
    _PLAYER = player
    _SPEAK = speak

    _TRACKER_THREAD = threading.Thread(target=_monitor_loop, daemon=True, name="habits-tracker")
    _TRACKER_THREAD.start()

    # Hilo de sugerencias (corre cada hora)
    _sug_thread = threading.Thread(target=_suggestion_loop, daemon=True, name="habits-suggester")
    _sug_thread.start()

    if player:
        player.write_log("📊 Monitor de hábitos iniciado (ventana activa cada 8s)")


def stop_tracker():
    """Detiene el monitor."""
    _STOP_EVENT.set()


def get_activity_summary() -> str:
    """Devuelve un resumen de actividad reciente."""
    activity = _load_activity()
    if not activity:
        return "No hay datos de actividad todavía."

    # Últimas 24 horas
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = [e for e in activity if datetime.fromisoformat(e["ts"]).replace(tzinfo=timezone.utc) > cutoff]

    app_count = defaultdict(int)
    for e in recent:
        app_count[e.get("app", "?")] += 1

    top = sorted(app_count.items(), key=lambda x: -x[1])[:10]
    lines = ["📊 Actividad reciente (últimas 24h):"]
    for app, count in top:
        lines.append(f"  • {app}: {count} veces")
    return "\n".join(lines)
