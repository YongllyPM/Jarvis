from ._google_auth import _get_service, _check_creds
import os
import io
from pathlib import Path


def google_drive(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list")
    query = parameters.get("query", "")
    file_id = parameters.get("file_id", "")
    folder_id = parameters.get("folder_id", "root")
    name = parameters.get("name", "")

    msg = _check_creds()
    if msg:
        return msg

    try:
        service = _get_service("drive", "v3")
        if not service:
            return "No se pudo conectar con Google Drive."

        if action == "list":
            q = f"'{folder_id}' in parents and trashed=false"
            if query:
                q += f" and name contains '{query}'"
            results = service.files().list(
                q=q, pageSize=20, fields="files(id, name, mimeType, size, modifiedTime)"
            ).execute()
            files = results.get("files", [])
            if not files:
                return "No se encontraron archivos en Drive."
            out = []
            for f in files:
                tipo = "📄" if "folder" not in f.get("mimeType", "") else "📁"
                size = f" ({int(f.get('size', 0)) // 1024}KB)" if f.get("size") else ""
                out.append(f"  {tipo} {f['name']}{size}")
            return "Drive:\n" + "\n".join(out)

        elif action == "search":
            q = f"name contains '{query}' and trashed=false"
            results = service.files().list(
                q=q, pageSize=10, fields="files(id, name, mimeType)"
            ).execute()
            files = results.get("files", [])
            if not files:
                return f"No encontré '{query}' en Drive."
            out = []
            for f in files:
                out.append(f"  {f['name']} (ID: {f['id'][:20]}...)")
            return "Resultados:\n" + "\n".join(out)

        elif action == "info":
            if not file_id:
                return "Necesito 'file_id'."
            f = service.files().get(fileId=file_id, fields="id,name,mimeType,size,modifiedTime,owners").execute()
            return (
                f"Nombre: {f.get('name', '?')}\n"
                f"Tipo: {f.get('mimeType', '?')}\n"
                f"Tamaño: {int(f.get('size', 0)) // 1024}KB\n"
                f"Modificado: {f.get('modifiedTime', '?')}"
            )

        elif action == "download":
            if not file_id:
                return "Necesito 'file_id'."
            if not name:
                name = service.files().get(fileId=file_id, fields="name").execute().get("name", "download")
            request = service.files().get_media(fileId=file_id)
            import io as _io
            fh = _io.BytesIO()
            downloader = None
            try:
                from googleapiclient.http import MediaIoBaseDownload
                downloader = MediaIoBaseDownload(fh, request)
            except ImportError:
                return "googleapiclient no disponible."
            done = False
            while not done:
                _, done = downloader.next_chunk()
            dest = Path.home() / "Downloads" / name
            dest.write_bytes(fh.getvalue())
            return f"Archivo descargado: {dest}"

        elif action == "create":
            if not name:
                return "Necesito 'name' para crear el archivo."
            file_metadata = {"name": name, "parents": [folder_id]}
            from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
            import io as _io
            media = MediaIoBaseUpload(_io.BytesIO(b""), mimetype="text/plain", resumable=True)
            f = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            return f"Archivo creado en Drive (ID: {f['id'][:20]}...)."

        else:
            return f"Acción '{action}' no reconocida. Acciones: list, search, info, download, create."

    except ImportError:
        return "Falta google-api-python-client. Ejecutá: pip install google-api-python-client google-auth-oauthlib"
    except Exception as e:
        return f"Error en Google Drive: {e}"
