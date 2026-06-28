import requests
import json
from pathlib import Path


def _get_key(name: str) -> str:
    try:
        path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg.get(name, "")
    except Exception:
        return ""


_AVIATION_KEY = None


def _get_aviation_key():
    global _AVIATION_KEY
    if _AVIATION_KEY is None:
        _AVIATION_KEY = _get_key("aviationstack_key")
    return _AVIATION_KEY


def flight_finder(parameters: dict, player=None) -> str:
    action = parameters.get("action", "search")
    origin = parameters.get("origin", "")
    destination = parameters.get("destination", "")
    date = parameters.get("date", "")
    flight_number = parameters.get("flight_number", "")
    airline = parameters.get("airline", "")

    try:
        # Try AviationStack API (free tier available)
        api_key = _get_aviation_key()

        if not api_key:
            return (
                "No hay API key de aviación configurada. "
                "Agregá 'aviationstack_key' en config/api_keys.json "
                "(registrate gratis en https://aviationstack.com)."
            )

        if action == "search":
            if not origin or not destination:
                return "Necesito 'origin' y 'destination' (códigos IATA, ej: 'EZE', 'MAD')."

            params = {
                "access_key": api_key,
                "dep_iata": origin.upper(),
                "arr_iata": destination.upper(),
            }
            if date:
                params["flight_date"] = date
            r = requests.get("https://api.aviationstack.com/v1/flights", params=params, timeout=15)
            data = r.json()
            flights = data.get("data", [])
            if not flights:
                return f"No encontré vuelos de {origin} a {destination}."
            out = []
            for f in flights[:10]:
                airline_name = f.get("airline", {}).get("name", "?")
                flight_num = f.get("flight", {}).get("iata", "?")
                dep = f.get("departure", {}).get("scheduled", "?")[:16]
                arr = f.get("arrival", {}).get("scheduled", "?")[:16]
                status = f.get("flight_status", "?")
                out.append(f"  {airline_name} {flight_num}: {dep} → {arr} [{status}]")
            return "Vuelos encontrados:\n" + "\n".join(out)

        elif action == "status":
            if not flight_number:
                return "Necesito 'flight_number' (ej: 'AA900')."

            params = {
                "access_key": api_key,
                "flight_iata": flight_number.upper(),
            }
            r = requests.get("https://api.aviationstack.com/v1/flights", params=params, timeout=15)
            data = r.json()
            flights = data.get("data", [])
            if not flights:
                return f"No encontré el vuelo {flight_number}."
            f = flights[0]
            airline_name = f.get("airline", {}).get("name", "?")
            dep = f.get("departure", {})
            arr = f.get("arrival", {})
            status = f.get("flight_status", "?")
            return (
                f"Vuelo {airline_name} {flight_number}\n"
                f"Salida: {dep.get('airport', '?')} — {dep.get('scheduled', '?')[:16]}\n"
                f"Llegada: {arr.get('airport', '?')} — {arr.get('scheduled', '?')[:16]}\n"
                f"Estado: {status}\n"
                f"Puerta: {dep.get('gate', '?')} | Terminal: {dep.get('terminal', '?')}"
            )

        elif action == "airport":
            if not origin:
                return "Necesito 'origin' (código IATA del aeropuerto)."
            params = {"access_key": api_key, "iata_code": origin.upper()}
            r = requests.get("https://api.aviationstack.com/v1/airports", params=params, timeout=15)
            data = r.json()
            airports = data.get("data", [])
            if not airports:
                return f"No encontré el aeropuerto {origin}."
            a = airports[0]
            return (
                f"{a.get('airport_name', '?')} ({origin.upper()})\n"
                f"Ciudad: {a.get('city', '?')}\n"
                f"País: {a.get('country', '?')}\n"
                f"Zona horaria: {a.get('timezone', '?')}"
            )

        else:
            return f"Acción '{action}' no reconocida. Acciones: search, status, airport."

    except ImportError:
        return "Falta requests. Ejecutá: pip install requests"
    except Exception as e:
        return f"Error en búsqueda de vuelos: {e}"
