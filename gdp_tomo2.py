from __future__ import annotations
from typing import Any
import base64, json, zlib
import pandas as pd

_PAYLOAD = "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"
SOURCE = "GDP-2024 - Tomo II, Volumen 4"
DECREE = "Decreto Ejecutivo No. 44762-MOPT"
PERIOD_TABLE = {
    (6,3):("Tabla 301-02",39),(6,4):("Tabla 301-03",40),(6,6):("Tabla 301-04",40),(6,9):("Tabla 301-05",41),(6,11):("Tabla 301-06",41),
    (8,3):("Tabla 301-07",42),(8,4):("Tabla 301-08",42),(8,6):("Tabla 301-09",43),(8,9):("Tabla 301-10",43),(8,11):("Tabla 301-11",44),
    (10,3):("Tabla 301-12",44),(10,4):("Tabla 301-13",45),(10,6):("Tabla 301-14",45),(10,9):("Tabla 301-15",46),(10,11):("Tabla 301-16",46),
    (12,3):("Tabla 301-17",47),(12,4):("Tabla 301-18",47),(12,6):("Tabla 301-19",48),(12,9):("Tabla 301-20",48),(12,11):("Tabla 301-21",49),
}

def classify_tpd(tpd: float) -> str | None:
    if tpd < 0: return None
    if tpd <= 500: return "T500"
    if tpd <= 800: return "T800"
    if tpd <= 1200: return "T1200"
    if tpd <= 2000: return "T2000"
    if tpd <= 3500: return "T3500"
    return None

def classify_cbr(cbr: float) -> int | None:
    if cbr < 3: return None
    if cbr < 4: return 3
    if cbr < 6: return 4
    if cbr < 9: return 6
    if cbr < 11: return 9
    return 11

def classify_heavy_pct(pct: float) -> str | None:
    if pct < 0: return None
    if pct <= 3.0: return "3"
    if pct <= 4.0: return "4"
    if pct <= 5.0: return "5"
    if pct <= 7.0: return "7"
    if pct <= 8.5: return "8.5"
    if pct <= 14.0: return "14"
    if pct <= 15.0: return "15"
    return None

def _load():
    obj=json.loads(zlib.decompress(base64.b64decode(_PAYLOAD)).decode("utf-8"))
    return pd.DataFrame(obj["assign"]), pd.DataFrame(obj["struct"])

def select_structures(tpd: float, heavy_pct: float, cbr: float, period: int) -> dict[str, Any]:
    criteria=[]
    tc=classify_tpd(tpd); cc=classify_cbr(cbr); pc=classify_heavy_pct(heavy_pct)
    if tc is None:
        criteria.append({"estado":"fuera_alcance","variable":"TPD","valor":tpd,"criterio":"TPD > 3500 veh/dia","referencia":"Seccion 201.01"})
    else: criteria.append({"estado":"cumple","variable":"TPD","valor":tpd,"categoria":tc,"referencia":"Seccion 201.01"})
    if cc is None:
        criteria.append({"estado":"fuera_alcance","variable":"CBR","valor":cbr,"criterio":"CBR < 3%","referencia":"Seccion 201.02"})
    else: criteria.append({"estado":"cumple","variable":"CBR","valor":cbr,"categoria":f"CBR {cc}%","referencia":"Seccion 201.02"})
    if pc is None:
        criteria.append({"estado":"fuera_alcance","variable":"Pesados","valor":heavy_pct,"criterio":"Pesados > 15%","referencia":"Seccion 201.03"})
    else: criteria.append({"estado":"cumple","variable":"Pesados","valor":heavy_pct,"categoria":f"P{pc}%","referencia":"Seccion 201.03"})
    if period not in (6,8,10,12):
        criteria.append({"estado":"fuera_catalogo","variable":"Periodo","valor":period,"criterio":"Solo 6, 8, 10 o 12 anos; sin interpolacion","referencia":"Division 300, Tablas 301-02 a 301-21"})
    else: criteria.append({"estado":"cumple","variable":"Periodo","valor":period,"referencia":"Division 300"})
    if tc is None or cc is None or pc is None or period not in (6,8,10,12):
        return {"status":"fuera_alcance","source":SOURCE,"decree":DECREE,"criteria":criteria,"alternatives":[]}
    table,page=PERIOD_TABLE[(period,cc)]
    assign,structs=_load()
    row=assign[(assign.periodo_anios==period)&(assign.cbr_categoria==cc)&(assign.pesados_categoria.astype(str).str.rstrip("0").str.rstrip(".")==pc)&(assign.tpd_categoria==tc)]
    if row.empty:
        return {"status":"sin_alternativa","source":SOURCE,"decree":DECREE,"table":table,"page":page,"criteria":criteria,"alternatives":[]}
    r=row.iloc[0]
    codes=[x for x in str(r.estructuras).split('|') if x and x!='nan']
    alternatives=[]
    for code in codes:
        sr=structs[structs.codigo==code]
        if sr.empty: continue
        s=sr.iloc[0]
        thickness=float(s.mac_cm)+float(s.base_granular_cm)+float(s.base_estabilizada_cm)+float(s.subbase_cm)
        alternatives.append({
            "codigo":code,"mac_cm":float(s.mac_cm),"base_granular_cm":float(s.base_granular_cm),"base_estabilizada_cm":float(s.base_estabilizada_cm),"subbase_cm":float(s.subbase_cm),
            "tratamiento_superficial":str(s.tratamiento_superficial).lower() in ('true','1','si','sí'),"espesor_total_capas_cm":thickness,
            "trazabilidad":{"fuente":SOURCE,"decreto":DECREE,"definicion_estructura":"Tabla 301-01, pagina 38","asignacion":f"{table}, pagina {page}","criterio":f"Periodo {period} anos; CBR {cc}%; pesados P{pc}%; TPD {tc}","celda_original":str(r.raw_cell),"nota_extraccion":str(r.nota_extraccion) if pd.notna(r.nota_extraccion) else ""}
        })
    return {"status":"ok" if alternatives else "sin_alternativa","source":SOURCE,"decree":DECREE,"table":table,"page":page,"categories":{"tpd":tc,"cbr":cc,"pesados":pc,"periodo":period},"criteria":criteria,"alternatives":alternatives}


def nearby_catalog_options(tpd: float, heavy_pct: float, cbr: float, period: int) -> list[dict[str, Any]]:
    """Return only explicitly tabulated nearby cells; never interpolate a structure."""
    candidates: list[dict[str, Any]] = []

    def add(kind: str, value: float, result: dict[str, Any], note: str, distance: float) -> None:
        codes = [str(alt.get("codigo", "")) for alt in result.get("alternatives", []) if alt.get("codigo")]
        if not codes:
            return
        candidates.append({
            "ajuste": kind,
            "valor": value,
            "estructuras": ", ".join(codes),
            "tabla": result.get("table", ""),
            "pagina": result.get("page"),
            "advertencia": note,
            "distancia": float(distance),
        })

    for candidate_period in (6, 8, 10, 12):
        if candidate_period == period:
            continue
        result = select_structures(tpd, heavy_pct, cbr, candidate_period)
        add(
            "Periodo de diseño",
            candidate_period,
            result,
            "Solo procede si el periodo adoptado por el proyecto se cambia y documenta.",
            abs(candidate_period - period),
        )

    for candidate_cbr in (3, 4, 6, 9, 11):
        if classify_cbr(cbr) == candidate_cbr:
            continue
        result = select_structures(tpd, heavy_pct, float(candidate_cbr), period)
        add(
            "Categoría CBR",
            candidate_cbr,
            result,
            "Solo procede con resultados geotécnicos representativos o mejoramiento verificado.",
            abs(candidate_cbr - cbr),
        )

    for candidate_heavy in (3.0, 4.0, 5.0, 7.0, 8.5, 14.0, 15.0):
        if classify_heavy_pct(heavy_pct) == str(candidate_heavy).rstrip("0").rstrip("."):
            continue
        result = select_structures(tpd, candidate_heavy, cbr, period)
        add(
            "Pesados (%)",
            candidate_heavy,
            result,
            "Es solo referencia; no cambie el tránsito sin respaldo del estudio correspondiente.",
            abs(candidate_heavy - heavy_pct),
        )

    candidates.sort(key=lambda item: (item["distancia"], item["ajuste"], item["valor"]))
    return candidates
