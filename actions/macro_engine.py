"""macro_engine.py — Macros de clics automatizados con disparo por frase."""
import json, uuid, time, threading, re
from pathlib import Path
from difflib import SequenceMatcher

BASE_DIR = Path(__file__).resolve().parent.parent
MACROS_FILE = BASE_DIR / "config" / "macros.json"

_MACROS: list[dict] = []
_LOCK = threading.Lock()


# ── Migración ─────────────────────────────────────────────────────────────────

def _migrate(m: dict):
    """Convierte macros del formato anterior (steps) al nuevo (variations)."""
    if "steps" in m and "variations" not in m:
        m["variations"] = [{"name": "Default", "steps": m.pop("steps")}]


# ── Carga / guardado ──────────────────────────────────────────────────────────

def _load():
    global _MACROS
    try:
        if MACROS_FILE.exists():
            _MACROS = json.loads(MACROS_FILE.read_text("utf-8")).get("macros", [])
            for m in _MACROS:
                _migrate(m)
    except Exception:
        _MACROS = []


def _save():
    MACROS_FILE.parent.mkdir(parents=True, exist_ok=True)
    MACROS_FILE.write_text(
        json.dumps({"macros": _MACROS}, indent=2, ensure_ascii=False), "utf-8"
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_all() -> list[dict]:
    with _LOCK:
        return [_migrated_copy(m) for m in _MACROS]


def _migrated_copy(m: dict) -> dict:
    c = dict(m)
    _migrate(c)
    return c


def get(id_: str) -> dict | None:
    with _LOCK:
        for m in _MACROS:
            if m["id"] == id_:
                return _migrated_copy(m)
    return None


def create(name: str, trigger: str, variations: list | None = None) -> dict:
    m = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "trigger": trigger.lower(),
        "variations": variations or [{"name": "Default", "steps": []}],
    }
    with _LOCK:
        _MACROS.append(m)
        _save()
    return dict(m)


def update(id_: str, data: dict) -> dict | None:
    with _LOCK:
        for m in _MACROS:
            if m["id"] == id_:
                m.update(data)
                _migrate(m)
                _save()
                return dict(m)
    return None


def delete(id_: str):
    with _LOCK:
        _MACROS[:] = [m for m in _MACROS if m["id"] != id_]
        _save()


# ── Coincidencia ──────────────────────────────────────────────────────────────

def find_matching(text: str) -> dict | None:
    """Busca una macro cuyo trigger o nombre se parezca al texto ingresado (fuzzy)."""
    text_lower = text.lower().strip()
    best = None
    best_ratio = 0.0
    with _LOCK:
        for m in _MACROS:
            # Comparar contra trigger y nombre, quedarse con el mejor ratio
            r1 = SequenceMatcher(None, text_lower, m["trigger"]).ratio()
            r2 = SequenceMatcher(None, text_lower, m.get("name", "")).ratio()
            ratio = max(r1, r2)
            if ratio > best_ratio and ratio > 0.4:
                best_ratio = ratio
                best = m
    return _migrated_copy(best) if best else None


# ── Selección de variación ────────────────────────────────────────────────────

def _detect_current_app() -> str:
    """Intenta detectar la ventana activa para elegir variación."""
    try:
        import pygetwindow as gw
        w = gw.getActiveWindow()
        if w and w.title:
            return w.title.lower()
    except Exception:
        pass
    return ""


def _pick_variation(macro: dict, player=None) -> list[dict] | None:
    """Selecciona la variación a ejecutar según la app activa o por defecto."""
    variations = macro.get("variations", [])
    if not variations:
        return None

    if len(variations) == 1:
        return variations[0].get("steps", [])

    # Intentar detectar app y emparejar
    current = _detect_current_app()
    for v in variations:
        vname = v.get("name", "").lower()
        if vname and current and vname in current:
            if player:
                player.write_log(f"  → Variación: {v['name']}")
            return v.get("steps", [])

    # Si hay múltiples variaciones y no se pudo detectar, usar la primera
    default = variations[0]
    if player:
        player.write_log(f"  → Usando variación por defecto: {default.get('name', '')}")
    return default.get("steps", [])


# ── Ejecución ─────────────────────────────────────────────────────────────────

def _ask_gemini_for_step(step_desc: str, api_key: str, b64: str, history: list) -> dict:
    """Envía screenshot + paso a Gemini y obtiene la siguiente acción para cumplir el paso.
    Prompt diseñado para que la IA NO escriba la descripción del paso, sino que
    ANALICE la pantalla y decida qué acción ejecutar para lograr el objetivo."""
    import urllib.request

    system = (
        "Eres un asistente que ejecuta PASOS de una macro en Windows.\n\n"
        "REGLAS:\n"
        "1. El usuario te da un PASO (una descripción de lo que hay que lograr).\n"
        "2. Mirá la CAPTURA DE PANTALLA actual y decidí qué hacer.\n"
        "3. NO escribas ni tipees el texto del paso. El paso es el OBJETIVO, no texto para escribir.\n"
        "4. CONTEXTO: Los pasos se ejecutan en SECUENCIA. Si el paso anterior ya abrió el navegador, "
        "NO lo abras de nuevo. Usá la ventana existente.\n"
        "5. Si el paso YA ESTÁ CUMPLIDO en la pantalla actual (ej: el navegador ya está abierto "
        "o ya estás en Gmail), respondé {\"action\": \"done\", \"params\": {}, \"reason\": \"Ya está.\"}\n"
        "6. Para ABRIR aplicaciones: presioná Win, escribí el nombre, Enter.\n"
        "7. Para NAVEGAR: si el navegador ya está abierto, usá Ctrl+T (nueva pestaña) o Ctrl+L "
        "(barra de direcciones), escribí la URL y Enter.\n"
        "8. Para ESCRIBIR texto en un campo: usá type (SOLO si el paso requiere escribir algo).\n"
        "9. Respondé SOLO JSON sin markdown: {\"action\": \"...\", \"params\": {...}, \"reason\": \"...\"}\n"
        "10. Acciones: click, double_click, right_click, type, hotkey, press, wait, scroll, move.\n"
        "11. Las coordenadas x,y son PÍXELES exactos en la imagen que ves.\n"
        "12. Si no podés cumplir el paso, respondé {\"action\": \"failed\"}."
    )

    user_msg = f"Paso de macro a ejecutar: \"{step_desc}\"\n\n"
    if history:
        user_msg += "Acciones realizadas en este paso:\n"
        for h in history[-5:]:
            user_msg += f"  - {h['action']}: {h['result']}\n"
        user_msg += "\n"
    user_msg += "¿Cuál es la PRÓXIMA acción para cumplir este paso?\n"
    user_msg += "Si el paso ya está completo, respondé con action='done'."

    payload = {
        "model": "google/gemini-2.5-flash",
        "max_tokens": 600,
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
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(content)
    except Exception as e:
        return {"action": "failed", "params": {}, "reason": str(e)[:200]}


def _execute_step_ai(desc: str, player=None, max_actions=8) -> bool:
    """Ejecuta un paso de macro usando visión + IA.
    Toma screenshot, lo envía a Gemini con un prompt específico para macros,
    ejecuta acciones hasta que el paso se completa o falla."""
    from actions.computer_agent import (
        _get_openrouter_key, _capture_screen_base64, _execute_action
    )

    api_key = _get_openrouter_key()
    if not api_key:
        if player:
            player.write_log("     ❌ No hay API key de OpenRouter para ejecución IA.")
        return False

    history: list = []
    mode = "foreground"

    for attempt in range(max_actions):
        b64, scale_x, scale_y = _capture_screen_base64()

        decision = _ask_gemini_for_step(desc, api_key, b64, history)
        action = decision.get("action", "failed")
        params = decision.get("params", {})
        reason = decision.get("reason", "")

        if player and reason:
            short = reason[:120] + "..." if len(reason) > 120 else reason
            player.write_log(f"     🧠 {short}")

        if action == "done":
            if player:
                player.write_log(f"     ✅ Paso completado.")
            return True

        if action == "failed":
            if player:
                player.write_log(f"     ⚠️ Paso no ejecutable: {reason[:100]}")
            return False

        # Escalar coordenadas
        if "x" in params:
            params["x"] = int(round(params["x"] * scale_x))
        if "y" in params:
            params["y"] = int(round(params["y"] * scale_y))

        result = _execute_action(action, params, mode)

        if player:
            if action == "click":
                x, y = params.get("x", "?"), params.get("y", "?")
                player.write_log(f"     🖱️ Click ({x},{y}) → {result}")
            elif action == "type":
                player.write_log(f"     ⌨️ Texto → {result}")
            elif action == "hotkey":
                player.write_log(f"     🔑 {params.get('keys','')} → {result}")
            elif action == "press":
                player.write_log(f"     ⌨️ {params.get('key','')} → {result}")
            elif action == "wait":
                player.write_log(f"     ⏳ {params.get('seconds','')}s")
            else:
                player.write_log(f"     → {result}")

        history.append({"action": action, "params": params, "result": result})
        time.sleep(0.3)

    if player:
        player.write_log(f"     ⚠️ Paso agotó {max_actions} intentos sin completarse.")
    return False


def execute(macro: dict, player=None, variation_name: str | None = None) -> str:
    """Ejecuta los pasos de una macro en secuencia.
    Si un paso tiene clicks → los ejecuta directamente.
    Si no tiene clicks → usa visión IA para entender y ejecutar el paso."""
    import pyautogui

    def log(msg):
        if player:
            player.write_log(msg)

    name = macro.get("name", "Sin nombre")
    log(f"⚡ Ejecutando macro: {name}")

    if variation_name:
        steps = []
        for v in macro.get("variations", []):
            if v.get("name", "").lower() == variation_name.lower():
                steps = v.get("steps", [])
                break
    else:
        steps = _pick_variation(macro, player)

    if not steps:
        log("  ⚠️ No hay pasos definidos para esta variación.")
        return "⚠️ Sin pasos."

    for i, step in enumerate(steps, 1):
        desc = step.get("description", "").strip()
        clicks = step.get("clicks", [])

        if desc:
            log(f"  ▶  Paso {i}: {desc}")
        else:
            log(f"  ▶  Paso {i}")

        # Si hay clicks, ejecutar clicks (precisión manual)
        for j, c in enumerate(clicks, 1):
            x, y = c.get("x"), c.get("y")
            action = c.get("action", "click")
            value = c.get("value", "")
            if x is None or y is None:
                continue

            if action == "hold":
                duration = float(value) if value else 0.5
                pyautogui.moveTo(x, y, duration=0.15)
                pyautogui.mouseDown()
                time.sleep(duration)
                pyautogui.mouseUp()
                log(f"     ⏱️ Pulsación {j} en ({x},{y}) {duration}s")

            elif action == "key":
                key_name = str(value) if value else "enter"
                pyautogui.press(key_name)
                log(f"     ⌨️ Tecla {j}: {key_name}")

            else:
                pyautogui.moveTo(x, y, duration=0.15)
                time.sleep(0.08)
                pyautogui.click()
                log(f"     🖱️ Click {j} en ({x}, {y})")
            time.sleep(0.3)

        # Si NO hay clicks, usar IA con visión para ejecutar el paso
        if not clicks and desc:
            _execute_step_ai(desc, player=player)

        time.sleep(0.2)

    log(f"✅ Macro '{name}' completada.")
    return f"✅ Macro '{name}' ejecutada."


# ── Comandos de IA ──────────────────────────────────────────────────────────────

def ai_generate_steps(description: str, player=None) -> list[dict]:
    """Usa la IA (OpenRouter) para generar pasos a partir de una descripción textual.
    Devuelve una lista de dicts con 'description', sin clicks."""
    from actions.openrouter_agent import openrouter_agent

    prompt = (
        f"Generá una lista de pasos para automatizar esta tarea: \"{description}\"\n\n"
        "Reglas para cada paso:\n"
        "- Si hay que abrir una app: empezar con \"Abrir [nombre]\"\n"
        "- Si hay que ir a una URL: empezar con \"Navegar a [url]\"\n"
        "- Si hay que escribir texto: empezar con \"Escribir [texto]\"\n"
        "- Si hay que presionar tecla: empezar con \"Presionar [tecla]\"\n"
        "- Si hay que esperar: empezar con \"Esperar [segundos]\"\n"
        "- Para cerrar ventana: \"Cerrar ventana\" o \"Cerrar pestaña\"\n"
        "- Para hacer clic en un lugar específico (botón, ícono, enlace): \"Hacer clic en [elemento]\"\n\n"
        "Devuelve SOLO un array JSON, sin markdown, sin texto adicional:\n"
        '[\n'
        '  {"description": "Abrir Chrome"},\n'
        '  {"description": "Navegar a mail.google.com"},\n'
        "  ...\n"
        "]\n\n"
        "Cada paso describe UNA acción concreta y breve. Máximo 12 pasos. Respondé SOLO el JSON."
    )

    if player:
        player.write_log("🤖 Macro AI: generando pasos...")

    raw = openrouter_agent(prompt)
    if not raw:
        if player:
            player.write_log("  ❌ No se recibió respuesta de la IA.")
        return []

    try:
        steps = json.loads(raw)
        if isinstance(steps, list):
            return _normalize_ai_steps(steps)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
    if match:
        try:
            steps = json.loads(match.group())
            if isinstance(steps, list):
                return _normalize_ai_steps(steps)
        except json.JSONDecodeError:
            pass

    if player:
        player.write_log("  ⚠️ No se pudo interpretar la respuesta JSON, usando fallback.")
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    fallback = []
    for l in lines:
        l_clean = re.sub(r"^\d+[\.\)]\s*", "", l).strip('" \n')
        if l_clean and len(l_clean) > 5:
            fallback.append({"description": l_clean})
    return fallback


def _normalize_ai_steps(steps: list) -> list[dict]:
    """Normaliza la respuesta de la IA al formato interno."""
    result = []
    for s in steps:
        if isinstance(s, str):
            result.append({"description": s})
        elif isinstance(s, dict):
            desc = s.get("description", s.get("name", s.get("step", "")))
            if desc:
                result.append({"description": desc.strip()})
    return result


_load()
