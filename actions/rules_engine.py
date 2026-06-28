"""rules_engine.py — Clean phrase-based automation and rules subsystem."""
import json
import time
import threading
from pathlib import Path
import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
RULES_PATH = BASE_DIR / "config" / "rules.json"

def rules_engine(parameters: dict, player=None) -> str:
    """Process dynamic rules settings."""
    action = parameters.get("action", "").lower()
    if action == "list":
        rules = _load_rules()
        if not rules:
            return "No hay reglas registradas."
        lines = ["Reglas registradas:"]
        for i, r in enumerate(rules, 1):
            name = r.get("name", "Sin nombre")
            cond = r.get("condition", {})
            act = r.get("action", {})
            lines.append(f"{i}. {name} — Condición: {json.dumps(cond, ensure_ascii=False)} — Acción: {json.dumps(act, ensure_ascii=False)}")
        return "\n".join(lines)

    elif action == "create":
        name = parameters.get("name")
        condition = parameters.get("condition")
        action_def = parameters.get("action_def")
        if not name or not condition or not action_def:
            return "Error: faltan parámetros (name, condition, action_def)."

        rules = _load_rules()
        rules.append({
            "name": name,
            "condition": condition,
            "action": action_def,
            "created": datetime.datetime.now().isoformat()
        })
        _save_rules(rules)
        return f"Regla '{name}' creada correctamente."

    elif action == "delete":
        name = parameters.get("name", "").strip()
        if not name:
            return "Error: falta el nombre de la regla a eliminar."
        rules = _load_rules()
        before = len(rules)
        rules = [r for r in rules if r.get("name", "") != name]
        if len(rules) == before:
            return f"No se encontró ninguna regla con el nombre '{name}'."
        _save_rules(rules)
        return f"Regla '{name}' eliminada."

    return "Comando no reconocido. Usá action=list, create o delete."

def start_rules_runner(player=None, speak=None) -> None:
    """Ejecuta reglas de inicio (startup) al arrancar JARVIS."""
    rules = _load_rules()
    startup_rules = [r for r in rules if r.get("condition", {}).get("type", "") == "startup"]
    if not startup_rules:
        return

    if player:
        player.write_log(f"⚡ Ejecutando {len(startup_rules)} regla(s) de inicio...")

    for rule in startup_rules:
        action = rule.get("action", {})
        _run_action(action, player=player)

def _load_rules() -> list[dict]:
    if not RULES_PATH.exists():
        return []
    try:
        data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        # Aceptar tanto lista como {"rules": [...]}
        if isinstance(data, dict) and "rules" in data:
            return data["rules"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []

def _save_rules(rules: list[dict]) -> None:
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps(rules, indent=4, ensure_ascii=False), encoding="utf-8")

def check_phrase_triggers(text: str) -> list[dict]:
    """Check text input against phrase triggers and return matching rule definitions."""
    rules = _load_rules()
    triggered = []
    text_lower = text.lower().strip()

    for rule in rules:
        condition = rule.get("condition", {})
        match_type = condition.get("match", "contains")
        trigger = condition.get("trigger", "").lower().strip()
        if not trigger:
            continue

        if match_type == "exact":
            if text_lower == trigger:
                triggered.append(rule)
        elif match_type == "startswith":
            if text_lower.startswith(trigger):
                triggered.append(rule)
        else:  # contains (default)
            if trigger in text_lower:
                triggered.append(rule)

    return triggered

def _run_action(action_def: dict, player=None) -> None:
    """Ejecuta las acciones de una regla en un hilo separado."""
    threading.Thread(
        target=_execute_action_def,
        args=(action_def, player),
        daemon=True
    ).start()

def _execute_action_def(action_def: dict, player=None) -> None:
    """Ejecuta acciones reales: abrir navegador, navegar a URL, etc."""
    import pyautogui

    def log(msg):
        if player:
            player.write_log(f"  {msg}")

    actions = action_def.get("actions", [action_def])

    for act in actions:
        act_type = act.get("type", "").lower()
        log(f"▶ Ejecutando: {act_type}")

        # browser → abre el navegador (opcional: navega a URL)
        if act_type == "browser":
            url = act.get("url", "")
            if url:
                pyautogui.hotkey("ctrl", "t")
                time.sleep(0.3)
                pyautogui.write(url, interval=0.03)
                time.sleep(0.1)
                pyautogui.press("enter")
                time.sleep(2)
            else:
                pyautogui.press("win")
                time.sleep(0.3)
                pyautogui.write("chrome", interval=0.05)
                time.sleep(0.5)
                pyautogui.press("enter")
                time.sleep(1.5)

        elif act_type == "open_app":
            app = act.get("app_name") or act.get("app") or ""
            if not app:
                log("  ⚠️ Sin nombre de app")
                continue
            log(f"  Abriendo {app}...")
            pyautogui.press("win")
            time.sleep(0.3)
            pyautogui.write(app, interval=0.05)
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(1.5)

        elif act_type == "open_browser":
            app = act.get("app", "chrome")
            log(f"  Abriendo {app}...")
            pyautogui.press("win")
            time.sleep(0.3)
            pyautogui.write(app, interval=0.05)
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(1.5)

        elif act_type == "open_url":
            url = act.get("url", "")
            if not url:
                continue
            pyautogui.hotkey("ctrl", "t")
            time.sleep(0.3)
            pyautogui.write(url, interval=0.03)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(2)

        elif act_type in ("navigate", "go_to"):
            url = act.get("url", "")
            if not url:
                continue
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.2)
            pyautogui.write(url, interval=0.03)
            time.sleep(0.1)
            pyautogui.press("enter")
            time.sleep(2)

        elif act_type == "new_tab":
            pyautogui.hotkey("ctrl", "t")
            time.sleep(0.3)

        elif act_type == "press":
            key = act.get("key", "enter")
            pyautogui.press(key)
            time.sleep(0.3)

        elif act_type == "hotkey":
            keys = act.get("keys", [])
            pyautogui.hotkey(*keys)
            time.sleep(0.3)

        elif act_type == "type":
            text = act.get("text", "")
            pyautogui.write(text, interval=0.02)
            time.sleep(0.3)

        elif act_type == "wait":
            seconds = act.get("seconds", 1)
            time.sleep(seconds)

        elif act_type == "notify":
            msg = act.get("message", "Notificación")
            log(f"  🔔 {msg}")

        elif act_type == "composite":
            sub_actions = act.get("actions", [])
            for sub in sub_actions:
                _execute_action_def({"actions": [sub]}, player=player)

        elif act_type == "run_script":
            command = act.get("command", "")
            if command:
                import subprocess
                try:
                    subprocess.Popen(command, shell=True)
                    log(f"  ▶ Script ejecutado: {command[:60]}")
                except Exception as e:
                    log(f"  ❌ Error: {e}")

        elif act_type == "music_play":
            log(f"  🎵 Reproducir música no implementado (conectá Spotify)")

        elif act_type == "smart_home":
            log(f"  🏠 Smart home no implementado")

        elif act_type == "speak":
            log(f"  🗣️ TTS: {act.get('message', '')}")

        else:
            log(f"  ⚠️ Tipo desconocido: {act_type}")

    log("✅ Regla ejecutada.")
