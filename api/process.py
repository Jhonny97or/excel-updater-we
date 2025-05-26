# -*- coding: utf-8 -*-
import os, pandas as pd, numpy as np, datetime as dt, re, unicodedata
from dateutil.relativedelta import relativedelta
from io import BytesIO
from vercel import VercelRequest, VercelResponse
from msal import ConfidentialClientApplication       # <─ OneDrive auth
import requests, json, tempfile, zipfile             #  (para ↓ descarga)

# ───────────────── helpers ─────────────────────────
def norm_code(x: str) -> str:
    if pd.isna(x): return ""
    t = unicodedata.normalize("NFKD", str(x).upper()).replace("\u00A0", "")
    return re.sub(r"[^A-Z0-9]", "", t)

def run_updates(inv_stream, ven_stream, period):
    yr, mo = map(int, period.split("-"))

    # 1) Inventario
    inv_raw = pd.concat(pd.read_excel(inv_stream, sheet_name=None).values(), ignore_index=True)
    inv_raw.columns = inv_raw.columns.str.strip().str.replace(r"\.$", "", regex=True)
    inv = inv_raw.rename(columns={
        "Número de artículo":"Product",
        "TTL":"OnHandQty",
        "Precio promedio total":"AvgPriceTotal"
    })
    inv["Product"] = inv["Product"].map(norm_code)

    # 2) Ventas
    ven_raw = pd.concat(pd.read_excel(ven_stream, sheet_name=None).values(), ignore_index=True)
    ven = ven_raw.rename(columns={
        "Número de artículo":"Product",
        "Cantidad":"Qty",
        "Total líneas":"TotalLineas",
        "Total Costo":"TotalCosto",
        "Día":"Dia","Mes":"Mes","Año":"Anio"
    })
    ven["Product"] = ven["Product"].map(norm_code)
    ven["Qty"] = pd.to_numeric(ven["Qty"], errors="coerce").fillna(0)
    for c in ("Dia","Mes","Anio"):
        ven[c] = pd.to_numeric(ven[c], errors="coerce")
    ven["Fecha"] = pd.to_datetime(dict(year=ven["Anio"], month=ven["Mes"], day=ven["Dia"]), errors="coerce")

    # 3) Ventas del mes
    mes_names = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
    qty_col = f"{mes_names[mo-1]}-qty-{yr}"
    ven_mes = ven[(ven["Anio"]==yr)&(ven["Mes"]==mo)]
    qty_mes = ven_mes.groupby("Product",as_index=False)["Qty"].sum()
    inv = inv.merge(qty_mes.rename(columns={"Qty":qty_col}), on="Product", how="left")
    inv[qty_col] = inv[qty_col].fillna(0).astype(int)

    # 4) Últimos 12 meses
    first = dt.date(yr,mo,1)
    ini12 = pd.Timestamp(first) - relativedelta(months=12)
    fin12 = pd.Timestamp(first) + relativedelta(months=1)
    ven12 = ven[(ven["Fecha"]>=ini12)&(ven["Fecha"]<fin12)]
    sales12 = ven12.groupby("Product").agg(
        Sls12=("TotalLineas","sum"),
        Cogs12=("TotalCosto","sum"),
        Qty12=("Qty","sum")
    ).reset_index().fillna(0)
    inv = inv.merge(sales12, on="Product", how="left").fillna(0)

    # 5) Métricas
    inv["Inventory$"]  = np.where(inv["OnHandQty"]>0, inv["OnHandQty"]*inv["AvgPriceTotal"].fillna(0),0)
    inv["12-Mo-Sls$"]  = inv["Sls12"];   inv["12-Mo-COGS$"] = inv["Cogs12"];  inv["12-Mo-Sales"]= inv["Qty12"]
    inv["Gross Margin"]= np.where(inv["12-Mo-Sls$"]>0,(inv["12-Mo-Sls$"]-inv["12-Mo-COGS$"])/inv["12-Mo-Sls$"],0)
    inv["Dy  Stock"]   = np.where(inv["12-Mo-COGS$"]>0, inv["Inventory$"]/(inv["12-Mo-COGS$"]/365),0)
    inv["GMROI"]       = np.where(inv["Inventory$"]>0,(inv["12-Mo-Sls$"]-inv["12-Mo-COGS$"])/inv["Inventory$"],0)

    # 6) ABC
    inv = inv.sort_values("12-Mo-COGS$",ascending=False).reset_index(drop=True)
    inv["Accum $"] = inv["12-Mo-COGS$"].cumsum(); inv["Accum%"] = inv["Accum $"]/inv["12-Mo-COGS$"].sum()
    inv["COGS Rank"]= inv["Accum%"].apply(lambda p:"A" if p<=.8 else "B" if p<=.95 else "C" if p<=.99 else "D")

    # 7) Filtro mínimo
    inv = inv[(inv["OnHandQty"]>0) | (inv["Product"].isin(ven["Product"]))]

    return inv

# ───────────────────────── OneDrive helper (delegado) ──────────────────────
GRAPH_SCOPES = ["Files.Read.All"]

def get_token(auth_code: str, redirect_uri: str):
    client   = ConfidentialClientApplication(
        os.environ["NEXT_PUBLIC_AZURE_CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{os.environ['NEXT_PUBLIC_AZURE_TENANT_ID']}",
        client_credential=os.environ["AZURE_CLIENT_SECRET"]
    )
    return client.acquire_token_by_authorization_code(auth_code, scopes=GRAPH_SCOPES, redirect_uri=redirect_uri)

# ──────────────────────────── Vercel handler ───────────────────────────────
def handler(req: VercelRequest) -> VercelResponse:
    try:
        # 1) Autorización: viene code & state desde el front
        if "code" in req.query:
            token = get_token(req.query["code"], req.query["redirect_uri"])
            return VercelResponse(json.dumps(token), status=200, headers={"Content-Type":"application/json"})

        # 2) Procesamiento normal (files subidos)
        inv_file = req.files["inv"].stream
        ven_file = req.files["ven"].stream
        period   = req.form["period"]

        df = run_updates(inv_file, ven_file, period)

        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="InvActualizado")

        return VercelResponse(
            bio.getvalue(), status=200,
            headers={
              "Content-Type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              "Content-Disposition":f'attachment; filename=\"TblInventario_actualizado_{period}.xlsx\"'
            }
        )

    except Exception as e:
        return VercelResponse(str(e), status=500, headers={"Content-Type":"text/plain"})
