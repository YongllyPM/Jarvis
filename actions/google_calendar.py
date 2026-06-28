from ._google_auth import _get_service, _check_creds
from datetime import datetime, timezone


def google_calendar(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    summary = parameters.get("summary", "")
    start_time = parameters.get("start_time", "")
    end_time = parameters.get("end_time", "")
    max_results = parameters.get("max_results", 10)

    msg = _check_creds()
    if msg:
        return msg

    try:
        service = _get_service("calendar", "v3")
        if not service:
            return "No se pudo conectar con Google Calendar."

        now = datetime.now(timezone.utc).isoformat()

        if action == "list":
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = events_result.get("items", [])
            if not events:
                return "No hay eventos próximos en tu calendario."
            out = []
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date", "?"))
                out.append(f"  {start[:16]} → {e['summary']}")
            return "Próximos eventos:\n" + "\n".join(out)

        elif action == "today":
            from datetime import timedelta
            end_of_day = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                timeMax=end_of_day.isoformat(),
                maxResults=30,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            events = events_result.get("items", [])
            if not events:
                return "No tenés eventos hoy."
            out = []
            for e in events:
                start = e["start"].get("dateTime", e["start"].get("date", "?"))
                out.append(f"  {start[:16]} → {e['summary']}")
            return "Eventos de hoy:\n" + "\n".join(out)

        elif action == "add":
            if not summary:
                return "Necesito un 'summary' para el evento."
            from datetime import timedelta
            start = datetime.now(timezone.utc)
            event = {
                "summary": summary,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": (start + timedelta(hours=1)).isoformat(), "timeZone": "UTC"},
            }
            if start_time:
                event["start"] = {"dateTime": start_time, "timeZone": "UTC"}
                event["end"] = {"dateTime": end_time or start_time, "timeZone": "UTC"}
            created = service.events().insert(calendarId="primary", body=event).execute()
            return f"Evento creado: {created.get('htmlLink', summary)}"

        else:
            return f"Acción '{action}' no reconocida. Acciones: list, today, add."

    except ImportError:
        return "Falta google-api-python-client. Ejecutá: pip install google-api-python-client google-auth-oauthlib"
    except Exception as e:
        return f"Error en Google Calendar: {e}"
