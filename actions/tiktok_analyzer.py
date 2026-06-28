import requests
import json
import re
from pathlib import Path


def tiktok_analyzer(parameters: dict, player=None) -> str:
    action = parameters.get("action", "trending")
    username = parameters.get("username", "")
    url = parameters.get("url", "")
    hashtag = parameters.get("hashtag", "")
    count = parameters.get("count", 10)

    try:
        if action == "trending":
            # Scrape trending TikTok sounds/videos
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
            r = requests.get(
                "https://www.tiktok.com/api/recommend/item_list/",
                params={"count": min(count, 30)}, headers=headers, timeout=15
            )
            try:
                data = r.json()
            except (json.JSONDecodeError, Exception):
                data = {}

            items = data.get("itemList", [])
            if not items:
                return (
                    "TikTok no permite acceso sin autenticación. "
                    "Para usar TikTok necesitás una API key de servicios como "
                    "RapidAPI o TikTok API Business. "
                    "Agregá 'tiktok_api_key' en config/api_keys.json."
                )

            out = []
            for item in items[:count]:
                desc = item.get("desc", "(sin descripción)")[:80]
                author = item.get("author", {}).get("uniqueId", "?")
                stats = item.get("stats", {})
                likes = stats.get("digitCount", stats.get("likeCount", 0))
                out.append(f"  @{author}: {desc} — ❤️ {likes}")
            return "TikToks populares:\n" + "\n".join(out)

        elif action == "user":
            if not username:
                return "Necesito 'username'."

            api_key = _get_key("tiktok_api_key")
            if not api_key:
                return (
                    "TikTok requiere API key. Obtené una en https://rapidapi.com "
                    "y agregá 'tiktok_api_key' en config/api_keys.json."
                )

            headers = {
                "x-rapidapi-key": api_key,
                "x-rapidapi-host": "tiktok-api23.p.rapidapi.com",
            }
            r = requests.get(
                f"https://tiktok-api23.p.rapidapi.com/api/user/info",
                params={"unique_id": username}, headers=headers, timeout=15
            )
            data = r.json()
            user = data.get("data", {}).get("user", {})
            if not user:
                return f"No encontré el usuario @{username}."

            stats = user.get("stats", {})
            return (
                f"@{username}\n"
                f"  Seguidores: {stats.get('followerCount', '?')}\n"
                f"  Siguiendo: {stats.get('followingCount', '?')}\n"
                f"  Likes: {stats.get('heartCount', '?')}\n"
                f"  Videos: {stats.get('videoCount', '?')}\n"
                f"  Bio: {user.get('signature', '(sin bio)')}"
            )

        elif action == "hashtag":
            if not hashtag:
                return "Necesito 'hashtag'."

            # Search via public API
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(
                f"https://www.tiktok.com/api/challenge/detail/",
                params={"challengeName": hashtag.lstrip("#")},
                headers=headers, timeout=15
            )
            data = r.json()
            info = data.get("challengeInfo", {})
            if not info:
                return f"No encontré el hashtag #{hashtag}."

            stats = info.get("stats", {})
            return (
                f"#{hashtag}\n"
                f"  Videos: {stats.get('videoCount', '?')}\n"
                f"  Vistas: {stats.get('viewCount', '?')}"
            )

        else:
            return f"Acción '{action}' no reconocida. Acciones: trending, user, hashtag."

    except ImportError:
        return "Falta requests."
    except Exception as e:
        return f"Error en TikTok: {e}"


def _get_key(name: str) -> str:
    try:
        path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg.get(name, "")
    except Exception:
        return ""
