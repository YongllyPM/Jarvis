import os
import json
import re
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "config" / "knowledge"
_KNOWLEDGE_FILE = _KNOWLEDGE_DIR / "knowledge_base.json"


def _ensure_file():
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    if not _KNOWLEDGE_FILE.exists():
        _KNOWLEDGE_FILE.write_text("[]", encoding="utf-8")


def _load() -> list[dict]:
    _ensure_file()
    try:
        return json.loads(_KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save(data: list[dict]):
    _ensure_file()
    _KNOWLEDGE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _search(entries: list[dict], query: str) -> list[dict]:
    query = query.lower()
    results = []
    for e in entries:
        text = json.dumps(e, ensure_ascii=False).lower()
        if query in text:
            results.append(e)
    return results


def knowledge_base(parameters: dict, player=None) -> str:
    action = parameters.get("action", "search")
    topic = parameters.get("topic", "")
    key = parameters.get("key", "")
    value = parameters.get("value", "")

    data = _load()

    try:
        if action == "search":
            if not topic:
                total = len(data)
                return f"Base de conocimiento: {total} entradas almacenadas. Usá 'topic' para buscar."
            results = _search(data, topic)
            if not results:
                return f"No encontré información sobre '{topic}'."
            out = []
            for r in results[:10]:
                out.append(f"- {r.get('topic', r.get('key', '?'))}: {r.get('value', r.get('info', ''))}")
            return "\n".join(out)

        elif action == "add":
            if not key or not value:
                return "Necesito 'key' y 'value' para agregar conocimiento."
            entry = {"topic": topic or key, "key": key, "value": value}
            # Evitar duplicados: actualizar si existe misma key
            for i, e in enumerate(data):
                if e.get("key") == key:
                    data[i] = entry
                    _save(data)
                    return f"Conocimiento actualizado: '{key}'."
            data.append(entry)
            _save(data)
            return f"Conocimiento guardado: '{key}'."

        elif action == "delete":
            if not topic and not key:
                return "Indica 'topic' o 'key' para eliminar."
            before = len(data)
            data[:] = [e for e in data if not (
                (topic and topic.lower() in e.get("topic", "").lower()) or
                (key and e.get("key") == key)
            )]
            removed = before - len(data)
            _save(data)
            return f"{removed} entradas eliminadas."

        elif action == "list":
            if not data:
                return "La base de conocimiento está vacía."
            topics = [e.get("topic", e.get("key", "?")) for e in data]
            return "Temas almacenados:\n  " + "\n  ".join(sorted(set(topics)))

        elif action == "clear":
            _save([])
            return "Base de conocimiento limpiada."

        else:
            return f"Acción '{action}' no reconocida. Acciones: search, add, delete, list, clear."

    except Exception as e:
        return f"Error en base de conocimiento: {e}"
