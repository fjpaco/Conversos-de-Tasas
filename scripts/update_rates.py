"""Descarga UF, dólar observado (CLP) y USD/MXN y los guarda en tasas.json.

Lo ejecuta GitHub Actions todos los días. No necesita librerías externas.
Si existe la variable BANXICO_TOKEN, usa el FIX oficial de Banxico para USD/MXN.
Si una fuente falla, conserva el último valor bueno que había en tasas.json.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tasas.json"
UA = {"User-Agent": "conversor-tasas/1.0 (+github actions)"}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def load_previous():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


def chile():
    """UF y dólar observado desde mindicador.cl (Banco Central de Chile)."""
    d = get_json("https://mindicador.cl/api")
    out = {}
    if d.get("uf", {}).get("valor"):
        out["uf"] = {"v": float(d["uf"]["valor"]), "date": d["uf"]["fecha"][:10], "src": "mindicador"}
    if d.get("dolar", {}).get("valor"):
        out["clp"] = {"v": float(d["dolar"]["valor"]), "date": d["dolar"]["fecha"][:10], "src": "dólar observado"}
    return out


def banxico_fix(token):
    """FIX oficial de Banxico (serie SF43718)."""
    d = get_json(
        "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno",
        {"Bmx-Token": token},
    )
    dato = d["bmx"]["series"][0]["datos"][0]
    dd, mm, yyyy = dato["fecha"].split("/")
    return {"v": float(dato["dato"].replace(",", "")), "date": f"{yyyy}-{mm}-{dd}", "src": "FIX Banxico"}


def market():
    """USD/MXN y USD/CLP de mercado, con una fuente de respaldo."""
    try:
        d = get_json("https://open.er-api.com/v6/latest/USD")
        if d.get("result") != "success":
            raise ValueError("er-api sin datos")
        date = datetime.fromtimestamp(d["time_last_update_unix"], tz=timezone.utc).strftime("%Y-%m-%d")
        return {"mxn": d["rates"]["MXN"], "clp": d["rates"]["CLP"], "date": date, "src": "er-api"}
    except Exception as e:
        print(f"er-api falló: {e}")
        d = get_json("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json")
        return {"mxn": d["usd"]["mxn"], "clp": d["usd"]["clp"], "date": d["date"], "src": "currency-api"}


def main():
    prev = load_previous()
    rates = {k: prev[k] for k in ("mxn", "clp", "uf") if k in prev}
    errors = []

    try:
        rates.update(chile())
    except Exception as e:
        errors.append(f"mindicador: {e}")

    mkt = None
    try:
        mkt = market()
    except Exception as e:
        errors.append(f"mercado: {e}")

    token = os.environ.get("BANXICO_TOKEN", "").strip()
    got_fix = False
    if token:
        try:
            rates["mxn"] = banxico_fix(token)
            got_fix = True
        except Exception as e:
            errors.append(f"Banxico: {e}")

    if mkt:
        if not got_fix:
            rates["mxn"] = {"v": float(mkt["mxn"]), "date": mkt["date"], "src": mkt["src"]}
        if rates.get("clp", {}).get("src") != "dólar observado":
            rates["clp"] = {"v": float(mkt["clp"]), "date": mkt["date"], "src": mkt["src"]}

    missing = [k for k in ("mxn", "clp", "uf") if k not in rates]
    if missing:
        raise SystemExit(f"Faltan tasas y no hay valores previos: {missing}. Errores: {errors}")

    rates["checked"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rates["errors"] = errors
    OUT.write_text(json.dumps(rates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
