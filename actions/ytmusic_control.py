"""ytmusic_control.py — YouTube Music controller using ytmusicapi + keyboard shortcuts."""
import time
import re

def _get_ytmusic():
    try:
        from ytmusicapi import YTMusic
        return YTMusic()
    except Exception:
        return None


def ytmusic_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    if not action:
        return "El parámetro action es obligatorio."

    try:
        import pyautogui

        if action in ("play", "pause", "toggle"):
            pyautogui.press("playpause")
            return "Reproducción alternada."

        elif action in ("next", "skip"):
            pyautogui.press("nexttrack")
            return "Canción siguiente."

        elif action in ("prev", "previous", "back"):
            pyautogui.press("prevtrack")
            return "Canción anterior."

        elif action == "volume":
            value = parameters.get("value", "")
            if "up" in str(value).lower():
                pyautogui.press("volumeup", presses=5)
                return "Volumen aumentado."
            elif "down" in str(value).lower():
                pyautogui.press("volumedown", presses=5)
                return "Volumen disminuido."
            else:
                return f"Ajuste de volumen requiere dirección: {value}"

        elif action in ("search", "play"):
            query = parameters.get("query", "")
            if not query:
                return "Se requiere 'query' para buscar."
            yt = _get_ytmusic()
            if not yt:
                return "No se pudo conectar con YouTube Music."
            results = yt.search(query, limit=5)
            if not results:
                return f"No se encontraron resultados para '{query}'."
            lines = [f"Resultados para '{query}':"]
            for i, r in enumerate(results[:5], 1):
                title = r.get("title", "?")
                artist = r.get("artists", [{}])[0].get("name", "?") if r.get("artists") else "?"
                lines.append(f"  {i}. {title} — {artist}")
            return "\n".join(lines)

        elif action == "current":
            yt = _get_ytmusic()
            if not yt:
                return "No se pudo conectar con YouTube Music."
            try:
                current = yt.get_liked_songs(limit=1)
                return "Revisa YouTube Music para ver la canción actual."
            except Exception:
                return "No se pudo obtener la canción actual."

        elif action == "like":
            yt = _get_ytmusic()
            if not yt:
                return "No se pudo conectar con YouTube Music."
            return "Acción 'like' requiere integración más profunda con la API de YT Music."

        else:
            return f"Acción '{action}' no reconocida."

    except Exception as e:
        return f"Error en control de YouTube Music: {e}"
