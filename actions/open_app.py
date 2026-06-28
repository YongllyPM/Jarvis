import os
import subprocess
import shutil

_MAPPINGS = {
    "notepad":               "notepad.exe",
    "bloc de notas":         "notepad.exe",
    "block de notas":        "notepad.exe",
    "calculator":            "calc.exe",
    "calculadora":           "calc.exe",
    "chrome":                "chrome.exe",
    "google chrome":         "chrome.exe",
    "brave":                 "brave.exe",
    "edge":                  "msedge.exe",
    "microsoft edge":        "msedge.exe",
    "explorer":              "explorer.exe",
    "explorador":            "explorer.exe",
    "explorador de archivos":"explorer.exe",
    "file explorer":         "explorer.exe",
    "cmd":                   "cmd.exe",
    "simbolo del sistema":   "cmd.exe",
    "simbolo de sistema":    "cmd.exe",
    "terminal":              "powershell.exe",
    "powershell":            "powershell.exe",
    "paint":                 "mspaint.exe",
    "word":                  "winword.exe",
    "excel":                 "excel.exe",
    "powerpoint":            "powerpnt.exe",
    "outlook":               "outlook.exe",
    "control panel":         "control.exe",
    "panel de control":      "control.exe",
    "task manager":          "taskmgr.exe",
    "administrador de tareas":"taskmgr.exe",
    "settings":              "ms-settings:",
    "configuracion":         "ms-settings:",
    "configuración":         "ms-settings:",
    "discord":               "Discord.exe",
    "spotify":               "Spotify.exe",
    "whatsapp":              "WhatsApp.exe",
    "telegram":              "Telegram.exe",
    "steam":                 "Steam.exe",
    "vscode":                "Code.exe",
    "visual studio code":    "Code.exe",
    "code":                  "Code.exe",
    "wordpad":               "wordpad.exe",
    "snipping tool":         "SnippingTool.exe",
    "recortes":              "SnippingTool.exe",
    "camera":                "WindowsCamera.exe",
    "camara":                "WindowsCamera.exe",
    "camara web":            "WindowsCamera.exe",
    "clock":                 "ms-clock:",
    "reloj":                 "ms-clock:",
    "alarms":                "ms-clock:",
    "alarmas":               "ms-clock:",
}


def open_app(parameters: dict, response=None, player=None) -> str:
    app_name = parameters.get("app_name", "").lower().strip()
    if not app_name:
        return "Indica el nombre de la aplicación."

    # Map to known executable / URI
    target = _MAPPINGS.get(app_name, app_name)

    try:
        # --- URI protocols (ms-settings:, ms-clock:) ---
        if target.startswith("ms-"):
            os.startfile(target)
            return f"Abriendo {app_name}."

        # --- Known executable via PATH ---
        full_path = shutil.which(target)
        if full_path:
            subprocess.Popen([full_path], shell=False)
            return f"{app_name} abierto."

        # --- Fallback: let Windows resolve it (App Execution Aliases, Store apps, etc.) ---
        #   start "" "name"  avoids the "start" title-parsing gotcha
        subprocess.Popen(f'start "" "{app_name}"', shell=True)
        return f"{app_name} abierto."

    except Exception as e:
        # Last resort: bare start command
        try:
            subprocess.Popen(["start", app_name], shell=True)
            return f"{app_name} abierto."
        except Exception:
            return f"No pude abrir '{app_name}': {e}"
