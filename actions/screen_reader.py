"""screen_reader.py — Lector de pantalla OCR en tiempo real."""
import threading
import time
import io
from pathlib import Path

_running = False
_thread = None
_last_text = ""

def _capture_screen_region():
    try:
        from mss import mss
        with mss() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            return img
    except Exception:
        return None

def _img_to_text(img) -> str:
    try:
        import pytesseract
        from PIL import Image
        if hasattr(img, "rgb"):
            pil_img = Image.frombytes("RGB", img.size, img.rgb)
        else:
            pil_img = img
        text = pytesseract.image_to_string(pil_img, lang="spa+eng")
        return text.strip()
    except Exception:
        return ""

def _ocr_loop(player=None, interval=3.0, callback=None):
    global _last_text
    while _running:
        try:
            img = _capture_screen_region()
            if img:
                text = _img_to_text(img)
                if text and text != _last_text:
                    _last_text = text
                    if callback:
                        callback(text)
                    if player:
                        player.write_log(f"👁️ OCR: {text[:100]}...")
        except Exception:
            pass
        time.sleep(interval)

def start_ocr(player=None, callback=None, interval=3.0):
    global _running, _thread
    if _running:
        return "El OCR ya está en ejecución."
    _running = True
    _thread = threading.Thread(target=_ocr_loop, args=(player, interval, callback), daemon=True)
    _thread.start()
    return "✅ Lector de pantalla OCR iniciado."

def stop_ocr():
    global _running
    _running = False
    return "⏹️ Lector de pantalla detenido."

def screen_reader(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()

    if action == "start" or action == "on":
        return start_ocr(player)
    elif action == "stop" or action == "off":
        return stop_ocr()
    elif action == "capture":
        img = _capture_screen_region()
        if img:
            text = _img_to_text(img)
            if text:
                if player:
                    player.write_log(f"📄 Texto capturado: {text[:200]}")
                return f"Texto en pantalla: {text[:500]}"
            return "No se detectó texto en la pantalla."
        return "Error al capturar pantalla."
    else:
        return "Acciones: start, stop, capture."
