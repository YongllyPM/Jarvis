import subprocess
import json


def accessibility_overlay(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status")
    color = parameters.get("color", "#0000FF")
    opacity = parameters.get("opacity", 100)
    position = parameters.get("position", "")

    try:
        if action == "status":
            return (
                "🖼️ Overlay de accesibilidad\n\n"
                "Funciones disponibles:\n"
                "  color_overlay — Superposición de color (ayuda para daltonismo)\n"
                "  crosshair — Punto de mira en pantalla\n"
                "  reading_guide — Guía de lectura (línea horizontal)\n\n"
                "Nota: Los overlays requieren una ventana siempre visible "
                "o herramientas de terceros como PowerToys."
            )

        elif action == "color_overlay":
            # Apply color filter via Windows Color Filter
            if "on" in str(opacity):
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\ColorFiltering' "
                     "-Name 'Active' -Value 1 -PropertyType DWORD -Force"],
                    capture_output=True, timeout=5
                )
                return f"🎨 Filtro de color activado. Usá Win+Ctrl+C para alternar."
            else:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\ColorFiltering' "
                     "-Name 'Active' -Value 0 -PropertyType DWORD -Force"],
                    capture_output=True, timeout=5
                )
                return "🎨 Filtro de color desactivado."

        elif action == "crosshair":
            # Use PowerToys crosshair if available
            powertoys = os.path.expandvars(r"%LocalAppData%\Microsoft\PowerToys\PowerToys.exe")
            import os
            if os.path.isfile(powertoys):
                return "Activá la herramienta 'PowerToys Mouse Crosshair' en PowerToys Settings."
            return "Descargá Microsoft PowerToys desde Microsoft Store para usar crosshair."

        elif action == "reading_guide":
            # Simulate reading guide via high contrast
            try:
                import pyautogui
                # Use focus assist or magnifier docking
                pyautogui.hotkey("win", "ctrl", "q")  # Quick assist
                return "📏 Guía de lectura activada. Usá la Lupa de Windows (Win++) en modo acoplado."
            except ImportError:
                return "Usá Win++ para activar la Lupa, luego configurala en modo 'Acoplado'."

        else:
            return f"Acción '{action}' no reconocida. Acciones: status, color_overlay, crosshair, reading_guide."

    except Exception as e:
        return f"Error en overlay: {e}"
