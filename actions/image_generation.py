"""image_generation.py — Generación de imágenes con Pollinations.ai."""
import json
import requests
import threading
from pathlib import Path
from datetime import datetime

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _get_save_dir() -> Path:
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        saved = cfg.get("default_save_path", "")
        if saved:
            p = Path(saved)
            p.mkdir(parents=True, exist_ok=True)
            return p
    except Exception:
        pass
    p = Path.home() / "Desktop"
    p.mkdir(parents=True, exist_ok=True)
    return p


_last_image_path = ""

_last_image_path = ""

def get_last_image() -> str:
    return _last_image_path

def image_generation(parameters: dict, player=None) -> str:
    prompt = parameters.get("prompt", "").strip()
    if not prompt:
        return "Se requiere un prompt para generar la imagen."

    count = int(parameters.get("count", 1))
    aspect = parameters.get("aspect_ratio", "1:1")

    def _generate():
        global _last_image_path
        try:
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in prompt)[:40]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{ts}.png"
            filepath = _get_save_dir() / filename

            width, height = _parse_aspect(aspect)

            url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
            params = {"width": width, "height": height, "nologo": "true"}

            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                filepath.write_bytes(resp.content)
                _last_image_path = str(filepath)
                if player:
                    player.write_log(f"🖼️ Imagen generada: {filepath.name}")
                    if hasattr(player, "on_image_generated"):
                        player.on_image_generated(str(filepath))
                    # Show notification
                    if hasattr(player, "_win") and hasattr(player._win, "_show_notification"):
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: player._win._show_notification(
                            f"🖼️ Imagen generada: {filepath.name}", icon="🖼️", timeout=4000, notif_type="success"
                        ))
            else:
                if player:
                    player.write_log(f"❌ Error generando imagen: HTTP {resp.status_code}")
                    if hasattr(player, "_win") and hasattr(player._win, "_show_notification"):
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, lambda: player._win._show_notification(
                            f"❌ Error generando imagen: HTTP {resp.status_code}", icon="❌", timeout=5000, notif_type="error"
                        ))
        except Exception as e:
            if player:
                player.write_log(f"❌ Error generando imagen: {e}")
                if hasattr(player, "_win") and hasattr(player._win, "_show_notification"):
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(0, lambda: player._win._show_notification(
                        f"❌ Error generando imagen: {e}", icon="❌", timeout=5000, notif_type="error"
                    ))

    def _parse_aspect(ar: str) -> tuple:
        mapping = {
            "1:1": (512, 512), "16:9": (1024, 576), "9:16": (576, 1024),
            "4:3": (768, 576), "3:2": (768, 512), "2:3": (512, 768)
        }
        return mapping.get(ar, (512, 512))

    threading.Thread(target=_generate, daemon=True).start()
    return f"🎨 Generando imagen: '{prompt}'..."
