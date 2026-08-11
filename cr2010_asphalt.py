from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pandas as pd
import streamlit as st


@dataclass
class AsphaltCheck:
    etapa: str
    control: str
    estado: str
    severidad: str
    evidencia: str
    referencia: str


def _state(ok: bool | None, na: bool = False) -> str:
    if na:
        return "No aplica"
    if ok is None:
        return "Pendiente"
    return "Cumple" if ok else "No cumple"


def _add(rows: list[AsphaltCheck], etapa: str, control: str, ok: bool | None,
         severidad: str, evidencia: str, referencia: str, na: bool = False) -> None:
    rows.append(AsphaltCheck(etapa, control, _state(ok, na), severidad, evidencia, referencia))


def render_asphalt_cr2010_checklist(project_name: str = "") -> dict[str, Any]:
    """Renderiza un control de proceso para mezcla asfáltica.

    Los límites automáticos se restringen a criterios explícitamente documentados en las
    fuentes de referencia incorporadas. Los parámetros propios del proyecto se registran
    aparte para evitar convertir un valor particular en un requisito general del CR-2010.
    """
    st.subheader("Control CR-2010 — Mezcla asfáltica")
    st.caption(
        "Checklist de apoyo para diseño, producción, colocación, compactación y recepción. "
        "No sustituye la inspección, los ensayos, las especificaciones particulares ni la aceptación contractual."
    )
    st.info(
        "Base normativa: CR-2010 y actualizaciones oficializadas por MOPT. Para mezcla asfáltica se consideran "
        "las secciones 401 (Marshall), 402 (Superpave), 405 (suministro y colocación), 413 (imprimación) y "
        "la referencia de riego de liga aplicable. Los valores particulares del proyecto deben documentarse por separado."
    )

    rows: list[AsphaltCheck] = []

    st.markdown("### 1. Diseño y documentación")
    d1, d2, d3 = st.columns(3)
    with d1:
        design_method = st.selectbox(
            "Método de diseño de mezcla",
            ["Marshall — Sección 401", "Superpave — Sección 402", "Especial / otro — justificar"],
            key="cr2010_mix_method",
        )
        mix_design_approved = st.checkbox("Diseño de mezcla aprobado y vigente", key="cr2010_mix_design_approved")
        binder_cert = st.checkbox("Certificado del cemento asfáltico disponible", key="cr2010_binder_cert")
    with d2:
        aggregate_cert = st.checkbox("Certificados/ensayos de agregados disponibles", key="cr2010_aggregate_cert")
        asphalt_content_doc = st.checkbox("Contenido de asfalto documentado", key="cr2010_asphalt_content_doc")
        lab_identified = st.checkbox("Laboratorio y fecha de ensayos identificados", key="cr2010_lab_identified")
    with d3:
        project_binder = st.text_input("Ligante especificado por el proyecto", value="", placeholder="Ej.: AC-30", key="cr2010_project_binder")
        binder_matches = st.checkbox("El certificado coincide con el ligante especificado", key="cr2010_binder_matches")
        project_spec_ref = st.text_input("Referencia de especificación particular", value="", placeholder="Ej.: IG-013-21 §10.6 p.74", key="cr2010_project_spec_ref")

    _add(rows, "Diseño", "Método de diseño definido", True if design_method else None, "Alta", design_method, "CR-2010 Secciones 401/402")
    _add(rows, "Diseño", "Diseño de mezcla aprobado y vigente", mix_design_approved, "Alta", "Sí" if mix_design_approved else "No", "CR-2010 Secciones 401/402")
    _add(rows, "Materiales", "Certificado del cemento asfáltico", binder_cert, "Alta", project_binder or "Ligante no indicado", "CR-2010 Subsección 702.01/702.02")
    _add(rows, "Materiales", "Certificados y ensayos de agregados", aggregate_cert, "Alta", "Documentados" if aggregate_cert else "Pendientes", "CR-2010 Subsección 703.07")
    _add(rows, "Diseño", "Contenido de asfalto documentado", asphalt_content_doc, "Media", "Documentado" if asphalt_content_doc else "Pendiente", "CR-2010 Secciones 401/402")
    _add(rows, "Documentación", "Laboratorio y fecha identificados", lab_identified, "Media", "Trazable" if lab_identified else "Pendiente", "Control de calidad / expediente")
    _add(rows, "Materiales", "Ligante certificado coincide con especificación del proyecto", binder_matches if project_binder else None, "Alta", project_binder or "No se indicó ligante particular", project_spec_ref or "Especificación particular del proyecto", na=not bool(project_binder))

    st.markdown("### 2. Material reciclado, planta y producción")
    p1, p2, p3 = st.columns(3)
    with p1:
        rap_pct = st.number_input("RAP en la mezcla (% en peso)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="cr2010_rap_pct")
        rap_surface = st.checkbox("Se propone RAP en capa superficial", key="cr2010_rap_surface")
    with p2:
        plant_m156 = st.checkbox("Planta documentada conforme AASHTO M156", key="cr2010_plant_m156")
        automated_controls = st.checkbox("Controles automatizados de producción disponibles", key="cr2010_automated_controls")
        dust_control = st.checkbox("Control de polvo operativo", key="cr2010_dust_control")
    with p3:
        max_binder_temp = st.number_input("Temperatura máxima registrada del cemento asfáltico (°C)", min_value=0.0, max_value=250.0, value=160.0, step=1.0, key="cr2010_max_binder_temp")
        production_records = st.checkbox("Registros de producción/lotes disponibles", key="cr2010_production_records")

    _add(rows, "Materiales", "RAP ≤ 15% en peso", rap_pct <= 15.0, "Alta", f"{rap_pct:.1f}%", "CR-2010 — resumen de requisitos para pavimentos asfálticos")
    _add(rows, "Materiales", "RAP no utilizado en capa superficial", not rap_surface, "Alta", "Sí" if rap_surface else "No", "CR-2010 — resumen de requisitos para pavimentos asfálticos", na=rap_pct <= 0.0)
    _add(rows, "Planta", "Planta conforme AASHTO M156", plant_m156, "Alta", "Verificado" if plant_m156 else "Pendiente", "CR-2010 — requisitos de planta")
    _add(rows, "Planta", "Controles automatizados", automated_controls, "Media", "Verificado" if automated_controls else "Pendiente", "CR-2010 — requisitos de planta")
    _add(rows, "Planta", "Control de polvo", dust_control, "Media", "Verificado" if dust_control else "Pendiente", "CR-2010 — requisitos de planta")
    _add(rows, "Producción", "Cemento asfáltico ≤ 175 °C", max_binder_temp <= 175.0, "Alta", f"{max_binder_temp:.1f} °C", "CR-2010 — control de temperatura de producción")
    _add(rows, "Producción", "Registros de producción y lotes", production_records, "Media", "Disponibles" if production_records else "Pendientes", "Control de calidad / expediente")

    st.markdown("### 3. Preparación, riegos y condiciones de colocación")
    c1, c2, c3 = st.columns(3)
    with c1:
        dry_day = st.checkbox("Colocación en día seco", key="cr2010_dry_day")
        air_temp = st.number_input("Temperatura del aire durante colocación (°C)", min_value=-10.0, max_value=60.0, value=20.0, step=0.5, key="cr2010_air_temp_place")
        surface_ready = st.checkbox("Superficie receptora limpia, preparada y aceptada", key="cr2010_surface_ready")
    with c2:
        prime_required = st.checkbox("El proyecto requiere riego de imprimación", key="cr2010_prime_required")
        prime_ok = st.checkbox("Riego de imprimación verificado", key="cr2010_prime_ok")
        tack_required = st.checkbox("El proyecto requiere riego de liga", value=True, key="cr2010_tack_required")
        tack_ok = st.checkbox("Riego de liga verificado", key="cr2010_tack_ok")
    with c3:
        paver_ok = st.checkbox("Pavimentadora/equipo de extendido verificado", key="cr2010_paver_ok")
        delivery_temp = st.number_input("Temperatura de mezcla a la llegada (°C)", min_value=0.0, max_value=250.0, value=145.0, step=1.0, key="cr2010_delivery_temp")
        delivery_temp_ok = st.checkbox("Temperatura de llegada cumple diseño/especificación", key="cr2010_delivery_temp_ok")

    _add(rows, "Colocación", "Día seco", dry_day, "Alta", "Seco" if dry_day else "No confirmado", "CR-2010 — condiciones de colocación")
    _add(rows, "Colocación", "Temperatura del aire > 2 °C", air_temp > 2.0, "Alta", f"{air_temp:.1f} °C", "CR-2010 — condiciones de colocación")
    _add(rows, "Preparación", "Superficie receptora preparada", surface_ready, "Alta", "Verificada" if surface_ready else "Pendiente", "CR-2010 Sección 405")
    _add(rows, "Riegos", "Riego de imprimación conforme", prime_ok if prime_required else None, "Alta", "Requerido" if prime_required else "No requerido", "CR-2010 Sección 413", na=not prime_required)
    _add(rows, "Riegos", "Riego de liga conforme", tack_ok if tack_required else None, "Alta", "Requerido" if tack_required else "No requerido", "CR-2010 — riego de liga / especificación aplicable", na=not tack_required)
    _add(rows, "Colocación", "Equipo de extendido verificado", paver_ok, "Media", "Verificado" if paver_ok else "Pendiente", "CR-2010 Sección 405")
    _add(rows, "Colocación", "Temperatura de llegada cumple especificación", delivery_temp_ok, "Alta", f"{delivery_temp:.1f} °C", project_spec_ref or "Diseño de mezcla / especificación particular")

    st.markdown("### 4. Compactación y control final")
    q1, q2, q3 = st.columns(3)
    with q1:
        compact_temp = st.number_input("Temperatura mínima registrada durante compactación (°C)", min_value=0.0, max_value=250.0, value=100.0, step=1.0, key="cr2010_compact_temp")
        project_min_compact = st.number_input("Mínimo exigido por el proyecto (°C, 0 = no definido)", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key="cr2010_project_min_compact")
        density_measured = st.checkbox("Densidad/compactación medida en campo", key="cr2010_density_measured")
        density_ok = st.checkbox("Densidad cumple especificación del proyecto", key="cr2010_density_ok")
    with q2:
        thickness_measured = st.checkbox("Espesor construido medido", key="cr2010_thickness_measured")
        thickness_ok = st.checkbox("Espesor cumple planos/especificación", key="cr2010_thickness_ok")
        iri_measured = st.checkbox("Regularidad/IRI documentada cuando corresponde", key="cr2010_iri_measured")
    with q3:
        asbuilt = st.checkbox("Planos conforme a obra actualizados", key="cr2010_asbuilt")
        qc_reports = st.checkbox("Informes y certificados de control de calidad archivados", key="cr2010_qc_reports")
        nonconformities_closed = st.checkbox("No conformidades cerradas o justificadas", key="cr2010_nonconformities_closed")

    temp_na = project_min_compact <= 0.0
    _add(rows, "Compactación", "Temperatura mínima cumple especificación particular", compact_temp >= project_min_compact if not temp_na else None, "Alta", f"Registrada {compact_temp:.1f} °C / mínima {project_min_compact:.1f} °C" if not temp_na else f"Registrada {compact_temp:.1f} °C; mínimo no definido", project_spec_ref or "Especificación particular / diseño de mezcla", na=temp_na)
    _add(rows, "Compactación", "Densidad medida en campo", density_measured, "Alta", "Medida" if density_measured else "Pendiente", "CR-2010 Sección 405 / control de calidad")
    _add(rows, "Compactación", "Densidad cumple especificación", density_ok if density_measured else None, "Alta", "Cumple" if density_ok else "Pendiente/no cumple", "Especificación particular / aceptación", na=not density_measured)
    _add(rows, "Recepción", "Espesor construido medido", thickness_measured, "Alta", "Medido" if thickness_measured else "Pendiente", "Planos y control de obra")
    _add(rows, "Recepción", "Espesor cumple planos/especificación", thickness_ok if thickness_measured else None, "Alta", "Cumple" if thickness_ok else "Pendiente/no cumple", "Planos y especificación particular", na=not thickness_measured)
    _add(rows, "Recepción", "Regularidad/IRI documentada", iri_measured, "Media", "Documentada" if iri_measured else "Pendiente", "CR-2010 / aceptación de pavimento")
    _add(rows, "Documentación", "Planos conforme a obra", asbuilt, "Media", "Actualizados" if asbuilt else "Pendientes", "Expediente de recepción")
    _add(rows, "Documentación", "Certificados e informes de calidad archivados", qc_reports, "Alta", "Archivados" if qc_reports else "Pendientes", "Expediente de recepción")
    _add(rows, "Cierre", "No conformidades cerradas o justificadas", nonconformities_closed, "Alta", "Cerradas" if nonconformities_closed else "Pendientes", "Control de calidad / aceptación")

    df = pd.DataFrame([asdict(r) for r in rows])
    applicable = df[df["estado"] != "No aplica"]
    completed = applicable[applicable["estado"].isin(["Cumple", "No cumple"])]
    compliant = int((applicable["estado"] == "Cumple").sum())
    failures = int((applicable["estado"] == "No cumple").sum())
    critical_failures = int(((applicable["estado"] == "No cumple") & (applicable["severidad"] == "Alta")).sum())
    total = len(applicable)
    pct = 100.0 * compliant / total if total else 0.0

    st.markdown("### Resultado del control")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Controles cumplidos", f"{compliant}/{total}")
    r2.metric("Cumplimiento", f"{pct:.0f}%")
    r3.metric("No conformidades", failures)
    r4.metric("Críticas", critical_failures)

    if critical_failures:
        st.error("Existen no conformidades de severidad alta. El proceso no debe considerarse cerrado hasta resolverlas o justificarlas formalmente.")
    elif failures:
        st.warning("Existen controles no conformes. Revise la evidencia antes del cierre del proceso.")
    elif len(completed) < total:
        st.info("No hay incumplimientos registrados, pero todavía existen controles pendientes.")
    else:
        st.success("Todos los controles aplicables registrados están marcados como cumplidos. Se mantiene requerida la revisión profesional y documental.")

    st.dataframe(df.rename(columns={
        "etapa": "Etapa", "control": "Control", "estado": "Estado", "severidad": "Severidad",
        "evidencia": "Evidencia", "referencia": "Referencia"
    }), use_container_width=True, hide_index=True)

    st.download_button(
        "Descargar checklist CR-2010 (CSV)",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="checklist_asfalto_cr2010.csv",
        mime="text/csv",
        key="download_cr2010_asphalt_checklist",
    )

    result = {
        "project": project_name,
        "design_method": design_method,
        "project_binder": project_binder,
        "project_spec_reference": project_spec_ref,
        "rap_pct": float(rap_pct),
        "max_binder_temp_c": float(max_binder_temp),
        "air_temp_placement_c": float(air_temp),
        "delivery_temp_c": float(delivery_temp),
        "compaction_temp_c": float(compact_temp),
        "project_min_compaction_temp_c": float(project_min_compact),
        "compliant": compliant,
        "total_applicable": total,
        "compliance_pct": pct,
        "nonconformities": failures,
        "critical_nonconformities": critical_failures,
        "checks": df.to_dict(orient="records"),
    }
    st.session_state["asphalt_cr2010_checklist"] = result
    return result
