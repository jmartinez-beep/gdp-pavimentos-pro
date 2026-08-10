from __future__ import annotations

import pandas as pd
import streamlit as st

from gdp_tomo2 import DECREE, SOURCE, select_structures

st.set_page_config(page_title="Tomo II GDP-2024 | GDP Pavimentos Pro", page_icon="📚", layout="wide")

st.title("📚 GDP-2024 · Tomo II — Catálogo oficial con trazabilidad")
st.caption(
    "Selección sistemática de estructuras de bajo volumen conforme al GDP-2024 Tomo II. "
    "Cada resultado conserva la tabla, página, criterio de selección y celda fuente usada."
)

with st.expander("Alcance normativo y fuente", expanded=False):
    st.markdown(f"**Fuente:** {SOURCE}")
    st.markdown(f"**Marco de adopción:** {DECREE}")
    st.markdown(
        "El selector aplica los límites del Tomo II: TPD hasta 3 500 veh/día, "
        "vehículos pesados hasta 15 %, CBR de subrasante desde 3 % y períodos de diseño "
        "discretos de 6, 8, 10 o 12 años. No se interpola entre tablas."
    )

c1, c2, c3, c4 = st.columns(4)
tpd = c1.number_input("TPD (veh/día)", min_value=0.0, value=890.0, step=10.0)
heavy_pct = c2.number_input("Vehículos pesados (%)", min_value=0.0, value=10.0, step=0.5)
cbr = c3.number_input("CBR subrasante (%)", min_value=0.0, value=5.0, step=0.5)
period = c4.selectbox("Período de diseño (años)", [6, 8, 10, 12], index=2)

result = select_structures(tpd=tpd, heavy_pct=heavy_pct, cbr=cbr, period=int(period))

st.subheader("Control de aplicabilidad")
criteria_df = pd.DataFrame(result.get("criteria", []))
if not criteria_df.empty:
    st.dataframe(criteria_df, use_container_width=True, hide_index=True)

status = result.get("status")
if status == "fuera_alcance":
    st.error(
        "El caso ingresado está fuera del alcance directo del catálogo del Tomo II o no corresponde "
        "a uno de los períodos tabulados. Revise los controles anteriores; no se emite una estructura normativa."
    )
    st.stop()

if status == "sin_alternativa":
    st.warning(
        "La combinación está dentro del dominio general del Tomo II, pero la celda consultada no contiene "
        "una alternativa estructural interpretable. Se conserva la trazabilidad para revisión manual."
    )
    st.json(result)
    st.stop()

cats = result.get("categories", {})
mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Categoría TPD", cats.get("tpd", "—"))
mc2.metric("Categoría CBR", str(cats.get("cbr", "—")))
mc3.metric("Categoría pesados", f"P{cats.get('pesados', '—')}%")
mc4.metric("Tabla consultada", result.get("table", "—"))

st.subheader("Alternativas normativas")
rows = []
for alt in result.get("alternatives", []):
    rows.append(
        {
            "Código": alt["codigo"],
            "MAC (cm)": alt["mac_cm"],
            "Base granular (cm)": alt["base_granular_cm"],
            "Base estabilizada (cm)": alt["base_estabilizada_cm"],
            "Subbase (cm)": alt["subbase_cm"],
            "Tratamiento superficial": "Sí" if alt["tratamiento_superficial"] else "No",
            "Total capas cuantificadas (cm)": alt["espesor_total_capas_cm"],
        }
    )
alt_df = pd.DataFrame(rows)
st.dataframe(alt_df, use_container_width=True, hide_index=True)

st.caption(
    "Nota: cuando la estructura incluye tratamiento superficial, el Tomo II lo identifica como componente "
    "de la estructura; el total mostrado suma únicamente los espesores numéricos explícitos almacenados."
)

st.subheader("Trazabilidad por resultado")
for alt in result.get("alternatives", []):
    tr = alt["trazabilidad"]
    with st.expander(f"{alt['codigo']} · {tr['asignacion']}", expanded=True):
        t1, t2 = st.columns(2)
        with t1:
            st.markdown(f"**Fuente:** {tr['fuente']}")
            st.markdown(f"**Decreto:** {tr['decreto']}")
            st.markdown(f"**Definición de estructura:** {tr['definicion_estructura']}")
            st.markdown(f"**Asignación:** {tr['asignacion']}")
        with t2:
            st.markdown(f"**Criterio:** {tr['criterio']}")
            st.markdown(f"**Celda original:** `{tr['celda_original']}`")
            if tr.get("nota_extraccion"):
                st.warning(f"Nota de extracción: {tr['nota_extraccion']}")

export_rows = []
for alt in result.get("alternatives", []):
    tr = alt["trazabilidad"]
    export_rows.append(
        {
            **{k: v for k, v in alt.items() if k != "trazabilidad"},
            "fuente": tr["fuente"],
            "decreto": tr["decreto"],
            "definicion_estructura": tr["definicion_estructura"],
            "asignacion": tr["asignacion"],
            "criterio": tr["criterio"],
            "celda_original": tr["celda_original"],
            "nota_extraccion": tr["nota_extraccion"],
        }
    )
export_df = pd.DataFrame(export_rows)
st.download_button(
    "Descargar resultados con trazabilidad (CSV)",
    data=export_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="gdp_tomo2_resultado_trazable.csv",
    mime="text/csv",
)

st.info(
    "Esta página complementa la interfaz histórica de Estructura. Para decisiones de Tomo II, "
    "use este selector trazable como referencia normativa de la versión actual."
)
