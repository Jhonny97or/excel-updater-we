// api/config.js
export default function handler(request, response) {
  try {
    const cfg = {
      clientId: process.env.AZURE_CLIENT_ID,
      tenantId: process.env.AZURE_TENANT_ID,
      authority: `https://login.microsoftonline.com/${process.env.AZURE_TENANT_ID}`,
      scopes:  ["Files.Read.All"]        // lo mismo que pediste en Azure
    };

    if (!cfg.clientId || !cfg.tenantId) {
      throw new Error("Env vars missing");
    }

    response.setHeader("Cache-Control", "public, max-age=3600");
    response.setHeader("Content-Type", "application/javascript");
    response.status(200).send(
      `window.EXCEL_UP_CFG = ${JSON.stringify(cfg)};`
    );
  } catch (err) {
    response.status(500).send("config error: " + err.message);
  }
}


