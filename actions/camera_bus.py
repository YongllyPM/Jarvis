import cv2
import os
import tempfile
import base64
from pathlib import Path


def camera_bus(parameters: dict, player=None) -> str:
    action = parameters.get("action", "capture")
    duration = parameters.get("duration", 1)

    try:
        if action == "capture":
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "No se detectó ninguna cámara conectada."

            # Warm up
            for _ in range(10):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret:
                return "No se pudo capturar imagen de la cámara."

            tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            cv2.imwrite(tmp.name, frame)
            tmp.close()

            size_info = f"{frame.shape[1]}x{frame.shape[0]}"
            file_size = os.path.getsize(tmp.name)

            player._current_camera_image = tmp.name

            return (
                f"📸 Foto capturada ({size_info}, {file_size // 1024}KB). "
                f"Podés pedirme que analice la imagen con screen_vision."
            )

        elif action == "record":
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "No se detectó ninguna cámara."

            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            tmp = tempfile.NamedTemporaryFile(suffix=".avi", delete=False)
            out = cv2.VideoWriter(tmp.name, fourcc, 20.0, (640, 480))

            import time as _time
            start = _time.time()
            while _time.time() - start < duration:
                ret, frame = cap.read()
                if ret:
                    out.write(frame)
                else:
                    break

            cap.release()
            out.release()
            file_size = os.path.getsize(tmp.name)
            return f"🎥 Video grabado ({duration}s, {file_size // 1024}KB)."

        elif action == "list":
            import subprocess
            ps = "Get-WmiObject Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' } | Select-Object Name, Status | ConvertTo-Json"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, text=True, timeout=10
            )
            import json
            try:
                cams = json.loads(r.stdout) if r.stdout.strip() else []
                if isinstance(cams, dict):
                    cams = [cams]
                if not cams:
                    return "No se detectaron cámaras."
                return "Cámaras:\n" + "\n".join(f"  {c.get('Name', '?')}" for c in cams)
            except json.JSONDecodeError:
                return "No se pudieron enumerar las cámaras."

        elif action == "status":
            cap = cv2.VideoCapture(0)
            available = cap.isOpened()
            cap.release()
            return "✅ Cámara disponible." if available else "❌ No se detectó cámara."

        else:
            return f"Acción '{action}' no reconocida. Acciones: capture, record, list, status."

    except ImportError:
        return "OpenCV (cv2) no está instalado. Ejecutá: pip install opencv-python"
    except Exception as e:
        return f"Error en cámara: {e}"
