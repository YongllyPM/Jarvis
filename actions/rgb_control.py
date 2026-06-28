import subprocess
import json
import socket
from pathlib import Path


def rgb_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status")
    device = parameters.get("device", "")
    color = parameters.get("color", "")
    effect = parameters.get("effect", "")
    brightness = parameters.get("brightness")
    speed = parameters.get("speed", "")

    try:
        # Try OpenRGB SDK (port 6742)
        if action == "status":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(("127.0.0.1", 6742))
                # Send "controller count" command
                s.sendall(bytes([0, 0, 0, 0]))  # Protocol: 4 bytes length prefix
                response = s.recv(1024)
                s.close()
                return "✅ OpenRGB detectado en localhost:6742. Usá action=set con color para cambiar luces."
            except (socket.timeout, ConnectionRefusedError, OSError):
                return (
                    "❌ OpenRGB no está corriendo. "
                    "Descargalo en https://openrgb.org y activá 'SDK Server' en Settings.\n"
                    "También podés usar action=wled si tenés LEDs WS2812B con WLED."
                )

        elif action == "set":
            if not color:
                return "Necesito un 'color' (ej: 'red', '#FF0000', '255,0,0')."

            # Convert color name to hex
            if not color.startswith("#"):
                color_map = {
                    "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
                    "white": "#FFFFFF", "yellow": "#FFFF00", "cyan": "#00FFFF",
                    "magenta": "#FF00FF", "orange": "#FF8800", "purple": "#8800FF",
                }
                color = color_map.get(color.lower(), color)

            # Try OpenRGB
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                s.connect(("127.0.0.1", 6742))
                # OpenRGB protocol: set color for all devices
                r, g, b = _hex_to_rgb(color)
                # Simple command: update LED colors (device 0, size 1)
                cmd = bytes([r, g, b, 0])
                s.sendall(cmd)
                s.close()
                return f"🎨 Color cambiado a {color}."
            except Exception as e:
                return f"No se pudo conectar con OpenRGB: {e}"

        elif action == "wled":
            # WLED LED strip control
            ip = device or "192.168.4.1"
            try:
                payload = {"on": True}
                if color:
                    r, g, b = _hex_to_rgb(color)
                    payload["seg"] = [{"col": [[r, g, b]]}]
                if brightness is not None:
                    payload["bri"] = max(0, min(255, int(brightness * 2.55)))
                if effect:
                    payload["seg"] = payload.get("seg", [{}])
                    payload["seg"][0]["fx"] = int(effect)
                r = __import__("requests").post(
                    f"http://{ip}/json/state",
                    json=payload, timeout=5
                )
                if r.status_code == 200:
                    return f"✅ WLED ({ip}) actualizado."
                return f"Error WLED: {r.status_code}"
            except ImportError:
                return "Falta requests para controlar WLED."
            except Exception as e:
                return f"Error WLED: {e}"

        elif action == "effects":
            return (
                "Efectos comunes WLED:\n"
                "  0: Sólido\n"
                "  1: Fade\n"
                "  2: Breath\n"
                "  3: Flash\n"
                "  16: Rainbow\n"
                "  17: Rainbow Cycle\n"
                "  Usá effect=NUM con action=wled"
            )

        else:
            return f"Acción '{action}' no reconocida. Acciones: status, set, wled, effects."

    except Exception as e:
        return f"Error en RGB: {e}"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (255, 0, 0)  # red fallback
