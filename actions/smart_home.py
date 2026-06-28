import json
import os
import subprocess
from pathlib import Path


def smart_home(parameters: dict, player=None) -> str:
    action = parameters.get("action", "discover")
    device = parameters.get("device", "")
    state = parameters.get("state", "")
    brightness = parameters.get("brightness")
    temperature = parameters.get("temperature")

    try:
        if action == "discover":
            # Try to find OpenRGB or similar local services
            devices = []
            # Check if OpenRGB server is running
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2)
                result = s.connect_ex(("127.0.0.1", 6742))
                s.close()
                if result == 0:
                    devices.append("OpenRGB (servidor local en puerto 6742)")
            except Exception:
                pass

            if not devices:
                return (
                    "No se detectaron dispositivos smart home. "
                    "Soportado: OpenRGB (descargalo en https://openrgb.org). "
                    "También podés controlar luces Wi-Fi con la herramienta rgb_control."
                )
            return "Dispositivos encontrados:\n" + "\n".join(f"  {d}" for d in devices)

        elif action == "control":
            if not device or not state:
                return "Necesito 'device' y 'state' (on/off)."
            # Generic response — actual control depends on specific hardware
            return (
                f"Comando enviado a '{device}' → {state}. "
                "Para control smart home real necesitás configurar "
                "un bridge (Philips Hue, Home Assistant, etc.)."
            )

        elif action == "temperature":
            if not temperature:
                return "Necesito 'temperature' en °C."
            return (
                f"Termostato ajustado a {temperature}°C. "
                "(Simulado — conectá un termostato compatible para control real.)"
            )

        elif action == "lights":
            if not device:
                device = "Luces"
            cmd = f"{state}"
            if brightness is not None:
                cmd += f" al {brightness}%"
            return (
                f"{device}: {cmd}. "
                "Para control real necesitás un hub compatible como Philips Hue."
            )

        else:
            return f"Acción '{action}' no reconocida. Acciones: discover, control, temperature, lights."

    except Exception as e:
        return f"Error en smart home: {e}"
