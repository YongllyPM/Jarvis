"""weather_report.py — Clean weather forecasting action."""
import urllib.request
import urllib.parse
import json
from pathlib import Path

def weather_action(parameters: dict, player=None) -> str:
    """Fetch current weather report from wttr.in in clean text format."""
    city = parameters.get("city", "").strip()
    if not city:
        # Fall back to auto-detected city from config
        try:
            cfg_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                city = cfg.get("ubicacion", "")
        except Exception:
            city = ""

    try:
        encoded_city = urllib.parse.quote(city)
        url = f"https://wttr.in/{encoded_city}?format=%C+%t+%h+%w"

        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = response.read().decode("utf-8").strip()

        report = f"Current weather in {city}: {data}"
        if player:
            player.write_log(f"🌤️ {report}")
        return report
    except Exception as e:
        msg = f"Unable to fetch real-time weather details for {city}: {e}"
        if player:
            player.write_log(f"⚠️ {msg}")
        return f"Sir, I'm having trouble connecting to the weather service right now. However, I can search online if you wish."
