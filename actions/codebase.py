import os
import json
import subprocess
from pathlib import Path


def codebase(parameters: dict, player=None) -> str:
    path = parameters.get("path", "")
    action = parameters.get("action", "overview")
    file_path = parameters.get("file_path", "")

    if not path:
        path = os.getcwd()
    if not os.path.isdir(path):
        return f"La ruta '{path}' no existe o no es una carpeta."

    try:
        if action == "overview":
            return _overview(path)
        elif action == "structure":
            depth = parameters.get("depth", 3)
            return _structure(path, depth)
        elif action == "dependencies":
            return _dependencies(path)
        elif action == "find":
            query = parameters.get("query", "")
            if not query:
                return "Indica 'query' para buscar."
            return _find_in_files(path, query)
        elif action == "stats":
            return _stats(path)
        elif action == "functions":
            p = os.path.join(path, file_path) if file_path else path
            return _list_functions(p)
        else:
            return f"Acción '{action}' no reconocida. Acciones: overview, structure, dependencies, find, stats, functions."
    except Exception as e:
        return f"Error analizando código: {e}"


def _overview(path: str) -> str:
    lines = []
    total_files = 0
    total_dirs = 0
    by_ext: dict[str, int] = {}
    for root, dirs, files in os.walk(path):
        if ".git" in root or "__pycache__" in root or ".venv" in root:
            continue
        total_dirs += 1
        for f in files:
            total_files += 1
            ext = Path(f).suffix.lower() or "(sin ext)"
            by_ext[ext] = by_ext.get(ext, 0) + 1

    lines.append(f"📁 {total_dirs} directorios, 📄 {total_files} archivos")
    lines.append("")
    if by_ext:
        top = sorted(by_ext.items(), key=lambda x: -x[1])[:10]
        lines.append("Extensiones:")
        for ext, count in top:
            lines.append(f"  {ext}: {count}")
    return "\n".join(lines)


def _structure(path: str, max_depth: int = 3) -> str:
    lines = []
    base_depth = path.rstrip(os.sep).count(os.sep)

    for root, dirs, files in os.walk(path):
        if ".git" in root or "__pycache__" in root or ".venv" in root:
            dirs.clear()
            continue
        depth = root.count(os.sep) - base_depth
        if depth > max_depth:
            dirs.clear()
            continue
        indent = "  " * depth
        lines.append(f"{indent}📁 {os.path.basename(root) or root}")
        for f in sorted(files):
            lines.append(f"{indent}  📄 {f}")

    return "\n".join(lines)


def _dependencies(path: str) -> str:
    req = os.path.join(path, "requirements.txt")
    if os.path.isfile(req):
        with open(req) as f:
            return f"requirements.txt:\n{f.read().strip()[:2000]}"

    pkg = os.path.join(path, "package.json")
    if os.path.isfile(pkg):
        with open(pkg) as f:
            data = json.load(f)
        deps = data.get("dependencies", {})
        if not deps:
            return "Sin dependencias en package.json."
        return "package.json:\n" + "\n".join(f"  {k}: {v}" for k, v in deps.items())

    cargo = os.path.join(path, "Cargo.toml")
    if os.path.isfile(cargo):
        with open(cargo) as f:
            return f"Cargo.toml:\n{f.read().strip()[:2000]}"

    return "No se encontró archivo de dependencias (requirements.txt, package.json, Cargo.toml)."


def _find_in_files(path: str, query: str) -> str:
    try:
        r = subprocess.run(
            ["rg", "-l", "-i", query, path],
            capture_output=True, text=True, timeout=30
        )
        if r.stdout:
            files = r.stdout.strip().split("\n")
            return "Archivos con coincidencias:\n  " + "\n  ".join(files[:20])
        else:
            return f"Sin coincidencias para '{query}'."
    except FileNotFoundError:
        # Fallback a grep de Python
        matches = []
        for root, dirs, files in os.walk(path):
            if ".git" in root or "__pycache__" in root or ".venv" in root:
                continue
            for f in files:
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            if query.lower() in line.lower():
                                matches.append(fp)
                                break
                except Exception:
                    pass
                if len(matches) >= 20:
                    break
            if len(matches) >= 20:
                break
        if matches:
            return "Archivos con coincidencias:\n  " + "\n  ".join(matches)
        return f"Sin coincidencias para '{query}'."


def _stats(path: str) -> str:
    total_lines = 0
    total_files = 0
    by_lang: dict[str, int] = {}

    for root, dirs, files in os.walk(path):
        if ".git" in root or "__pycache__" in root or ".venv" in root:
            continue
        for f in files:
            fp = os.path.join(root, f)
            try:
                with open(fp, "rb") as fh:
                    lines = sum(1 for _ in fh)
                total_lines += lines
                total_files += 1
                ext = Path(f).suffix.lower() or "(sin ext)"
                by_lang[ext] = by_lang.get(ext, 0) + lines
            except Exception:
                pass

    out = [f"📊 {total_files} archivos, {total_lines} líneas"]
    if by_lang:
        top = sorted(by_lang.items(), key=lambda x: -x[1])[:10]
        out.append("")
        out.append("Por extensión:")
        for ext, lines in top:
            out.append(f"  {ext}: {lines} líneas")
    return "\n".join(out)


def _list_functions(path: str) -> str:
    if os.path.isfile(path):
        paths = [path]
    else:
        paths = []
        for root, dirs, files in os.walk(path):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if f.endswith(".py"):
                    paths.append(os.path.join(root, f))

    import re
    out = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
            funcs = re.findall(r"^(?:async\s+)?def\s+(\w+)\s*\(", content, re.MULTILINE)
            classes = re.findall(r"^class\s+(\w+)", content, re.MULTILINE)
            rel = os.path.relpath(p, os.path.commonpath([p, os.getcwd()]))
            parts = []
            if classes:
                parts.append(f"clases: {', '.join(classes)}")
            if funcs:
                parts.append(f"funciones: {', '.join(funcs)}")
            if parts:
                out.append(f"{rel}: {' | '.join(parts)}")
        except Exception:
            pass

    return "\n".join(out[:30]) if out else "No se encontraron funciones Python."
