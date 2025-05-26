// api/config.js
//
// Devuelve un fragmento <script> con la configuración MSAL que el
// front-end necesita para iniciar sesión (flujo delegado contra OneDrive).

export default function handler(req, res) {
  // 1)  Variables de entorno que configuraste en Vercel
  const { AZURE_CLIENT_ID, AZURE_TENANT_ID } = process.env;

  // 2)  Comprobación rápida: si faltan, devolvemos error visible en consola
  if (!AZURE_CLIENT_ID || !AZURE_TENANT_ID) {
    return res
      .status(500)
      .send(
        "❌ Falta configurar AZURE_CLIENT_ID y/o AZURE_TENANT_ID en Vercel → Settings → Environment Variables."
      );
  }

  // 3)  Construimos la autoridad de login (v2.0)
  const authority = `https://login.microsoftonline.com/${AZURE_TENANT_ID}/`;

  // 4)  Serializamos los datos dentro de window.EXCEL_UP_CFG para que
  //     el HTML pueda leerlos antes de inicializar MSAL.
  const payload = {
    clientId: AZURE_CLIENT_ID,
    authority
  };

  res
    .setHeader("Content-Type", "application/javascript")
    .send(`window.EXCEL_UP_CFG = ${JSON.stringify(payload)};`);
}
