// api/config.js
/**
 * Devuelve la configuración MSAL al front-end
 * (los valores se insertan desde las variables de entorno de Vercel)
 */

export default function handler(req, res) {
  const { AZURE_CLIENT_ID, AZURE_TENANT_ID } = process.env;

  if (!AZURE_CLIENT_ID || !AZURE_TENANT_ID) {
    return res
      .status(500)
      .setHeader("Content-Type", "text/plain")
      .end("❌ Falta configurar AZURE_CLIENT_ID o AZURE_TENANT_ID en Vercel");
  }

  /* authority v2: https://login.microsoftonline.com/<tenant>/ */
  const authority =
    "https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/";

  res
    .status(200)
    .setHeader("Content-Type", "application/javascript")
    .end(
      `window.EXCEL_UP_CFG = ${JSON.stringify({
        clientId: AZURE_CLIENT_ID,
        authority,
      })};`
    );
}
