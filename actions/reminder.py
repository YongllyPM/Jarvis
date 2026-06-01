"""reminder.py — Recordatorios con lenguaje natural y lista en tiempo real."""
import re
import threading
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

_REMINDERS_PATH = Path(__file__).resolve().parent.parent / "memory" / "reminders.json"

_active_reminders: list[dict] = []
_listener = None

def _ensure_file():
    _REMINDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _REMINDERS_PATH.exists():
        _REMINDERS_PATH.write_text("[]", encoding="utf-8")

def _load() -> list[dict]:
    _ensure_file()
    try:
        return json.loads(_REMINDERS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def _save(reminders: list[dict]):
    _ensure_file()
    _REMINDERS_PATH.write_text(json.dumps(reminders, indent=2, ensure_ascii=False), encoding="utf-8")

def list_reminders() -> list[dict]:
    return _load()

def _parse_natural_time(text: str):
    text = text.lower().strip()

    # "en X minutos / segundos / horas / min / s / h"
    m = re.search(r'en\s+(\d+)\s*(minutos?|min|m|segundos?|s|horas?|h)', text)
    if m:
        val = int(m.group(1))
        unit = m.group(2)[0]
        if unit in ("s",):
            return datetime.now() + timedelta(seconds=val)
        elif unit in ("m",):
            return datetime.now() + timedelta(minutes=val)
        else:
            return datetime.now() + timedelta(hours=val)

    # "a las XX:YY" o "a las XX"
    m = re.search(r'a\s*las\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        ampm = m.group(3)
        now = datetime.now()
        if ampm:
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        target = now.replace(hour=hour, minute=minute, second=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "en X minutos" (without space, e.g. "en 20min")
    m = re.search(r'en\s+(\d+)\s*(min|s|h)\b', text)
    if m:
        val = int(m.group(1))
        unit = m.group(2)
        if unit == "s":
            return datetime.now() + timedelta(seconds=val)
        elif unit == "min":
            return datetime.now() + timedelta(minutes=val)
        else:
            return datetime.now() + timedelta(hours=val)

    # Plain number + unit ("20 minutos", "1 hora")
    m = re.search(r'(\d+)\s*(minutos?|min|segundos?|s|horas?|h)', text)
    if m:
        val = int(m.group(1))
        unit = m.group(2)[0]
        if unit in ("s",):
            return datetime.now() + timedelta(seconds=val)
        elif unit in ("m",):
            return datetime.now() + timedelta(minutes=val)
        else:
            return datetime.now() + timedelta(hours=val)

    return None


def reminder(parameters: dict, response=None, player=None) -> str:
    text = parameters.get("message", "").strip()
    time_raw = parameters.get("time_str", "") or parameters.get("time", "")

    if not text:
        text = "Recordatorio"

    target = None

    if time_raw:
        target = _parse_natural_time(time_raw)

    if not target:
        target = datetime.now() + timedelta(minutes=1)

    entry = {
        "id": int(time.time() * 1000) % 100000,
        "message": text,
        "time": target.isoformat(),
        "created": datetime.now().isoformat(),
        "done": False
    }

    reminders = _load()
    reminders.append(entry)
    _save(reminders)

    delay = (target - datetime.now()).total_seconds()

    def _run():
        if delay > 0:
            time.sleep(delay)
        reminders = _load()
        for r in reminders:
            if r["id"] == entry["id"]:
                r["done"] = True
                break
        _save(reminders)
        if player:
            try:
                import winsound
                winsound.PlaySound("SystemExclamation", winsound.SND_ALIAS | winsound.SND_ASYNC)
            except Exception:
                pass
            player.write_log(f"⏰ Recordatorio: {text}")
            player.speak(f"Señor, recordatorio: {text}")

    threading.Thread(target=_run, daemon=True).start()

    remaining = _format_delta(delay)
    return f"✅ Recordatorio programado: '{text}' en {remaining}."


def _format_delta(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)} segundos"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minutos"
    hours = minutes // 60
    mins = minutes % 60
    if mins:
        return f"{hours} hora(s) {mins} min"
    return f"{hours} hora(s)"
