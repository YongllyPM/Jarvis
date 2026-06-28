import re
import threading
import time
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

_SCHEDULE_FILE = Path(__file__).resolve().parent.parent / "config" / "scheduled_tasks.json"
_scheduler_running = False


def _ensure_file():
    _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _SCHEDULE_FILE.exists():
        _SCHEDULE_FILE.write_text("[]", encoding="utf-8")


def _load() -> list[dict]:
    _ensure_file()
    try:
        return json.loads(_SCHEDULE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save(data: list[dict]):
    _ensure_file()
    _SCHEDULE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_time(t_str: str) -> datetime | None:
    now = datetime.now()
    t_str = t_str.lower().strip()

    # "en X minutos/segundos/horas"
    m = re.search(r"(\d+)\s*(min|minuto|minutos|s|seg|segundo|segundos|h|hora|horas)", t_str)
    if m:
        n = int(m.group(1))
        unit = m.group(2)[0]
        if unit in ("m", "i"):
            return now + timedelta(minutes=n)
        elif unit == "s":
            return now + timedelta(seconds=n)
        else:
            return now + timedelta(hours=n)

    # "a las HH:MM"
    m = re.search(r"(\d{1,2}):(\d{2})", t_str)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        target = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target

    # "en X dias"
    m = re.search(r"(\d+)\s*(d|dia|dias)", t_str)
    if m:
        return now + timedelta(days=int(m.group(1)))

    return None


def scheduler(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "list")
    task_id = parameters.get("task_id", "")
    time_str = parameters.get("time", "")
    message = parameters.get("message", "")
    command = parameters.get("command", "")

    data = _load()

    try:
        if action == "add":
            if not time_str:
                return "Necesito 'time' para programar (ej: 'en 5 minutos', 'a las 14:30')."
            target = _parse_time(time_str)
            if not target:
                return f"No entendí la hora: '{time_str}'. Usá formato como 'en 5 minutos' o 'a las 14:30'."

            task = {
                "id": str(int(time.time())),
                "time": target.isoformat(),
                "message": message or "Tarea programada",
                "command": command,
                "created": datetime.now().isoformat(),
            }
            data.append(task)
            _save(data)
            return f"Tarea programada para {target.strftime('%d/%m/%Y %H:%M')}: {task['message']}"

        elif action == "list":
            now = datetime.now()
            lines = []
            for t in data:
                dt = datetime.fromisoformat(t["time"])
                status = "⏰ pendiente" if dt > now else "✅ vencida"
                lines.append(f"  [{t['id']}] {t['message']} → {dt.strftime('%d/%m %H:%M')} {status}")
            if not lines:
                return "No hay tareas programadas."
            return "Tareas:\n" + "\n".join(lines)

        elif action == "delete":
            if not task_id:
                return "Indica 'task_id' a eliminar."
            before = len(data)
            data[:] = [t for t in data if t["id"] != task_id]
            _save(data)
            return "Tarea eliminada." if len(data) < before else f"Tarea '{task_id}' no encontrada."

        elif action == "clear":
            _save([])
            return "Todas las tareas eliminadas."

        else:
            return f"Acción '{action}' no reconocida. Acciones: add, list, delete, clear."

    except Exception as e:
        return f"Error en scheduler: {e}"


def start_runner(player=None, speak=None):
    _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_run_loop, args=(player, speak), daemon=True).start()


def _run_loop(player=None, speak=None):
    global _scheduler_running
    if _scheduler_running:
        return
    _scheduler_running = True
    try:
        while True:
            now = datetime.now()
            data = _load()
            changed = False
            for t in data[:]:
                dt = datetime.fromisoformat(t["time"])
                if dt <= now:
                    msg = f"⏰ Recordatorio: {t['message']}"
                    if player:
                        player.write_log(msg)
                    if speak:
                        speak(msg)
                    if t.get("command"):
                        try:
                            subprocess.Popen(t["command"], shell=True)
                        except Exception:
                            pass
                    data.remove(t)
                    changed = True
            if changed:
                _save(data)
            time.sleep(10)
    except Exception:
        pass
    finally:
        _scheduler_running = False
