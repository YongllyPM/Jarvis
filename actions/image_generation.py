"""image_generation.py — Generación de imágenes con Pollinations.ai."""
import json
import requests
import threading
from pathlib import Path
from datetime import datetime

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "assets" / "generated"
_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

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
            filepath = _IMAGES_DIR / filename

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
            else:
                if player:
                    player.write_log(f"❌ Error generando imagen: HTTP {resp.status_code}")
        except Exception as e:
            if player:
                player.write_log(f"❌ Error generando imagen: {e}")

    def _parse_aspect(ar: str) -> tuple:
        mapping = {
            "1:1": (512, 512), "16:9": (1024, 576), "9:16": (576, 1024),
            "4:3": (768, 576), "3:2": (768, 512), "2:3": (512, 768)
        }
        return mapping.get(ar, (512, 512))

    threading.Thread(target=_generate, daemon=True).start()
    return f"🎨 Generando imagen: '{prompt}'..."
