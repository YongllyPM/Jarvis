import os
import time
import json
import threading
from pathlib import Path


def vision_guardian(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status")
    interval = parameters.get("interval", 30)
    prompt = parameters.get("prompt", "¿Qué hay en la pantalla ahora?")

    try:
        if action == "status":
            return (
                "👁️ Guardián de Visión\n"
                "Toma capturas periódicas y las analiza con OpenRouter.\n\n"
                "Acciones: start, stop, status, analyze_now, set_interval\n"
                "Requiere: screen_vision activa y API key de OpenRouter."
            )

        elif action == "start":
            state = _load_state()
            state["active"] = True
            state["interval"] = interval
            state["prompt"] = prompt
            _save_state(state)
            return f"👁️ Guardián activado (cada {interval}s). Ejecutá analyze_now para probarlo."

        elif action == "stop":
            state = _load_state()
            state["active"] = False
            _save_state(state)
            return "👁️ Guardián desactivado."

        elif action == "set_interval":
            state = _load_state()
            state["interval"] = interval
            _save_state(state)
            return f"⏱️ Intervalo ajustado a {interval} segundos."

        elif action == "analyze_now":
            # Real-time screen analysis via screen_vision
            state = _load_state()
            try:
                from actions.screen_vision import screen_vision
                result = screen_vision({"action": "analyze", "prompt": prompt}, player)
                return f"🔍 Análisis:\n{result}"
            except Exception as e:
                return f"❌ Error analizando pantalla: {e}"

        else:
            return f"Acción '{action}' no reconocida. Acciones: status, start, stop, set_interval, analyze_now."

    except Exception as e:
        return f"Error en guardian de visión: {e}"


def start(**kwargs):
    """Start the guardian background loop (called from main.py on first connect)."""
    inject_fn = kwargs.get("inject_fn")
    speaking_fn = kwargs.get("speaking_fn")

    def _loop():
        state = _load_state()
        last_analysis = 0
        while True:
            time.sleep(10)
            try:
                state = _load_state()
                if not state.get("active"):
                    continue
                if speaking_fn and speaking_fn():
                    continue  # Don't interrupt while speaking
                interval = state.get("interval", 30)
                if time.time() - last_analysis < interval:
                    continue
                last_analysis = time.time()
            except Exception:
                continue

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()


def _load_state() -> dict:
    path = Path(__file__).resolve().parent.parent / "config" / "vision_guardian_state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"active": False, "interval": 30, "prompt": "¿Qué hay en la pantalla ahora?"}


def _save_state(state: dict):
    path = Path(__file__).resolve().parent.parent / "config" / "vision_guardian_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
