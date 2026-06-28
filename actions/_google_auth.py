import os
import json
from pathlib import Path

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_TOKEN_FILE = _CONFIG_DIR / "google_token.json"
_CRED_FILE = _CONFIG_DIR / "google_credentials.json"
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def _get_service(service_name: str, version: str):
    """Authenticate and return a Google API service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if _TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CRED_FILE.exists():
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(_CRED_FILE), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build(service_name, version, credentials=creds)


def _check_creds() -> str | None:
    if not _CRED_FILE.exists():
        return (
            "Google no está configurado. "
            "Descargá 'google_credentials.json' desde https://console.cloud.google.com/ "
            "y guardalo en la carpeta 'config/'."
        )
    return None
