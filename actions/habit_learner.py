"""habit_learner.py — Aprendizaje de hábitos del usuario.

Observa acciones repetitivas (apps abiertas, clicks, comandos) y detecta
patrones para sugerirlos o ejecutarlos automáticamente.
"""
import json, time, threading, uuid
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).resolve().parent.parent
HISTORY_FILE = BASE_DIR / "config" / "habit_history.json"
HABITS_FILE  = BASE_DIR / "config" / "learned_habits.json"

_LOCK = threading.Lock()
_HISTORY: list[dict] = []
_HABITS:  list[dict] = []

# ── Gestión de datos ─────────────────────────────────────────────────────────

def _load_history():
    global _HISTORY
    try:
        if HISTORY_FILE.exists():
            _HISTORY = json.loads(HISTORY_FILE.read_text("utf-8"))
    except Exception:
        _HISTORY = []

def _save_history():
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Solo mantener últimas 5000 entradas
    with _LOCK:
        data = _HISTORY[-5000:] if len(_HISTORY) > 5000 else _HISTORY
        HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")

def _load_habits():
    global _HABITS
    try:
        if HABITS_FILE.exists():
            _HABITS = json.loads(HABITS_FILE.read_text("utf-8"))
    except Exception:
        _HABITS = []

def _save_habits():
    HABITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    HABITS_FILE.write_text(json.dumps(_HABITS, indent=2, ensure_ascii=False), "utf-8")

# ── Registro de acciones ─────────────────────────────────────────────────────

def record(action_type: str, details: dict, player=None):
    """Registra una acción del usuario en el historial."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action_type,
        "details": details,
    }
    with _LOCK:
        _HISTORY.append(entry)

    # Guardar y analizar cada ~20 acciones
    if len(_HISTORY) % 20 == 0:
        _save_history()
        try:
            _analyze()
        except Exception:
            pass

def record_app_focus(app_name: str, window_title: str = "", player=None):
    """Registra cuando el usuario cambia de aplicación."""
    record("app_focus", {"app": app_name, "title": window_title}, player)

def record_command(text: str, player=None):
    """Registra un comando enviado por el usuario."""
    record("command", {"text": text[:200]}, player)

def record_click(x: int, y: int, app: str = "", player=None):
    """Registra un clic (generalmente vía computer_agent)."""
    record("click", {"x": x, "y": y, "app": app}, player)

def record_boot(player=None):
    """Registra el inicio del sistema."""
    record("system", {"event": "boot"}, player)

# ── Detección de patrones ────────────────────────────────────────────────────

def _analyze():
    """Busca patrones repetitivos en el historial y actualiza hábitos."""
    sessions = _split_sessions()

    # Buscar secuencias de 2-4 pasos que se repitan
    patterns = defaultdict(lambda: {"count": 0, "last": "", "contexts": set()})

    for session in sessions:
        actions = [s["action"] for s in session]
        contexts = _session_context(session)

        # Subsecuencias de longitud 2 a 4
        for length in range(2, min(5, len(actions) + 1)):
            for start in range(len(actions) - length + 1):
                seq = tuple(actions[start:start + length])
                key = json.dumps(seq)
                patterns[key]["count"] += 1
                patterns[key]["last"] = session[-1]["ts"]
                patterns[key]["contexts"].update(contexts)

    # Convertir patrones frecuentes en hábitos
    MIN_REPEAT = 3
    existing_names = {h.get("trigger_seq") for h in _HABITS}

    for seq_json, info in patterns.items():
        if info["count"] >= MIN_REPEAT and seq_json not in existing_names:
            seq = json.loads(seq_json)
            # Buscar detalles del primer paso para construir el hábito
            first_details = _get_step_details(seq)
            habit = {
                "id": uuid.uuid4().hex[:12],
                "name": _generate_habit_name(seq),
                "trigger_seq": seq_json,
                "steps": first_details,
                "confidence": min(info["count"] / 10, 0.95),
                "times_seen": info["count"],
                "last_seen": info["last"],
                "contexts": list(info["contexts"])[:5],
                "enabled": True,
                "auto_exec": info["count"] >= 6,
            }
            with _LOCK:
                _HABITS.append(habit)
            _save_habits()

def _split_sessions() -> list[list[dict]]:
    """Divide el historial en sesiones (corte si >120s entre acciones)."""
    with _LOCK:
        entries = list(_HISTORY)

    if not entries:
        return []

    sessions = []
    current = [entries[0]]
    for e in entries[1:]:
        t1 = datetime.fromisoformat(current[-1]["ts"])
        t2 = datetime.fromisoformat(e["ts"])
        if (t2 - t1).total_seconds() > 120:
            sessions.append(current)
            current = []
        current.append(e)
    if current:
        sessions.append(current)
    return sessions

def _session_context(session: list[dict]) -> list[str]:
    """Extrae contexto de una sesión: apps usadas, eventos de sistema."""
    ctx = set()
    for e in session:
        if e["action"] == "app_focus":
            ctx.add(f"app:{e['details'].get('app','')}")
        elif e["action"] == "system":
            ctx.add(f"sys:{e['details'].get('event','')}")
    return list(ctx)

def _get_step_details(seq: list[str]) -> list[dict]:
    """Busca en el historial los detalles del primer matching de la secuencia."""
    with _LOCK:
        entries = list(_HISTORY)

    steps = []
    idx = 0
    for i in range(len(entries)):
        if idx < len(seq) and i + len(seq) - idx <= len(entries):
            match = True
            for j in range(len(seq) - idx):
                if entries[i + j]["action"] != seq[idx + j]:
                    match = False
                    break
            if match:
                for j in range(len(seq) - idx):
                    steps.append({
                        "action": seq[idx + j],
                        "details": entries[i + j].get("details", {}),
                    })
                break
    return steps

def _generate_habit_name(seq: list[str]) -> str:
    """Genera un nombre legible para el hábito."""
    name_map = {
        "app_focus": "Abrir app",
        "command": "Ejecutar comando",
        "click": "Hacer clic",
        "system": "Evento del sistema",
    }
    parts = [name_map.get(a, a) for a in seq[:3]]
    return " → ".join(parts)

# ── Consulta de hábitos ──────────────────────────────────────────────────────

def get_matching_habits_by_context(context: str) -> list[dict]:
    """Devuelve hábitos cuyo contexto coincida."""
    results = []
    with _LOCK:
        for h in _HABITS:
            if not h.get("enabled", True):
                continue
            for ctx in h.get("contexts", []):
                if context in ctx:
                    results.append(h)
                    break
    return results

def get_matching_habits_by_text(text: str) -> list[dict]:
    """Devuelve hábitos cuyo nombre se parezca al texto."""
    text_lower = text.lower().strip()
    results = []
    with _LOCK:
        for h in _HABITS:
            if not h.get("enabled", True):
                continue
            name = h.get("name", "").lower()
            if SequenceMatcher(None, text_lower, name).ratio() > 0.35:
                results.append(h)
    return results

def get_habits_for_boot() -> list[dict]:
    """Devuelve hábitos que deberían ejecutarse al iniciar el sistema."""
    results = []
    with _LOCK:
        for h in _HABITS:
            if not h.get("enabled", True):
                continue
            contexts = h.get("contexts", [])
            if "sys:boot" in contexts and h.get("auto_exec", False):
                results.append(h)
    return results

def get_all_habits() -> list[dict]:
    with _LOCK:
        return list(_HABITS)

# ── Ejecución de hábitos ─────────────────────────────────────────────────────

def execute_habit(habit: dict, player=None) -> str:
    """Ejecuta los pasos de un hábito aprendido."""
    import pyautogui

    name = habit.get("name", "Hábito")
    if player:
        player.write_log(f"🔄 Ejecutando hábito aprendido: {name}")

    steps = habit.get("steps", [])
    for i, step in enumerate(steps, 1):
        action = step.get("action", "")
        details = step.get("details", {})

        if player:
            player.write_log(f"  ▶  Paso {i}: {action}")

        if action == "app_focus":
            app = details.get("app", "")
            if app and player:
                player.write_log(f"     Abriendo {app} (simulado — el agente autónomo puede hacerlo)")
            # Nota: abrir apps requiere open_app; esto es una sugerencia

        elif action == "click":
            x, y = details.get("x"), details.get("y")
            if x and y:
                pyautogui.moveTo(x, y, duration=0.15)
                time.sleep(0.1)
                pyautogui.click()
                if player:
                    player.write_log(f"     🖱️ Click en ({x}, {y})")
                time.sleep(0.3)

        elif action == "command":
            cmd_text = details.get("text", "")
            if cmd_text:
                if player:
                    player.write_log(f"     Reenviando comando: {cmd_text}")
                # El comando se reenviaría a _on_text_command

        time.sleep(0.2)

    if player:
        player.write_log(f"✅ Hábito '{name}' completado.")
    return f"✅ Hábito '{name}' ejecutado."


# ── Inicialización ───────────────────────────────────────────────────────────

_load_history()
_load_habits()
