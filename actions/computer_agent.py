"""computer_agent.py — Agente autónomo multi-paso para control total de la PC.

Usa un bucle visión → razonamiento → acción para completar tareas complejas
como descargar e instalar programas, crear documentos, etc.
"""

import json
import base64
import time
import urllib.request
import urllib.error
import logging
import io
import threading
from pathlib import Path

from mss import mss
from PIL import Image

logger = logging.getLogger("computer_agent")

BASE_DIR = Path(__file__).resolve().parent.parent
API_FILE = BASE_DIR / "config" / "api_keys.json"

_MAX_STEPS = 30
_MAX_SCREENSHOTS = 6  # solo enviar las últimas 6 capturas

# ── Mecanismo de detención ────────────────────────────────────────────────────
_AGENT_STOP = threading.Event()

def stop_agent():
    """Señal para detener el agente en el siguiente ciclo."""
    _AGENT_STOP.set()

def _agent_should_stop() -> bool:
    return _AGENT_STOP.is_set()

def _reset_stop():
    _AGENT_STOP.clear()


def _get_openrouter_key() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_api_key", "")
    except Exception:
        return ""


def _capture_screen_base64(max_size: tuple | None = None, quality: int = 85):
    """Captura la pantalla y devuelve (b64_string, scale_x, scale_y).
    
    Si no se especifica max_size, usa la resolución nativa del monitor.
    """
    with mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGBA", screenshot.size, screenshot.bgra)
        r, g, b, a = img.split()
        img = Image.merge("RGB", (b, g, r))
        orig_w, orig_h = img.size

        if max_size is not None:
            img.thumbnail(max_size, Image.Resampling.BILINEAR)
            new_w, new_h = img.size
            scale_x = orig_w / new_w
            scale_y = orig_h / new_h
        else:
            scale_x = 1.0
            scale_y = 1.0

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode("utf-8"), scale_x, scale_y


def _screen_fingerprint() -> str:
    """Hash perceptual rápido (16x16) para detectar cambios en pantalla."""
    with mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGBA", screenshot.size, screenshot.bgra)
        img = img.resize((16, 16), Image.Resampling.BILINEAR)
        gray = img.convert("L")
        pixels = list(gray.getdata())
        avg = sum(pixels) / len(pixels)
        return "".join("1" if p > avg else "0" for p in pixels)


def _execute_action(action: str, params: dict, mode: str) -> str:
    """Ejecuta una acción atómica vía pyautogui. Devuelve resultado."""
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    try:
        if action == "click":
            x, y = params.get("x"), params.get("y")
            if x is None or y is None:
                return "Error: faltan coordenadas x/y"
            ok, msg = _click_with_retry(x, y, params.get("retries", 3))
            return msg

        elif action == "double_click":
            x, y = params.get("x"), params.get("y")
            if x is None or y is None:
                return "Error: faltan coordenadas x/y"
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.doubleClick()
            return f"Doble click en ({x}, {y})"

        elif action == "right_click":
            x, y = params.get("x"), params.get("y")
            if x is None or y is None:
                return "Error: faltan coordenadas x/y"
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.rightClick()
            return f"Click derecho en ({x}, {y})"

        elif action == "type":
            text = params.get("text", "")
            interval = 0.01 if mode == "background" else 0.05
            pyautogui.typewrite(text, interval=interval)
            return f"Texto escrito ({len(text)} chars)"

        elif action == "hotkey":
            keys = params.get("keys", "")
            if isinstance(keys, str):
                keys = keys.split("+")
            pyautogui.hotkey(*keys)
            return f"Hotkey: {'+'.join(keys)}"

        elif action == "scroll":
            direction = params.get("direction", "down")
            amount = params.get("amount", 3)
            clicks = amount if direction in ("down", "right") else -amount
            pyautogui.scroll(clicks)
            return f"Scroll {direction} x{amount}"

        elif action == "wait":
            seconds = params.get("seconds", 1)
            time.sleep(seconds)
            return f"Espera {seconds}s"

        elif action == "move":
            x, y = params.get("x", 0), params.get("y", 0)
            pyautogui.moveTo(x, y, duration=0.2)
            return f"Mouse movido a ({x}, {y})"

        elif action == "screenshot":
            path = params.get("path")
            if not path:
                path = str(BASE_DIR / "assets" / "agent_screenshot.png")
            pyautogui.screenshot(path)
            return f"Captura guardada"

        elif action == "press":
            key = params.get("key", "enter")
            pyautogui.press(key)
            return f"Tecla: {key}"

        else:
            return f"Acción desconocida: {action}"

    except Exception as e:
        return f"Error ejecutando '{action}': {e}"


def _click_with_retry(cx: int, cy: int, max_retries: int = 3) -> tuple:
    """
    Intenta hacer click en (cx, cy). Si la pantalla no cambia,
    prueba en un patrón espiral hacia afuera (radio 3, 5, 8 px).
    """
    import pyautogui
    steps = []
    # Espiral: centro + 4 direcciones cardinales a distancias crecientes
    spiral = [(0, 0), (5, 0), (-5, 0), (0, 5), (0, -5),
              (8, 4), (-8, 4), (8, -4), (-8, -4),
              (5, 8), (-5, 8), (5, -8), (-5, -8)]
    for dx, dy in spiral[:max_retries + 1]:
        x, y = cx + dx, cy + dy
        before = _screen_fingerprint()
        pyautogui.moveTo(x, y, duration=0.08)
        pyautogui.click()
        time.sleep(0.15)
        after = _screen_fingerprint()
        steps.append(f"({x},{y})")
        if before != after:
            return True, f"Click en ({x},{y}) (intento {len(steps)})"
    return False, f"Click falló tras {len(steps)} intentos: {', '.join(steps)} ⚠️ No se detectó cambio en pantalla."


_ACTIONS_THAT_CHANGE_SCREEN = {"click", "double_click", "right_click", "type", "hotkey", "press", "scroll"}


def _ask_gemini(task: str, mode: str, history: list, api_key: str, b64: str) -> dict:
    """Envía la pantalla actual + historial a Gemini y obtiene la siguiente acción."""

    system = (
        "Eres un agente autónomo de PC con capacidad de razonamiento visual. "
        "Tu tarea es completar el objetivo del usuario "
        "usando acciones atómicas sobre la computadora.\n\n"
        "REGLAS:\n"
        "1. RAZONAMIENTO: Antes de decidir, pensá paso a paso. En el campo 'reason' explicá "
        "qué ves en la captura y por qué elegís esa acción.\n"
        "2. Respondé SOLO con JSON sin markdown:\n"
        "   {\"action\": \"...\", \"params\": {...}, \"reason\": \"...\"}\n"
        "3. Acciones disponibles: click, double_click, right_click, type, hotkey, scroll, wait, move, press\n"
        "4. Para click: x, y son coordenadas de PIXEL exactas en la imagen que ves.\n"
        "5. Para type: text es el texto a escribir.\n"
        "6. Para hotkey: keys puede ser lista o string separado por +, ej: [\"ctrl\", \"c\"] o \"ctrl+c\".\n"
        "7. Para wait: seconds es tiempo en segundos (máx 5).\n"
        "8. Para scroll: direction=\"up\"|\"down\", amount=clicks.\n"
        "9. Para press: key es el nombre de la tecla (enter, tab, esc, etc.)\n"
        "10. Preferí hotkeys antes que type cuando sea posible (Ctrl+A, Ctrl+C, Ctrl+V, Win+D, etc.)\n"
        "11. Si la tarea está COMPLETA, respondé: {\"action\": \"done\", \"params\": {\"summary\": \"...\"}, \"reason\": \"...\"}\n"
        "12. Si la tarea es IMPOSIBLE de completar, respondé: {\"action\": \"failed\", \"params\": {\"error\": \"...\"}, \"reason\": \"...\"}\n"
        "13. PRECISIÓN: Apuntá al CENTRO de los botones/elementos, no a los bordes. "
        "Si ves un botón con texto \"Empezar\", identificá sus bordes visuales y calculá el centro exacto.\n"
        "14. Si un click no funcionó (no cambió la pantalla), el sistema reintenta automáticamente en posiciones cercanas.\n"
        "15. Después de escribir texto en un campo de búsqueda, presioná Enter.\n"
        "16. PARA TAREAS QUE REQUIERAN INVESTIGACIÓN: abrí primero un navegador, buscá en Google, "
        "leé los resultados de la búsqueda, y recién después actuá.\n"
        "17. Para abrir la Microsoft Store: presioná la tecla Windows, escribí 'Store', y presioná Enter.\n"
        "18. Navegación web: identificá claramente la barra de direcciones, campos de búsqueda, botones y enlaces. "
        "Usá coordenadas precisas para cada elemento.\n"
        "19. Para Khan Academy, Duolingo, etc.: buscá visualmente el texto de los botones "
        "(\"Empezar\", \"Siguiente\", \"Continuar\", \"Probar\", \"Comprobar\", \"Enviar\") "
        "y hacé click exactamente en el centro de ese texto.\n"
        "20. Para ejercicios interactivos: leé la pregunta, identificá los campos de respuesta, "
        "escribí la respuesta correcta y hacé click en \"Comprobar\" o \"Enviar\".\n"
    )

    user_msg = f"Objetivo: {task}\nModo: {mode}\n\n"

    if history:
        recent = history[-8:]
        user_msg += "Historial de acciones recientes:\n"
        for h in recent:
            user_msg += f"  - {h['action']}: {h['result']}\n"

    user_msg += "\n¿Cuál es la PRÓXIMA acción basada en la captura de pantalla actual?"

    payload = {
        "model": "google/gemini-2.5-flash",
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            },
        ],
    }

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/jarvis-beta",
        "X-Title": "JARVIS AI Assistant",
        "Content-Type": "application/json",
    }

    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0].strip()
            return json.loads(content)
    except json.JSONDecodeError as e:
        return {"action": "failed", "params": {"error": f"Respuesta inválida: {content[:200]}"}, "reason": str(e)}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {"action": "failed", "params": {"error": f"HTTP {e.code}: {err_body[:200]}"}, "reason": str(e)}
    except Exception as e:
        return {"action": "failed", "params": {"error": str(e)[:200]}, "reason": str(e)}


def computer_agent(parameters: dict, player=None, speak=None) -> str:
    """Agente autónomo: recibe una tarea y la ejecuta paso a paso."""
    _reset_stop()

    api_key = _get_openrouter_key()
    if not api_key:
        return "❌ No hay clave de OpenRouter en config/api_keys.json."

    task = parameters.get("task", "").strip()
    mode = parameters.get("mode", "foreground").strip().lower()
    if mode not in ("foreground", "background"):
        mode = "foreground"

    if not task:
        return "❌ No se proporcionó ninguna tarea."

    if player:
        player.write_log(f"🤖 Agent iniciando: {task[:80]}")
    if speak:
        speak(f"Voy a {task[:150].lower()}")

    history: list[dict] = []
    step = 0
    MAX_STEPS = parameters.get("max_steps", _MAX_STEPS)
    consecutive_failures = 0

    while step < MAX_STEPS:
        if _agent_should_stop():
            if player:
                player.write_log("⛏️ Agente detenido por el usuario.")
            if speak:
                speak("Agente detenido.")
            return "⛏️ Agente detenido."

        step += 1

        if player:
            player.write_log(f"🔍 Paso {step}: analizando pantalla...")

        b64, scale_x, scale_y = _capture_screen_base64()

        decision = _ask_gemini(task, mode, history, api_key, b64)
        action = decision.get("action", "failed")
        params = decision.get("params", {})
        reason = decision.get("reason", "")

        if player and reason:
            player.write_log(f"🧠 {reason}")
        if speak and reason:
            speak(reason[:200])

        logger.info(f"Step {step}: {action} — {reason}")

        if action == "done":
            summary = params.get("summary", "Tarea completada.")
            if speak:
                speak(summary)
            if player:
                player.write_log(f"✅ Agent: {summary}")
            return f"✅ {summary}"

        if action == "failed":
            error = params.get("error", "Error desconocido.")
            if player:
                player.write_log(f"❌ Agent falló: {error}")
            if speak:
                speak(f"Lo siento, fallé: {error[:150]}")
            return f"❌ {error}"

        # Escalar coordenadas de la imagen redimensionada a la pantalla real
        if "x" in params:
            params["x"] = int(round(params["x"] * scale_x))
        if "y" in params:
            params["y"] = int(round(params["y"] * scale_y))

        fingerprint_before = _screen_fingerprint() if action in _ACTIONS_THAT_CHANGE_SCREEN else None

        result = _execute_action(action, params, mode)

        if player:
            if action == "click":
                x, y = params.get("x", "?"), params.get("y", "?")
                player.write_log(f"🖱️ Click en ({x}, {y}) → {result}")
            elif action == "type":
                player.write_log(f"⌨️ Escribiendo texto... → {result}")
            elif action == "hotkey":
                player.write_log(f"🔑 Atajo: {params.get('keys','')} → {result}")
            elif action == "scroll":
                player.write_log(f"📜 Scroll {params.get('direction','')} → {result}")
            elif action == "wait":
                player.write_log(f"⏳ Esperando {params.get('seconds','')}s...")
            else:
                player.write_log(f"  → {action}: {result}")

        if speak and action in ("click", "type", "hotkey", "scroll", "wait"):
            if action == "click":
                speak(f"Haciendo clic...")
            elif action == "type":
                text = params.get("text", "")[:60]
                speak(f"Escribiendo: {text}" if text else "Escribiendo texto...")
            elif action == "hotkey":
                speak(f"Presionando {params.get('keys', '')}")
            elif action == "scroll":
                speak(f"Desplazando hacia {params.get('direction', 'abajo')}")
            elif action == "wait":
                speak(f"Esperando {params.get('seconds', 'unos')} segundos")

        if fingerprint_before is not None and action != "click":
            time.sleep(0.25)
            fingerprint_after = _screen_fingerprint()
            if fingerprint_before == fingerprint_after:
                consecutive_failures += 1
                result += " ⚠️ La pantalla NO cambió después de esta acción."
            else:
                consecutive_failures = 0

        history.append({"action": action, "params": params, "result": result})

        if consecutive_failures >= 3:
            msg = "El agente falló 3 veces seguidas porque los clicks no impactaban en la pantalla. Intentá de nuevo con instrucciones más claras."
            if speak:
                speak("Fallé demasiadas veces seguidas. Necesito instrucciones más claras.")
            return f"❌ {msg}"

        time.sleep(0.3)

    msg = "⏱️ Agente alcanzó el límite de pasos sin completar la tarea."
    if speak:
        speak("No terminé a tiempo. Necesito más pasos o instrucciones más específicas.")
    return msg
