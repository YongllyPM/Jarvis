from ._google_auth import _get_service, _check_creds
import base64
from email.message import EmailMessage


def gmail_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    query = parameters.get("query", "")
    max_results = parameters.get("max_results", 10)
    to = parameters.get("to", "")
    subject = parameters.get("subject", "")
    body = parameters.get("body", "")

    msg = _check_creds()
    if msg:
        return msg

    try:
        service = _get_service("gmail", "v1")
        if not service:
            return "No se pudo conectar con Gmail."

        if action == "list":
            q = query or "in:inbox"
            results = service.users().messages().list(
                userId="me", q=q, maxResults=max_results
            ).execute()
            messages = results.get("messages", [])
            if not messages:
                return "No se encontraron mensajes."

            out = []
            for m in messages[:max_results]:
                msg_data = service.users().messages().get(userId="me", id=m["id"]).execute()
                headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                out.append(f"  {headers.get('From', '?')[:40]} — {headers.get('Subject', '(sin asunto)')[:60]}")
            return "Correos:\n" + "\n".join(out)

        elif action == "read":
            results = service.users().messages().list(
                userId="me", q=query or "in:inbox", maxResults=1
            ).execute()
            messages = results.get("messages", [])
            if not messages:
                return "No hay mensajes para leer."
            m = messages[0]
            msg_data = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            payload = msg_data.get("payload", {})
            parts = []
            if "parts" in payload:
                for p in payload["parts"]:
                    if p.get("mimeType") == "text/plain":
                        data = p.get("body", {}).get("data", "")
                        if data:
                            parts.append(base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")[:500])
            body_text = parts[0] if parts else "(sin contenido texto)"
            return (
                f"De: {headers.get('From', '?')}\n"
                f"Asunto: {headers.get('Subject', '(sin asunto)')}\n"
                f"Fecha: {headers.get('Date', '?')}\n"
                f"---\n{body_text}"
            )

        elif action == "unread":
            results = service.users().messages().list(
                userId="me", q="in:inbox is:unread", maxResults=max_results
            ).execute()
            messages = results.get("messages", [])
            count = len(messages)
            return f"Tenés {count} mensajes sin leer." if count > 0 else "No tenés mensajes sin leer."

        elif action == "send":
            if not to or not subject or not body:
                return "Necesito 'to', 'subject' y 'body' para enviar."
            message = EmailMessage()
            message.set_content(body)
            message["To"] = to
            message["Subject"] = subject
            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": encoded}).execute()
            return f"Correo enviado a {to}."

        else:
            return f"Acción '{action}' no reconocida. Acciones: list, read, unread, send."

    except ImportError:
        return "Falta google-api-python-client. Ejecutá: pip install google-api-python-client google-auth-oauthlib"
    except Exception as e:
        return f"Error en Gmail: {e}"
