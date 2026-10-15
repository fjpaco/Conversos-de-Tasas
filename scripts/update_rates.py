"""Descarga UF, dólar observado (CLP) y USD/MXN y los guarda en tasas.json.

Lo ejecuta GitHub Actions todos los días a las 9:30 (hora del centro de México).
Cada tasa guarda 'date' (fecha oficial del valor) y 'fetched' (cuándo se descargó).
No necesita librerías externas.

Fuentes, en orden de preferencia:
  UF y dólar observado: mindicador.cl (con reintentos) y, si falla, la API de la CMF
                        (requiere el secreto CMF_API_KEY).
  USD/MXN: FIX de Banxico (requiere el secreto BANXICO_TOKEN) o mercado (er-api).
  USD/CLP de mercado: solo si no se obtuvo el dólar observado.
Si una fuente falla, se conserva el último valor bueno que había en tasas.json.
"""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "tasas.json"
UA = {"User-Agent": "Mozilla/5.0 (conversor-tasas; GitHub Actions)", "Accept": "application/json"}


def get_json(url, headers=None, timeout=20, tries=1, wait=10):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            print(f"  intento {i + 1}/{tries} falló para {url.split('?')[0]}: {e}")
            if i < tries - 1:
                time.sleep(wait)
    raise last


def num_cl(s):
    """Convierte '41.057,20' a 41057.2"""
    return float(str(s).replace(".", "").replace(",", "."))


def load_previous():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------- Chile ----------
def mindicador(tipo):
    d = get_json(f"https://mindicador.cl/api/{tipo}", timeout=40, tries=3, wait=15)
    ult = d["serie"][0]
    return float(ult["valor"]), ult["fecha"][:10]


def cmf(tipo, key):
    """API oficial de la Comisión para el Mercado Financiero de Chile."""
    d = get_json(f"https://api.cmfchile.cl/api-sbifv3/recursos_api/{tipo}?apikey={key}&formato=json",
                 timeout=30, tries=2)
    lista = d["UFs"] if tipo == "uf" else d["Dolares"]
    return num_cl(lista[0]["Valor"]), lista[0]["Fecha"][:10]


def chile_rate(tipo, nombre_src, errors):
    """tipo: 'uf' o 'dolar'. Devuelve dict de tasa o None."""
    try:
        v, date = mindicador(tipo)
        return {"v": v, "date": date, "src": "mindicador" if tipo == "uf" else nombre_src}
    except Exception as e:
        errors.append(f"mindicador {tipo}: {e}")
    key = os.environ.get("CMF_API_KEY", "").strip()
    if key:
        try:
            v, date = cmf(tipo, key)
            return {"v": v, "date": date, "src": "CMF" if tipo == "uf" else "dólar observado (CMF)"}
        except Exception as e:
            errors.append(f"CMF {tipo}: {e}")
    return None


# ---------- México y mercado ----------
def banxico_fix(token):
    d = get_json("https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43718/datos/oportuno",
                 {"Bmx-Token": token}, timeout=30, tries=2)
    dato = d["bmx"]["series"][0]["datos"][0]
    dd, mm, yyyy = dato["fecha"].split("/")
    return {"v": float(dato["dato"].replace(",", "")), "date": f"{yyyy}-{mm}-{dd}", "src": "FIX Banxico"}


def market():
    try:
        d = get_json("https://open.er-api.com/v6/latest/USD", tries=2)
        if d.get("result") != "success":
            raise ValueError("er-api sin datos")
        date = datetime.fromtimestamp(d["time_last_update_unix"], tz=timezone.utc).strftime("%Y-%m-%d")
        return {"mxn": d["rates"]["MXN"], "clp": d["rates"]["CLP"], "date": date, "src": "er-api"}
    except Exception as e:
        print(f"er-api falló: {e}")
        d = get_json("https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json", tries=2)
        return {"mxn": d["usd"]["mxn"], "clp": d["usd"]["clp"], "date": d["date"], "src": "currency-api"}


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    prev = load_previous()
    rates = {k: prev[k] for k in ("mxn", "clp", "uf") if k in prev}
    errors = []

    uf = chile_rate("uf", "mindicador", errors)
    if uf:
        rates["uf"] = {**uf, "fetched": now}

    obs = chile_rate("dolar", "dólar observado", errors)
    if obs:
        rates["clp"] = {**obs, "fetched": now}

    mkt = None
    try:
        mkt = market()
    except Exception as e:
        errors.append(f"mercado: {e}")

    got_fix = False
    token = os.environ.get("BANXICO_TOKEN", "").strip()
    if token:
        try:
            rates["mxn"] = {**banxico_fix(token), "fetched": now}
            got_fix = True
        except Exception as e:
            errors.append(f"Banxico: {e}")

    if mkt:
        if not got_fix:
            rates["mxn"] = {"v": float(mkt["mxn"]), "date": mkt["date"], "src": mkt["src"], "fetched": now}
        if not obs:
            rates["clp"] = {"v": float(mkt["clp"]), "date": mkt["date"], "src": mkt["src"], "fetched": now}

    missing = [k for k in ("mxn", "clp", "uf") if k not in rates]
    if missing:
        raise SystemExit(f"Faltan tasas y no hay valores previos: {missing}. Errores: {errors}")

    rates["checked"] = now
    rates["errors"] = errors
    OUT.write_text(json.dumps(rates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
