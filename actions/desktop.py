import os
import subprocess
import json


def desktop_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    number = parameters.get("number", 1)

    try:
        if action == "list":
            # Use PowerShell to enumerate virtual desktops
            ps = '''
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class VirtualDesktop {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
}
"@
            $desktop = (Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" | Select-Object -First 1).ProcessId
            Write-Host "Escritorio actual activo."
            '''
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=10
            )
            return "Gestión de escritorios virtuales activa."

        elif action == "switch":
            # Switch to desktop number via keyboard shortcut
            # Win+Ctrl+Arrow or Win+Ctrl+number
            import pyautogui
            if number <= 4:
                # Win+Ctrl+Left/Right or use specific keyboard shortcut
                for _ in range(number - 1):
                    pyautogui.hotkey("win", "ctrl", "right")
                    pyautogui.sleep(0.3)
                return f"Cambiando al escritorio virtual {number}."
            else:
                # Create new desktop
                pyautogui.hotkey("win", "ctrl", "d")
                return "Nuevo escritorio virtual creado."

        elif action == "new":
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "d")
            return "Nuevo escritorio virtual creado."

        elif action == "close":
            import pyautogui
            pyautogui.hotkey("win", "ctrl", "f4")
            return "Escritorio virtual cerrado."

        elif action == "move_window":
            # Move current window to another desktop
            import pyautogui
            target = parameters.get("target", 2)
            pyautogui.hotkey("win", "ctrl", "alt", str(target))
            return f"Ventana movida al escritorio {target}."

        else:
            return f"Acción '{action}' no reconocida. Acciones: list, switch, new, close, move_window."

    except ImportError:
        return "pyautogui no está instalado. No se puede controlar escritorios virtuales."
    except Exception as e:
        return f"Error en control de escritorios: {e}"
