// /api/config.js   — handler Node para Vercel
export default function handler(req, res) {
  const { AZURE_CLIENT_ID, AZURE_TENANT_ID } = process.env;

  /* ── valida que las env-vars existan ───────────────────────── */
  if (!AZURE_CLIENT_ID || !AZURE_TENANT_ID) {
    console.error("⛔  AZURE env vars missing", {
      AZURE_CLIENT_ID,
      AZURE_TENANT_ID,
    });
    return res
      .status(500)
      .send("❌ Variables de entorno faltantes en Vercel");
  }

  const authority =
    "https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/";

  /* ── responde JavaScript que el front lee directamente ─────── */
  res
    .setHeader("Content-Type", "application/javascript")
    .send(
      `window.EXCEL_UP_CFG = ${JSON.stringify({
        clientId: AZURE_CLIENT_ID,
        authority,
      })};`
    );
}

