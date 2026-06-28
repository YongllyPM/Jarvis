import subprocess
import os
import sys
import json
from datetime import datetime


def dev_agent(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "execute")
    command = parameters.get("command", "")
    language = parameters.get("language", "python")
    code = parameters.get("code", "")
    file_path = parameters.get("file_path", "")
    test_command = parameters.get("test_command", "")

    try:
        if action == "execute":
            if not command and not code:
                return "Necesito 'command' o 'code' para ejecutar."

            if code:
                # Execute code snippet
                return _run_code(code, language)

            # Execute shell command (scoped to safe commands)
            return _run_command(command)

        elif action == "test":
            if not test_command and not file_path:
                return "Necesito 'test_command' o 'file_path' para correr tests."

            if test_command:
                r = subprocess.run(
                    test_command, shell=True,
                    capture_output=True, text=True, timeout=60
                )
            elif file_path:
                r = subprocess.run(
                    [sys.executable, "-m", "pytest", file_path, "-v"],
                    capture_output=True, text=True, timeout=60
                )

            out = r.stdout.strip()[:1500]
            err = r.stderr.strip()[:500]
            result = ""
            if out:
                result += f"📋 {out}\n"
            if err:
                result += f"⚠️ {err}"
            return result.strip() or "Tests completados."

        elif action == "install":
            pkg = parameters.get("package", "")
            if not pkg:
                return "Necesito 'package' para instalar."
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0:
                return f"✅ {pkg} instalado correctamente."
            return f"❌ Error instalando {pkg}: {r.stderr.strip()[:500]}"

        elif action == "search":
            query = parameters.get("query", "")
            if not query:
                return "Necesito 'query' para buscar en PyPI."

            import requests
            r = requests.get(
                "https://pypi.org/simple/",
                params={"q": query}, timeout=10
            )
            return f"Buscá en https://pypi.org/search/?q={query}"

        elif action == "build":
            if not file_path:
                return "Necesito 'file_path' del script a compilar."

            # Try to compile/build
            if file_path.endswith(".py"):
                r = subprocess.run(
                    [sys.executable, "-m", "py_compile", file_path],
                    capture_output=True, text=True, timeout=30
                )
                if r.returncode == 0:
                    return f"✅ {file_path} compila sin errores."
                return f"❌ Error: {r.stderr.strip()[:500]}"

            return f"No sé cómo compilar {file_path}."

        elif action == "venv":
            venv_path = parameters.get("venv_path", ".venv")
            if not os.path.isdir(venv_path):
                return f"No se encontró el entorno virtual en {venv_path}."
            py = os.path.join(venv_path, "Scripts", "python.exe")
            if not os.path.isfile(py):
                return f"Python no encontrado en {venv_path}."
            r = subprocess.run(
                [py, "-m", "pip", "list", "--format=columns"],
                capture_output=True, text=True, timeout=30
            )
            return r.stdout.strip()[:2000] or r.stderr.strip()[:500]

        elif action == "debug":
            if not file_path:
                return "Necesito 'file_path' para debuggear."
            if not os.path.isfile(file_path):
                return f"Archivo no encontrado: {file_path}"

            try:
                with open(file_path, "r") as f:
                    content = f.read()
                compile(content, file_path, "exec")
                return f"✅ {file_path} no tiene errores de sintaxis."
            except SyntaxError as e:
                return f"❌ Error en {file_path} línea {e.lineno}: {e.msg}"

        else:
            return f"Acción '{action}' no reconocida. Acciones: execute, test, install, search, build, venv, debug."

    except subprocess.TimeoutExpired:
        return "El comando tardó demasiado y fue cancelado."
    except Exception as e:
        return f"Error en dev_agent: {e}"


def _run_code(code: str, language: str) -> str:
    if language == "python":
        try:
            r = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=15
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
            return "Timeout."
    elif language in ("powershell", "ps", "pwsh"):
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", code],
            capture_output=True, text=True, timeout=15
        )
        return (r.stdout.strip()[:1000] + "\n" + r.stderr.strip()[:500]).strip()
    else:
        r = subprocess.run(
            ["cmd", "/c", code],
            capture_output=True, text=True, timeout=15
        )
        return (r.stdout.strip()[:1000] + "\n" + r.stderr.strip()[:500]).strip()


def _run_command(command: str) -> str:
    # Whitelist allowed commands
    dangerous = ["rmdir", "del /f", "format", "diskpart", "reg delete", "shutdown"]
    cmd_lower = command.lower()
    for d in dangerous:
        if d in cmd_lower:
            return f"Comando '{command}' no permitido por seguridad."

    r = subprocess.run(
        command, shell=True,
        capture_output=True, text=True, timeout=30
    )
    out = r.stdout.strip()[:1000]
    err = r.stderr.strip()[:500]
    result = ""
    if out:
        result += out + "\n"
    if err:
        result += f"⚠️ {err}"
    return result.strip() or f"Comando ejecutado (código {r.returncode})."
