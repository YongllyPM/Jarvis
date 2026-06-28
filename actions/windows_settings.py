"""windows_settings.py — Real Windows system settings control."""
import os
import subprocess
import logging

logger = logging.getLogger("windows_settings")

_ACTION_MAP = {
    "bluetooth": lambda a: _toggle_setting("bluetooth"),
    "wifi":      lambda a: _toggle_setting("wifi"),
    "night":     lambda a: _toggle_setting("nightlight"),
    "airplane":  lambda a: _toggle_setting("airplanemode"),
    "dark":      lambda a: _run_ms("ms-settings:personalization-colors"),
    "display":   lambda a: _run_ms("ms-settings:display"),
    "sound":     lambda a: _run_ms("ms-settings:sound"),
    "network":   lambda a: _run_ms("ms-settings:network"),
    "update":    lambda a: _run_ms("ms-settings:windowsupdate"),
    "about":     lambda a: _run_ms("ms-settings:about"),
}


def _run_ms(uri: str) -> str:
    try:
        subprocess.Popen(["start", uri], shell=True)
        return f"Abriendo configuración de Windows."
    except Exception as e:
        return f"Error: {e}"


def _toggle_setting(name: str) -> str:
    """Open the quick actions flyout (Win+A) as a generic toggle approach."""
    try:
        import pyautogui
        pyautogui.hotkey("win", "a")
        return f"Abriendo Centro de acciones para ajustar {name}."
    except Exception as e:
        return f"Error: {e}"


def windows_settings(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    if not action:
        return "Acción requerida."

    handler = _ACTION_MAP.get(action)
    if handler:
        try:
            return handler(parameters)
        except Exception as e:
            logger.exception("windows_settings error")
            return f"Error al ejecutar '{action}': {e}"

    return f"Acción desconocida: {action}"
