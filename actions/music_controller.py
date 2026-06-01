"""music_controller.py — Unified facade for Spotify / YouTube Music control."""
import json
from pathlib import Path


def _get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_CONFIG_PATH = _get_base_dir() / "config" / "api_keys.json"


def _get_active_platform() -> str:
    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("music_platform", "spotify").lower().strip()
    except Exception:
        return "spotify"


def music_control(parameters: dict, player=None) -> str:
    platform = _get_active_platform()
    platform_label = "YouTube Music" if platform == "ytmusic" else "Spotify"

    if platform == "ytmusic":
        try:
            from actions.ytmusic_control import ytmusic_control
            result = ytmusic_control(parameters, player)
        except Exception as e:
            result = f"Error en {platform_label}: {e}"
    else:
        try:
            from actions.spotify_control import spotify_control
            result = spotify_control(parameters, player)
        except Exception as e:
            result = f"Error en {platform_label}: {e}"

    if player:
        player.write_log(f"🎵 [{platform_label}] {parameters.get('action', '?')}: {result}")
    return result
