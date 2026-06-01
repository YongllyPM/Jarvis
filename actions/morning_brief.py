"""morning_brief.py — Informe matutino automático con datos reales."""
import json
from datetime import datetime, date
from pathlib import Path

_BRIEF_STATE = Path(__file__).resolve().parent.parent / "config" / "morning_brief_state.json"

def _get_state() -> dict:
    try:
        return json.loads(_BRIEF_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_date": ""}

def _set_state(data: dict):
    _BRIEF_STATE.parent.mkdir(parents=True, exist_ok=True)
    _BRIEF_STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def already_briefed_today() -> bool:
    state = _get_state()
    return state.get("last_date", "") == date.today().isoformat()

def mark_briefed():
    state = _get_state()
    state["last_date"] = date.today().isoformat()
    _set_state(state)

def _get_weather() -> str:
    try:
        from actions.weather_report import weather_action
        city = ""
        result = weather_action({"city": city})
        if result:
            return result[:200]
    except Exception:
        pass
    return ""

def _get_calendar() -> list[dict]:
    try:
        from actions.google_calendar import google_calendar
        result = google_calendar({"action": "list", "days_ahead": 1})
        if result and isinstance(result, str):
            return result
    except Exception:
        pass
    return ""

def _get_todos() -> str:
    try:
        from actions.reminder import list_reminders
        reminders = list_reminders()
        active = [r for r in reminders if not r.get("done", False)]
        if active:
            return f"Tienes {len(active)} recordatorio(s) pendiente(s)."
    except Exception:
        pass
    return ""

def morning_brief(parameters: dict, player=None) -> str:
    parts = ["☀️ Buenos días, señor."]

    weather = _get_weather()
    if weather:
        parts.append(f"Clima: {weather}")

    calendar = _get_calendar()
    if calendar:
        parts.append(f"Calendario: {calendar}")

    todos = _get_todos()
    if todos:
        parts.append(f"Tareas: {todos}")

    brief = "\n".join(parts)

    if player:
        # player.write_log(f"📋 Informe matutino:\n{brief}") # Comentado para evitar error
        # player.speak(brief) # Comentado para evitar error
        pass

    mark_briefed()
    return brief
