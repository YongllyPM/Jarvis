import subprocess
import os
import json


def game_updater(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "check")
    game = parameters.get("game", "")
    platform = parameters.get("platform", "")

    try:
        if action == "check":
            # Check running games
            ps = "Get-Process | Where-Object { $_.MainWindowTitle -ne '' } | Select-Object Name, MainWindowTitle, StartTime | ConvertTo-Json"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=10
            )
            try:
                processes = json.loads(r.stdout) if r.stdout.strip() else []
                if isinstance(processes, dict):
                    processes = [processes]
            except json.JSONDecodeError:
                processes = []

            running = [p for p in processes if p.get("Name", "").lower() not in
                       ("explorer", "svchost", "conhost", "powershell", "cmd", "python", "pythonw")]

            if running:
                out = "Juegos/programas en ejecución:\n"
                for p in running[:10]:
                    out += f"  - {p.get('MainWindowTitle', p.get('Name', '?'))}\n"
                return out.strip()
            return "No se detectaron juegos en ejecución."

        elif action == "list":
            # List common game launchers status
            launchers = {
                "Steam": os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steam.exe"),
                "Epic Games": os.path.expandvars(r"%ProgramFiles(x86)%\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe"),
                "Battle.net": os.path.expandvars(r"%ProgramFiles(x86)%\Battle.net\Battle.net.exe"),
                "Xbox": os.path.expandvars(r"%ProgramFiles%\WindowsApps\*Xbox*\xbox.exe"),
            }
            out = []
            for name, path in launchers.items():
                exists = os.path.exists(path)
                out.append(f"  {'✅' if exists else '❌'} {name}: {'instalado' if exists else 'no encontrado'}")
            return "Launchers:\n" + "\n".join(out)

        elif action == "launch":
            if not game:
                return "Indica qué juego o plataforma lanzar."
            return f"Lanzando {game}... (ejecutá la herramienta open_app para lanzarlo)"

        elif action == "update":
            # Check for updates via winget
            if not game:
                return "Indica qué juego o plataforma actualizar."
            r = subprocess.run(
                ["winget", "upgrade", game],
                capture_output=True, text=True, timeout=30
            )
            return r.stdout.strip()[:1000] or r.stderr.strip()[:1000]

        else:
            return f"Acción '{action}' no reconocida. Acciones: check, list, launch, update."

    except Exception as e:
        return f"Error en game_updater: {e}"
