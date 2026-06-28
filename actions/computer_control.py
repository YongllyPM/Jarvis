"""computer_control.py — Real keyboard/mouse/desktop control using pyautogui."""
import pyautogui
import logging

logger = logging.getLogger("computer_control")

# ── Map friendly action names to pyautogui methods ──────────────────────────

_ACTION_MAP = {
    "press":        lambda a: pyautogui.press(a.get("key", "enter")),
    "hotkey":       lambda a: pyautogui.hotkey(*a.get("keys", "enter").split("+")),
    "type":         lambda a: pyautogui.typewrite(a.get("text", ""), interval=0.02),
    "smart_type":   lambda a: _smart_type(a),
    "click":        lambda a: pyautogui.click(a.get("x", None), a.get("y", None)),
    "double_click": lambda a: pyautogui.doubleClick(a.get("x", None), a.get("y", None)),
    "right_click":  lambda a: pyautogui.rightClick(a.get("x", None), a.get("y", None)),
    "scroll":       lambda a: _do_scroll(a),
    "move":         lambda a: pyautogui.moveTo(a.get("x", 0), a.get("y", 0), duration=0.2),
    "copy":         lambda a: _copy(),
    "paste":        lambda a: _paste(),
    "screenshot":   lambda a: _screenshot(a),
    "wait":         lambda a: pyautogui.sleep(a.get("seconds", 1)),
    "clear_field":  lambda a: _clear_field(a),
    "focus_window": lambda a: _focus_window(a),
}

_MEDIA_MAP = {
    "volumen":     lambda: pyautogui.press("volumeup", presses=5),
    "bajar":       lambda: pyautogui.press("volumedown", presses=5),
    "silenciar":   lambda: pyautogui.press("volumemute"),
    "playpause":   lambda: pyautogui.press("playpause"),
    "siguiente":   lambda: pyautogui.press("nexttrack"),
    "anterior":    lambda: pyautogui.press("prevtrack"),
}


def _smart_type(a):
    text = a.get("text", "")
    if a.get("clear_first", True):
        pyautogui.hotkey("ctrl", "a")
        pyautogui.sleep(0.05)
        pyautogui.press("delete")
    pyautogui.typewrite(text, interval=0.01)


def _do_scroll(a):
    d = a.get("direction", "down").lower()
    amt = a.get("amount", 3)
    clicks = amt if d in ("down", "right") else -amt
    pyautogui.scroll(clicks)


def _copy():
    pyautogui.hotkey("ctrl", "c")
    return "Copiado al portapapeles."


def _paste():
    pyautogui.hotkey("ctrl", "v")
    return "Pegado."


def _screenshot(a):
    path = a.get("path")
    if not path:
        from datetime import datetime
        from pathlib import Path
        path = str(Path.home() / "Desktop" / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    pyautogui.screenshot(path)
    return f"Captura guardada en {path}"


def _clear_field(a):
    pyautogui.tripleClick()
    pyautogui.press("delete")


def _focus_window(a):
    title = a.get("title", "")
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(title)
        if wins:
            wins[0].activate()
            return f"Ventana '{title}' enfocada."
        return f"No se encontró ventana: {title}"
    except Exception as e:
        return f"Error al enfocar ventana: {e}"


def computer_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    text = parameters.get("text", "").lower().strip()

    if not action:
        return "Acción requerida."

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    # ── Media/volume shortcuts via text ──
    if action == "smart_type" and player:
        for keyword, handler in _MEDIA_MAP.items():
            if keyword in text:
                handler()
                return f"Comando '{keyword}' ejecutado."

    # ── Direct action ──
    handler = _ACTION_MAP.get(action)
    if handler:
        try:
            result = handler(parameters)
            return result or f"Acción '{action}' ejecutada."
        except Exception as e:
            logger.exception("computer_control error")
            return f"Error al ejecutar '{action}': {e}"

    return f"Acción desconocida: {action}"
