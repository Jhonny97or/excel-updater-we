# api/config.js  (sí, la extensión sigue siendo .js para que el
# navegador lo interprete; Vercel lo ejecuta con python gracias a la
# build @vercel/python).

from vercel import VercelRequest, VercelResponse
import os, json

def handler(req: VercelRequest) -> VercelResponse:
    """
    Genera un pequeño archivo JavaScript que define window.EXCEL_UP_CFG
    con los valores de tus variables de entorno.
    """
    cfg = {
        "clientId":   os.environ.get("AZURE_CLIENT_ID", ""),
        "tenantId":   os.environ.get("AZURE_TENANT_ID", ""),
        # authority = https://login.microsoftonline.com/<TENANT_ID>
        "authority":  f"https://login.microsoftonline.com/{os.environ.get('AZURE_TENANT_ID', '')}"
    }
    js = "window.EXCEL_UP_CFG = " + json.dumps(cfg, indent=2) + ";"
    return VercelResponse(
        js,
        status=200,
        headers={"Content-Type": "application/javascript"}
    )
