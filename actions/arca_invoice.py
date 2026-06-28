import json
import os
import subprocess
from pathlib import Path


def arca_invoice(parameters: dict, player=None) -> str:
    action = parameters.get("action", "info")
    invoice_type = parameters.get("type", "factura")
    amount = parameters.get("amount", 0)
    client = parameters.get("client", "")
    cuit = parameters.get("cuit", "")
    description = parameters.get("description", "")
    output_dir = parameters.get("output_dir", str(Path.home() / "Documents" / "Facturas"))

    cfg = _load_cfg()

    try:
        if action == "info":
            return (
                "📋 ARCA (ex AFIP) — Facturación Argentina\n\n"
                "Para emitir facturas necesitás:\n"
                "  1. CUIT propio (config/api_keys.json → 'arca_cuit')\n"
                "  2. Clave Fiscal nivel 3 o superior\n"
                "  3. Certificado digital (.crt + .key)\n\n"
                "Esta herramienta genera facturas offline en formato JSON/PDF. "
                "La presentación web ante ARCA requiere integración con "
                "su API (WSFEv1) que necesita certificado digital."
            )

        elif action == "generate":
            if not cuit:
                cuit = cfg.get("arca_cuit", "")
            if not cuit:
                return "Necesito 'cuit' (el del cliente) o configurá 'arca_cuit' en api_keys.json."

            invoice = {
                "tipo": invoice_type.upper(),
                "fecha": __import__("datetime").datetime.now().isoformat()[:10],
                "cuit_emisor": cfg.get("arca_cuit", "XXXXXXXXX"),
                "cuit_cliente": cuit,
                "cliente": client or "Consumidor Final",
                "importe": float(amount),
                "descripcion": description or "Servicios",
                "moneda": "ARS",
            }

            os.makedirs(output_dir, exist_ok=True)
            filename = f"factura_{invoice['fecha']}_{cuit}.json"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(invoice, f, ensure_ascii=False, indent=2)

            return (
                f"✅ Factura generada: {filepath}\n"
                f"   Tipo: {invoice['tipo']}\n"
                f"   Cliente: {invoice['cliente']} (CUIT: {cuit})\n"
                f"   Importe: ${amount:,.2f}\n\n"
                "⚠️ Esta factura es offline. Para presentarla en ARCA "
                "necesitás un certificado digital e integración WSFEv1."
            )

        elif action == "list":
            os.makedirs(output_dir, exist_ok=True)
            files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
            if not files:
                return f"No hay facturas en {output_dir}."
            out = []
            for f in sorted(files, reverse=True)[:20]:
                path = os.path.join(output_dir, f)
                try:
                    data = json.loads(Path(path).read_text(encoding="utf-8"))
                    out.append(f"  {f} → {data.get('cliente', '?')} ${data.get('importe', 0):,.2f}")
                except Exception:
                    out.append(f"  {f} → (error al leer)")
            return "Facturas:\n" + "\n".join(out)

        elif action == "cuit":
            # Validate CUIT format
            cuit = cuit or cfg.get("arca_cuit", "")
            if not cuit:
                return "Indicá un CUIT para validar."
            # Simple format check
            clean = cuit.replace("-", "").replace(" ", "")
            if len(clean) != 11:
                return f"❌ CUIT inválido: debe tener 11 dígitos (tiene {len(clean)})."
            return f"✅ CUIT {cuit} con formato válido."

        else:
            return f"Acción '{action}' no reconocida. Acciones: info, generate, list, cuit."

    except Exception as e:
        return f"Error en facturación: {e}"


def _load_cfg() -> dict:
    try:
        path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
