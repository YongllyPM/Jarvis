import json
import requests
from pathlib import Path


def _get_key(name: str) -> str:
    try:
        path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg.get(name, "")
    except Exception:
        return ""


def social_media(parameters: dict, player=None) -> str:
    action = parameters.get("action", "post")
    platform = parameters.get("platform", "").lower()
    message = parameters.get("message", "")
    url = parameters.get("url", "")
    image_path = parameters.get("image_path", "")

    if not platform:
        return "Indicá 'platform' (twitter, telegram, discord, webhook)."
    if not message and action != "trends":
        return "Necesito un 'message' para publicar."

    try:
        if platform == "twitter":
            api_key = _get_key("twitter_bearer_token")
            if not api_key:
                return (
                    "Twitter no está configurado. Agregá 'twitter_bearer_token' "
                    "en config/api_keys.json."
                )

            if action == "post":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                data = {"text": message}
                r = requests.post(
                    "https://api.twitter.com/2/tweets",
                    headers=headers, json=data, timeout=15
                )
                if r.status_code in (200, 201):
                    return "Tweet publicado correctamente."
                return f"Error al publicar tweet: {r.status_code} {r.text[:200]}"

            elif action == "trends":
                headers = {"Authorization": f"Bearer {api_key}"}
                woeid = parameters.get("woeid", 468739)  # 468739 = Buenos Aires
                r = requests.get(
                    f"https://api.twitter.com/1.1/trends/place.json?id={woeid}",
                    headers=headers, timeout=15
                )
                if r.status_code == 200:
                    trends = r.json()[0].get("trends", [])
                    out = []
                    for t in trends[:10]:
                        out.append(f"  {t['name']} ({t.get('tweet_volume', '?')} tweets)")
                    return "Tendencias:\n" + "\n".join(out) if out else "No hay tendencias."
                return f"Error: {r.status_code}"

            else:
                return f"Acción '{action}' no soportada en Twitter."

        elif platform == "telegram":
            token = _get_key("telegram_token")
            chat_id = parameters.get("chat_id", "")
            if not token or not chat_id:
                return "Configurá 'telegram_token' y 'chat_id' en api_keys.json para Telegram."

            url_api = f"https://api.telegram.org/bot{token}/sendMessage"
            r = requests.post(url_api, json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=15)
            if r.status_code == 200:
                return "Mensaje enviado por Telegram."
            return f"Error Telegram: {r.status_code}"

        elif platform == "discord":
            webhook_url = _get_key("discord_webhook") or url
            if not webhook_url:
                return "Necesito 'url' del webhook de Discord o configurar 'discord_webhook'."

            payload = {"content": message}
            if image_path:
                try:
                    with open(image_path, "rb") as f:
                        r = requests.post(
                            webhook_url, data=payload,
                            files={"file": f}, timeout=30
                        )
                except FileNotFoundError:
                    return f"Imagen no encontrada: {image_path}"
            else:
                r = requests.post(webhook_url, json=payload, timeout=15)

            if r.status_code in (200, 204):
                return "Mensaje enviado a Discord."
            return f"Error Discord: {r.status_code}"

        elif platform == "webhook":
            webhook_url = url or _get_key("generic_webhook")
            if not webhook_url:
                return "Necesito 'url' para el webhook."
            r = requests.post(webhook_url, json={"message": message}, timeout=15)
            return f"Webhook ejecutado: {r.status_code}"

        else:
            return f"Plataforma '{platform}' no soportada. Usá: twitter, telegram, discord, webhook."

    except ImportError:
        return "Falta requests."
    except Exception as e:
        return f"Error en redes sociales: {e}"
