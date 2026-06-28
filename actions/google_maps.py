import requests
import json
import urllib.parse


def google_maps(parameters: dict, player=None) -> str:
    action = parameters.get("action", "search")
    query = parameters.get("query", "")
    origin = parameters.get("origin", "")
    destination = parameters.get("destination", "")
    lat = parameters.get("lat")
    lon = parameters.get("lon")
    place_id = parameters.get("place_id", "")

    # Try OpenStreetMap Nominatim (free, no key) as primary
    # Fallback to Google Maps API if configured
    api_key = _get_maps_key()

    try:
        if action == "search":
            if not query:
                return "Indicá 'query' para buscar."

            if api_key:
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                r = requests.get(url, params={"query": query, "key": api_key}, timeout=10)
                data = r.json()
                results = data.get("results", [])
                if not results:
                    return f"No encontré '{query}'."
                out = []
                for p in results[:5]:
                    addr = p.get("formatted_address", "")
                    rating = p.get("rating", "?")
                    out.append(f"  {p['name']} ({rating}★) — {addr}")
                return "Lugares:\n" + "\n".join(out)
            else:
                # OSM fallback
                url = "https://nominatim.openstreetmap.org/search"
                headers = {"User-Agent": "JARVIS-AI/1.0"}
                r = requests.get(
                    url, params={"q": query, "format": "json", "limit": 5, "addressdetails": 1},
                    headers=headers, timeout=10
                )
                results = r.json()
                if not results:
                    return f"No encontré '{query}'."
                out = []
                for p in results:
                    addr = p.get("display_name", "")[:60]
                    out.append(f"  {p.get('name', addr)} — {addr}")
                return "Lugares:\n" + "\n".join(out)

        elif action == "directions":
            if not origin or not destination:
                return "Necesito 'origin' y 'destination'."

            if api_key:
                url = "https://maps.googleapis.com/maps/api/directions/json"
                r = requests.get(url, params={
                    "origin": origin, "destination": destination, "key": api_key,
                    "language": "es"
                }, timeout=10)
                data = r.json()
                routes = data.get("routes", [])
                if not routes:
                    return f"No encontré ruta de '{origin}' a '{destination}'."
                leg = routes[0]["legs"][0]
                dist = leg.get("distance", {}).get("text", "?")
                duration = leg.get("duration", {}).get("text", "?")
                steps = []
                for s in leg.get("steps", [])[:5]:
                    html = s.get("html_instructions", "")
                    import re
                    text = re.sub(r"<[^>]+>", "", html)
                    steps.append(f"  → {text}")
                return (
                    f"De {origin} a {destination}\n"
                    f"Distancia: {dist} | Duración: {duration}\n"
                    + "\n".join(steps)
                )
            else:
                # OSRM fallback for directions
                url = "https://router.project-osrm.org/route/v1/driving/{},{};{},{}"
                # Geocode first
                geo_src = _geocode_osm(origin)
                geo_dst = _geocode_osm(destination)
                if not geo_src or not geo_dst:
                    return "No pude geocodificar origen o destino."
                route_url = url.format(geo_src[1], geo_src[0], geo_dst[1], geo_dst[0])
                r = requests.get(route_url, params={"overview": "false", "steps": "true"}, timeout=10)
                data = r.json()
                routes = data.get("routes", [])
                if not routes:
                    return "No encontré ruta."
                leg = routes[0]["legs"][0]
                dist = f"{leg['distance'] / 1000:.1f} km"
                duration = f"{leg['duration'] / 60:.0f} min"
                return f"De {origin} a {destination} — {dist}, {duration}."

        elif action == "geocode":
            location = query or f"{lat},{lon}" if lat and lon else ""
            if not location:
                return "Indicá 'query' o 'lat'+'lon'."

            if api_key:
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                r = requests.get(url, params={"address": location, "key": api_key}, timeout=10)
                data = r.json()
                results = data.get("results", [])
                if not results:
                    return f"No encontré '{location}'."
                p = results[0]
                return f"{p['formatted_address']} (lat:{p['geometry']['location']['lat']}, lng:{p['geometry']['location']['lng']})"
            else:
                result = _geocode_osm(location)
                if result:
                    return f"{result[2]} (lat:{result[0]}, lon:{result[1]})"
                return f"No encontré '{location}'."

        else:
            return f"Acción '{action}' no reconocida. Acciones: search, directions, geocode."

    except ImportError:
        return "Falta requests. Ejecutá: pip install requests"
    except Exception as e:
        return f"Error en Maps: {e}"


def _get_maps_key() -> str:
    try:
        path = __import__("pathlib").Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg.get("google_maps_key", "")
    except Exception:
        return ""


def _geocode_osm(query: str) -> tuple | None:
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "JARVIS-AI/1.0"}
    r = requests.get(url, params={"q": query, "format": "json", "limit": 1}, headers=headers, timeout=10)
    results = r.json()
    if results:
        p = results[0]
        return (p["lat"], p["lon"], p.get("display_name", ""))
    return None
