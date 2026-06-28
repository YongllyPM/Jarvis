import subprocess
import os


def accessibility(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status")
    feature = parameters.get("feature", "")
    state = parameters.get("state", "")

    try:
        if action == "status":
            return (
                "🔧 Herramientas de accesibilidad:\n"
                "  action details — info sobre una herramienta\n"
                "  screen_magnifier — Lupa de Windows\n"
                "  narrator — Narrador de Windows\n"
                "  high_contrast — Alto contraste\n"
                "  osd_keyboard — Teclado en pantalla\n"
                "  dictation — Dictado por voz (Win+H)"
            )

        elif action == "details":
            if not feature:
                return "Indicá 'feature' para ver detalles."
            features = {
                "magnifier": (
                    "Lupa de Windows: Win++ y Win+- para zoom. "
                    "Win+Esc para salir."
                ),
                "narrator": (
                    "Narrador: lee la pantalla en voz alta. "
                    "Win+Ctrl+Enter para activar/desactivar."
                ),
                "high_contrast": (
                    "Alto contraste: Alt+Shift+PrtScn. "
                    "Mejora la visibilidad del texto."
                ),
                "osd_keyboard": (
                    "Teclado en pantalla: Win+Ctrl+O. "
                    "Útil si tenés problemas con el teclado físico."
                ),
                "dictation": (
                    "Dictado por voz: Win+H para activar. "
                    "Hablar y escribe automáticamente."
                ),
            }
            feature_lower = feature.lower()
            for key, desc in features.items():
                if key in feature_lower or feature_lower in key:
                    return f"📖 {key}: {desc}"
            return f"No encontré información sobre '{feature}'."

        elif action in ("magnifier", "lupa"):
            if state in ("on", "true", "1", "si"):
                # Simulate Win++ to open magnifier
                try:
                    import pyautogui
                    pyautogui.hotkey("win", "=")
                    return "🔍 Lupa activada (Win++)."
                except ImportError:
                    return "Usá Win++ para abrir la Lupa."
            else:
                try:
                    import pyautogui
                    pyautogui.hotkey("win", "esc")
                    return "🔍 Lupa desactivada."
                except ImportError:
                    return "Usá Win+Esc para cerrar la Lupa."

        elif action in ("narrator", "narrador"):
            try:
                import pyautogui
                if state in ("on", "true", "1", "si"):
                    pyautogui.hotkey("win", "ctrl", "enter")
                    return "🔊 Narrador activado (Win+Ctrl+Enter)."
                else:
                    subprocess.run(
                        ["powershell", "-NoProfile", "-Command",
                         "Stop-Process -Name Narrator -Force -ErrorAction SilentlyContinue"],
                        capture_output=True, timeout=5
                    )
                    return "🔊 Narrador desactivado."
            except ImportError:
                return "Usá Win+Ctrl+Enter para activar/desactivar el Narrador."

        elif action in ("osd_keyboard", "teclado"):
            try:
                import pyautogui
                pyautogui.hotkey("win", "ctrl", "o")
                return "⌨️ Teclado en pantalla activado."
            except ImportError:
                return "Usá Win+Ctrl+O para abrir el teclado en pantalla."

        elif action == "voice_access":
            try:
                import pyautogui
                pyautogui.hotkey("win", "ctrl", "s")
                return "🎤 Acceso por voz activado."
            except ImportError:
                return "Usá Win+Ctrl+S para activar Acceso por voz."

        elif action in ("dictation", "dictado"):
            try:
                import pyautogui
                pyautogui.hotkey("win", "h")
                return "🎤 Dictado por voz activado (Win+H)."
            except ImportError:
                return "Usá Win+H para activar el dictado."

        elif action == "reduce_animations":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "New-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Accessibility' "
                 "-Name 'ReducedAnimation' -Value 1 -PropertyType DWORD -Force"],
                capture_output=True, timeout=5
            )
            return "Animaciones reducidas configuradas."

        else:
            return f"Acción '{action}' no reconocida. Usá action=status para ver opciones."

    except Exception as e:
        return f"Error en accesibilidad: {e}"


def eye_tracking(parameters: dict, player=None) -> str:
    return "Eye tracking requiere hardware compatible (Tobii, EyeTech). No detectado."


def micro_movement(parameters: dict, player=None) -> str:
    return "Micro-movement no disponible sin cámara especializada."


def task_simplify(parameters: dict, player=None) -> str:
    action = parameters.get("action", "options")
    if action == "options":
        return (
            "Simplificación de tareas:\n"
            "  Focus Assist: Win+Alt+K (No molestar)\n"
            "  Modo oscuro: activalo en Configuración → Personalización\n"
            "  Texto más grande: Configuración → Accesibilidad → Tamaño de texto"
        )
    return "Usá las opciones de Windows para simplificar la interfaz."


def routine_gamify(parameters: dict, player=None) -> str:
    action = parameters.get("action", "info")
    if action == "info":
        return (
            "Gamificación de rutinas: creá metas con la herramienta 'goals'.\n"
            "Podés:\n"
            "  - goals action=add goal='tarea' → agregar tarea\n"
            "  - goals action=list → ver progreso\n"
            "  - goals action=complete goal_id=X → marcar completada"
        )
    return "Usá la herramienta 'goals' para gamificar tus rutinas."
