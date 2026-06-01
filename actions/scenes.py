"""scenes.py — Atajos de voz personalizados (escenas multi-acción)."""
import json
import threading
from pathlib import Path

_SCENES_PATH = Path(__file__).resolve().parent.parent / "config" / "scenes.json"

def _ensure():
    _SCENES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _SCENES_PATH.exists():
        _SCENES_PATH.write_text("{}", encoding="utf-8")

def _load() -> dict:
    _ensure()
    try:
        return json.loads(_SCENES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save(scenes: dict):
    _ensure()
    _SCENES_PATH.write_text(json.dumps(scenes, indent=2, ensure_ascii=False), encoding="utf-8")

def list_scenes() -> dict:
    return _load()

def scenes_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    name = parameters.get("name", "").strip()

    scenes = _load()

    if action == "list":
        if not scenes:
            return "No hay escenas configuradas."
        lines = ["🎬 Escenas disponibles:"]
        for sname, sdata in scenes.items():
            actions_str = ", ".join(a.get("type", "?") for a in sdata.get("actions", []))
            lines.append(f"  • {sname}: {actions_str}")
        return "\n".join(lines)

    elif action == "run":
        if not name or name not in scenes:
            return f"Escena '{name}' no encontrada."
        scene = scenes[name]
        threading.Thread(target=_execute_scene, args=(scene, player), daemon=True).start()
        return f"🎬 Ejecutando escena '{name}'..."

    elif action == "create" or action == "save":
        actions_raw = parameters.get("actions", [])
        if not name:
            return "Se requiere 'name' para la escena."
        if not actions_raw:
            return "Se requiere 'actions' (lista de acciones)."
        scenes[name] = {"actions": actions_raw}
        _save(scenes)
        return f"✅ Escena '{name}' guardada."

    elif action == "delete":
        if name in scenes:
            del scenes[name]
            _save(scenes)
            return f"🗑️ Escena '{name}' eliminada."
        return f"Escena '{name}' no encontrada."

    else:
        return f"Acción '{action}' no reconocida. Usa: list, run, create, delete."


def _execute_scene(scene: dict, player=None):
    for step in scene.get("actions", []):
        step_type = step.get("type", "").lower()
        try:
            if step_type == "open_app":
                from actions.open_app import open_app
                open_app({"app_name": step.get("app_name", "")}, player)
            elif step_type == "music_play":
                _call_music({"action": "play", "query": step.get("query", "")}, player)
            elif step_type == "browser":
                _call_browser({"action": "go_to", "url": step.get("url", "https://google.com")}, player)
            elif step_type == "speak":
                if player and hasattr(player, "speak"):
                    player.speak(step.get("message", ""))
            elif step_type == "wait":
                import time as _t
                _t.sleep(int(step.get("seconds", 1)))
        except Exception:
            pass
        import time as _t
        _t.sleep(0.3)

def _call_music(params, player):
    try:
        from actions.music_controller import music_control
        music_control(params, player)
    except Exception:
        pass

def _call_browser(params, player):
    try:
        from actions.browser_control import browser_control
        browser_control(params, player)
    except Exception:
        pass
