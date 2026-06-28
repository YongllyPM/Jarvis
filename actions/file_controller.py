import os
import shutil
import glob
import json
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _default_save_path() -> str:
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("default_save_path", "") or str(Path.home() / "Desktop")
    except Exception:
        return str(Path.home() / "Desktop")


def file_controller(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    path = parameters.get("path", "")
    dest = parameters.get("dest", "")
    content = parameters.get("content", "")
    pattern = parameters.get("pattern", "*")
    name = parameters.get("name", "")

    if not path:
        path = _default_save_path()

    try:
        if action == "list":
            items = os.listdir(path)
            files = [f for f in items if os.path.isfile(os.path.join(path, f))]
            dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
            return (
                f"📁 {len(dirs)} carpetas:\n  " + "\n  ".join(dirs[:30]) +
                f"\n\n📄 {len(files)} archivos:\n  " + "\n  ".join(files[:30])
            )

        elif action == "read":
            p = os.path.join(path, name) if name else path
            if not os.path.isfile(p):
                return f"Archivo no encontrado: {p}"
            try:
                with open(p, "r", encoding="utf-8") as f:
                    text = f.read(5000)
                return text[:2000] + ("..." if len(text) > 2000 else "")
            except UnicodeDecodeError:
                return f"Archivo binario: {os.path.getsize(p)} bytes."

        elif action == "write" or action == "create_file":
            p = os.path.join(path, name) if name else path
            os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Archivo guardado: {p} ({len(content)} caracteres)."

        elif action == "find":
            search = name or pattern or "*"
            if name and not pattern.endswith("*"):
                search = f"*{name}*" if "*" not in name else name
            p = os.path.join(path, search)
            matches = sorted(glob.glob(p, recursive=True))
            if not matches:
                return f"Sin resultados para '{search}' en {path}."
            lines = []
            for m in matches[:50]:
                if os.path.isfile(m):
                    size = os.path.getsize(m)
                    lines.append(f"📄 {m} ({_fmt_size(size)})")
                else:
                    lines.append(f"📁 {m}/")
            return "\n".join(lines[:50]) + (f"\n... y {len(matches)-50} más" if len(matches) > 50 else "")

        elif action == "copy":
            if not dest:
                return "Indica el destino con 'dest'."
            src = os.path.join(path, name) if name else path
            if os.path.isdir(src):
                shutil.copytree(src, dest, dirs_exist_ok=True)
                return f"Carpeta copiada de '{src}' a '{dest}'."
            else:
                os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
                shutil.copy2(src, dest)
                return f"Archivo copiado de '{src}' a '{dest}'."

        elif action == "move":
            if not dest:
                return "Indica el destino con 'dest'."
            src = os.path.join(path, name) if name else path
            os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
            shutil.move(src, dest)
            return f"Movido de '{src}' a '{dest}'."

        elif action == "delete":
            p = os.path.join(path, name) if name else path
            if os.path.isdir(p):
                shutil.rmtree(p)
                return f"Carpeta eliminada: {p}"
            else:
                os.remove(p)
                return f"Archivo eliminado: {p}"

        elif action == "rename":
            if not name or not dest:
                return "Indica 'name' (actual) y 'dest' (nuevo nombre)."
            src = os.path.join(path, name)
            dst = os.path.join(path, dest)
            os.rename(src, dst)
            return f"Renombrado '{name}' → '{dest}'."

        elif action == "mkdir":
            p = os.path.join(path, name) if name else path
            os.makedirs(p, exist_ok=True)
            return f"Carpeta creada: {p}"

        elif action == "info":
            p = os.path.join(path, name) if name else path
            if not os.path.exists(p):
                return f"No existe: {p}"
            stat = os.stat(p)
            info = {
                "tamaño": _fmt_size(stat.st_size),
                "creado": _fmt_time(stat.st_ctime),
                "modificado": _fmt_time(stat.st_mtime),
                "es_carpeta": os.path.isdir(p),
            }
            return json.dumps(info, ensure_ascii=False, indent=2)

        else:
            return f"Acción '{action}' no reconocida. Acciones: list, read, write, create_file, find, copy, move, delete, rename, mkdir, info."

    except Exception as e:
        return f"Error en operación de archivo: {e}"


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fmt_time(t: float) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(t).strftime("%d/%m/%Y %H:%M")
