import subprocess
import os
import sys
import ast
import textwrap


def code_helper(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    code = parameters.get("code", "")
    file_path = parameters.get("file_path", "")
    language = parameters.get("language", "")
    query = parameters.get("query", "")

    try:
        if action == "analyze":
            if not code and not file_path:
                return "Necesito 'code' o 'file_path' para analizar."
            if file_path:
                if not os.path.isfile(file_path):
                    return f"Archivo no encontrado: {file_path}"
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()

            lines = code.split("\n")
            imports = []
            funcs = []
            classes = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    imports.append(stripped)
                if stripped.startswith("def "):
                    funcs.append(stripped)
                if stripped.startswith("class "):
                    classes.append(stripped)

            return (
                f"📊 Análisis ({len(lines)} líneas):\n"
                f"  Importaciones: {len(imports)}\n"
                f"  Funciones: {len(funcs)}\n"
                f"  Clases: {len(classes)}\n"
                + ("\n".join(f"  ℹ️ {i}" for i in imports[:5]) if imports else "")
            )

        elif action == "format":
            if not code:
                return "Necesito 'code' para formatear."

            # Try autopep8 or black
            try:
                r = subprocess.run(
                    [sys.executable, "-m", "black", "--diff", "-"],
                    input=code, capture_output=True, text=True, timeout=10
                )
                if r.returncode == 0:
                    return r.stdout[:2000] or "Código ya está formateado."
                # Fallback to autopep8
                r2 = subprocess.run(
                    [sys.executable, "-m", "autopep8", "-"],
                    input=code, capture_output=True, text=True, timeout=10
                )
                return r2.stdout[:2000] if r2.stdout.strip() else "Código OK."
            except FileNotFoundError:
                return "Instalá black o autopep8: pip install black autopep8"

        elif action == "lint":
            if not code and not file_path:
                return "Necesito 'code' o 'file_path'."
            if file_path:
                try:
                    r = subprocess.run(
                        [sys.executable, "-m", "py_compile", file_path],
                        capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0:
                        return "✅ Sin errores de sintaxis."
                    return f"❌ Error: {r.stderr.strip()[:500]}"
                except Exception:
                    pass

            try:
                ast.parse(code)
                return "✅ Sintaxis Python válida."
            except SyntaxError as e:
                return f"❌ Error de sintaxis: {e}"

        elif action == "snippet":
            if not query:
                return "¿Qué tipo de snippet necesitás? Ej: 'leer archivo CSV'"

            query_lower = query.lower()
            snippets = {
                "csv": (
                    "import csv\nwith open('archivo.csv', 'r') as f:\n"
                    "    reader = csv.DictReader(f)\n"
                    "    for row in reader:\n"
                    "        print(row['columna'])"
                ),
                "json": (
                    "import json\nwith open('archivo.json', 'r') as f:\n"
                    "    data = json.load(f)\nprint(data)"
                ),
                "http": (
                    "import requests\nr = requests.get('https://api.example.com')\n"
                    "print(r.json())"
                ),
                "thread": (
                    "import threading\ndef worker():\n    print('Hola')\n"
                    "t = threading.Thread(target=worker)\nt.start()\nt.join()"
                ),
                "regex": (
                    'import re\npatron = r"(\\w+)@(\\w+)\\.(\\w+)"\n'
                    "match = re.search(patron, 'user@example.com')\n"
                    "if match: print(match.groups())"
                ),
            }

            for key, snippet in snippets.items():
                if key in query_lower:
                    return f"```python\n{snippet}\n```"
            return (
                "Ejemplos disponibles: CSV, JSON, HTTP, thread, regex. "
                "O escribí 'snippet de [tema]' para uno específico."
            )

        elif action == "run":
            if not code:
                return "Necesito 'code' para ejecutar."
            try:
                r = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True, text=True, timeout=10
                )
                out = r.stdout.strip()[:1000]
                err = r.stderr.strip()[:500]
                result = ""
                if out:
                    result += f"Salida:\n{out}\n"
                if err:
                    result += f"Errores:\n{err}"
                return result.strip() or "(sin salida)"
            except subprocess.TimeoutExpired:
                return "Timeout: el código tardó más de 10 segundos."
            except Exception as e:
                return f"Error ejecutando: {e}"

        else:
            return f"Acción '{action}' no reconocida. Acciones: analyze, format, lint, snippet, run."

    except Exception as e:
        return f"Error en code_helper: {e}"
