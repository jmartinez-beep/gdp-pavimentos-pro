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
    origen: str


def _state(ok: bool | None, na: bool = False) -> str:
    if na:
        return "No aplica"
    if ok is None:
        return "Pendiente"
    return "Cumple" if ok else "No cumple"


def _add(rows: list[AsphaltCheck], etapa: str, control: str, ok: bool | None,
         severidad: str, evidencia: str, referencia: str, origen: str = "CR-2020",
         na: bool = False) -> None:
    rows.append(AsphaltCheck(etapa, control, _state(ok, na), severidad, evidencia, referencia, origen))


def render_asphalt_cr2020_checklist(project_name: str = "") -> dict[str, Any]:
    """Checklist constructivo trazable con CR-2020 como referencia normativa vigente."""
    st.subheader("Control constructivo — CR-2020")
    st.caption(
        "Control de apoyo para diseño de mezcla, materiales, producción, transporte, colocación, "
        "compactación, aceptación y trazabilidad. No sustituye la inspección, los ensayos, la fórmula "
        "de trabajo, el tramo de prueba ni las especificaciones particulares del contrato."
    )

    norm_mode = st.selectbox(
        "Normativa contractual de referencia",
        ["CR-2020 — vigente", "CR-2010 — proyecto transitorio/preexistente"],
        key="cr2020_norm_mode",
        help="CR-2020 se usa por defecto. Mantenga CR-2010 únicamente cuando el expediente contractual aplicable así lo requiera.",
    )
    norm = "CR-2020" if norm_mode.startswith("CR-2020") else "CR-2010"
    if norm == "CR-2020":
        st.info(
            "CR-2020 fue oficializado mediante Decreto Ejecutivo 43397-MOPT y actualiza el CR-2010. "
            "En CR-2020 las mezclas asfálticas se organizan en las secciones 401 a 405; los riegos de "
            "emulsión asfáltica se concentran en la Sección 414 y la Sección 413 queda reservada."
        )
    else:
        st.warning(
            "Modo transitorio CR-2010. Verifique que el cartel, contrato u orden de servicio justifique "
            "mantener la edición anterior y documente esa decisión en el expediente."
        )

    rows: list[AsphaltCheck] = []
    norm_origin = norm

    st.markdown("### 1. Diseño, materiales y trazabilidad")
    d1, d2, d3 = st.columns(3)
    with d1:
        design_method = st.selectbox(
            "Método de diseño de mezcla",
            ["Marshall — Sección 401", "Superpave — Sección 402", "Especial — Sección 403", "Reciclada RAP — Sección 404"],
            key="cr2020_mix_method",
        )
        mix_design_approved = st.checkbox("Diseño de mezcla / fórmula de trabajo aprobada", key="cr2020_mix_design_approved")
        trial_section = st.checkbox("Tramo de prueba ejecutado y documentado cuando corresponde", key="cr2020_trial_section")
    with d2:
        binder_cert = st.checkbox("Certificado del ligante disponible", key="cr2020_binder_cert")
        aggregate_cert = st.checkbox("Certificados/ensayos de agregados disponibles", key="cr2020_aggregate_cert")
        qc_lab = st.checkbox("Laboratorio de control/verificación identificado", key="cr2020_qc_lab")
    with d3:
        project_binder = st.text_input("Ligante especificado por el proyecto", value="", placeholder="Ej.: AC-30", key="cr2020_project_binder")
        binder_matches = st.checkbox("El certificado coincide con el ligante especificado", key="cr2020_binder_matches")
        project_spec_ref = st.text_input("Referencia particular del proyecto", value="", placeholder="Ej.: IG-013-21 §10.6 p.74", key="cr2020_project_spec_ref")

    _add(rows, "Diseño", "Método de diseño identificado", bool(design_method), "Alta", design_method, f"{norm} Secciones 401-404", norm_origin)
    _add(rows, "Diseño", "Fórmula de trabajo/diseño aprobado", mix_design_approved, "Alta", "Aprobado" if mix_design_approved else "Pendiente", f"{norm} Sección 405", norm_origin)
    _add(rows, "Diseño", "Tramo de prueba documentado cuando corresponde", trial_section, "Alta", "Documentado" if trial_section else "Pendiente", f"{norm} Sección 405 / fórmula de trabajo", norm_origin)
    _add(rows, "Materiales", "Certificado del ligante", binder_cert, "Alta", project_binder or "Ligante no indicado", f"{norm} División 700 / expediente de calidad", norm_origin)
    _add(rows, "Materiales", "Certificados/ensayos de agregados", aggregate_cert, "Alta", "Documentados" if aggregate_cert else "Pendientes", f"{norm} División 700 / expediente de calidad", norm_origin)
    _add(rows, "Calidad", "Laboratorio de control/verificación identificado", qc_lab, "Alta", "Identificado" if qc_lab else "Pendiente", f"{norm} control de calidad", norm_origin)
    _add(rows, "Materiales", "Ligante certificado coincide con la especificación particular", binder_matches if project_binder else None, "Alta", project_binder or "No definido", project_spec_ref or "Contrato/diseño de mezcla", "Especificación particular", na=not bool(project_binder))

    st.markdown("### 2. Transporte, superficie y riegos")
    t1, t2, t3 = st.columns(3)
    with t1:
        truck_cover = st.checkbox("Vagonetas protegidas con lona/manteado", key="cr2020_truck_cover")
        load_temp_monitored = st.checkbox("Temperatura de cada carga monitoreada", key="cr2020_load_temp_monitored")
        weight_time_log = st.checkbox("Registro de peso y hora de despacho", key="cr2020_weight_time_log")
    with t2:
        surface_ready = st.checkbox("Capas subyacentes preparadas y aceptadas", key="cr2020_surface_ready")
        weather_suitable = st.checkbox("Condiciones climáticas aptas; sin efectos de lluvia", key="cr2020_weather_suitable")
        prime_required = st.checkbox("Requiere riego de imprimación", key="cr2020_prime_required")
        prime_ok = st.checkbox("Imprimación conforme", key="cr2020_prime_ok")
    with t3:
        tack_required = st.checkbox("Requiere riego de liga/adherencia", value=True, key="cr2020_tack_required")
        tack_ok = st.checkbox("Riego de liga/adherencia conforme", key="cr2020_tack_ok")
        delivery_temp = st.number_input("Temperatura justo antes de descarga (°C)", min_value=0.0, max_value=250.0, value=145.0, step=1.0, key="cr2020_delivery_temp")
        formula_temp_ok = st.checkbox("Temperatura de entrega cumple la fórmula de trabajo", key="cr2020_formula_temp_ok")

    _add(rows, "Transporte", "Carga protegida del intemperismo", truck_cover, "Media", "Protegida" if truck_cover else "Pendiente", f"{norm} Sección 405", norm_origin)
    _add(rows, "Transporte", "Temperatura de cada carga monitoreada", load_temp_monitored, "Alta", "Monitoreada" if load_temp_monitored else "Pendiente", f"{norm} Sección 405", norm_origin)
    _add(rows, "Transporte", "Peso y hora registrados", weight_time_log, "Media", "Registrados" if weight_time_log else "Pendientes", f"{norm} Sección 405 / control de producción", norm_origin)
    _add(rows, "Preparación", "Capas subyacentes preparadas", surface_ready, "Alta", "Preparadas" if surface_ready else "Pendiente", f"{norm} Sección 405", norm_origin)
    _add(rows, "Colocación", "Condiciones climáticas aptas", weather_suitable, "Alta", "Aptas" if weather_suitable else "No confirmadas", f"{norm} Sección 405", norm_origin)
    riego_ref = "CR-2020 Sección 414 — Riegos de emulsión asfáltica" if norm == "CR-2020" else "CR-2010 — riegos según edición contractual"
    _add(rows, "Riegos", "Riego de imprimación conforme", prime_ok if prime_required else None, "Alta", "Requerido" if prime_required else "No requerido", riego_ref, norm_origin, na=not prime_required)
    _add(rows, "Riegos", "Riego de liga/adherencia conforme", tack_ok if tack_required else None, "Alta", "Requerido" if tack_required else "No requerido", riego_ref, norm_origin, na=not tack_required)
    _add(rows, "Colocación", "Temperatura de entrega según fórmula de trabajo", formula_temp_ok, "Alta", f"{delivery_temp:.1f} °C", f"{norm} Sección 405 + fórmula de trabajo", "CR-2020" if norm == "CR-2020" else "CR-2010")

    st.markdown("### 3. Compactación — criterio normativo y especificación particular")
    c1, c2, c3 = st.columns(3)
    with c1:
        modified_mix = st.checkbox("Mezcla con ligante modificado", key="cr2020_modified_mix")
        start_compaction_temp = st.number_input("Temperatura al iniciar compactación (°C)", min_value=0.0, max_value=250.0, value=135.0, step=1.0, key="cr2020_start_compaction_temp")
        provider_compaction_temp = st.number_input("Temperatura de compactación indicada por proveedor/fórmula (°C)", min_value=0.0, max_value=250.0, value=140.0, step=1.0, key="cr2020_provider_compaction_temp")
    with c2:
        end_compaction_temp = st.number_input("Temperatura al completar compactación (°C)", min_value=0.0, max_value=250.0, value=90.0, step=1.0, key="cr2020_end_compaction_temp")
        project_min_temp = st.number_input("Mínimo particular del proyecto (°C, 0 = no definido)", min_value=0.0, max_value=200.0, value=0.0, step=1.0, key="cr2020_project_min_temp")
        initial_static = st.checkbox("Patrón/equipo de compactación aprobado", key="cr2020_compaction_pattern")
    with c3:
        final_pneumatic = st.checkbox("Rodillo neumático incluido cuando corresponde", key="cr2020_final_pneumatic")
        low_thickness = st.checkbox("Capa delgada / condición especial documentada", key="cr2020_low_thickness")
        special_compaction_ok = st.checkbox("Restricciones especiales de vibración/equipo verificadas", key="cr2020_special_compaction_ok")

    # Para evitar trasladar límites del CR-2010 sin respaldo, CR-2020 usa la fórmula de trabajo
    # y el tramo de prueba como autoridad operativa para temperaturas y patrón de compactación.
    if norm == "CR-2020":
        start_temp_ok = formula_temp_ok and (trial_section or not modified_mix)
        start_ref = "CR-2020 Sección 405 + fórmula de trabajo/tramo de prueba"
    else:
        min_start = max(125.0, provider_compaction_temp - 5.0)
        start_temp_ok = start_compaction_temp >= min_start if not modified_mix else trial_section and formula_temp_ok
        start_ref = "CR-2010 criterio contractual heredado; confirmar edición aplicable"
    _add(rows, "Compactación", "Temperatura de inicio conforme a fórmula/tramo de prueba", start_temp_ok, "Alta", f"{start_compaction_temp:.1f} °C", start_ref, norm_origin)
    _add(rows, "Compactación", "Temperatura final registrada y trazable", True if end_compaction_temp > 0 else None, "Media", f"{end_compaction_temp:.1f} °C", f"{norm} Sección 405 / registro de obra", norm_origin)
    _add(rows, "Compactación", "Patrón y equipo de compactación aprobados", initial_static, "Alta", "Verificado" if initial_static else "Pendiente", f"{norm} Sección 405 / tramo de prueba", norm_origin)
    _add(rows, "Compactación", "Rodillo neumático verificado cuando corresponde", final_pneumatic, "Media", "Verificado" if final_pneumatic else "Pendiente", f"{norm} Sección 405 / patrón aprobado", norm_origin, na=not final_pneumatic and low_thickness)
    _add(rows, "Compactación", "Restricciones especiales de vibración/equipo verificadas", special_compaction_ok if low_thickness else None, "Alta", "Condición especial" if low_thickness else "No aplica", f"{norm} Sección 405 / fórmula de trabajo", norm_origin, na=not low_thickness)
    particular_na = project_min_temp <= 0
    _add(rows, "Compactación", "Temperatura mínima particular del proyecto", start_compaction_temp >= project_min_temp if not particular_na else None, "Alta", f"Inicio {start_compaction_temp:.1f} °C / mínimo particular {project_min_temp:.1f} °C" if not particular_na else "No definida", project_spec_ref or "Especificación particular", "Especificación particular", na=particular_na)

    st.markdown("### 4. Densidad, vacíos, espesor y apertura")
    q1, q2, q3 = st.columns(3)
    with q1:
        density_pct = st.number_input("Densidad en sitio (% de máxima teórica)", min_value=0.0, max_value=110.0, value=93.0, step=0.1, key="cr2020_density_pct")
        air_voids_pct = st.number_input("Vacíos de aire de mezcla compactada (%)", min_value=0.0, max_value=30.0, value=8.0, step=0.1, key="cr2020_air_voids_pct")
        density_formula_ok = st.checkbox("Densidad y vacíos cumplen fórmula/especificación aplicable", key="cr2020_density_formula_ok")
    with q2:
        layer_thickness_mm = st.number_input("Espesor colocado (mm)", min_value=0.0, max_value=500.0, value=50.0, step=1.0, key="cr2020_layer_thickness_mm")
        nmas_mm = st.number_input("NMAS (mm)", min_value=0.1, max_value=100.0, value=12.5, step=0.5, key="cr2020_nmas_mm")
        thickness_formula_ok = st.checkbox("Espesor cumple diseño/fórmula de trabajo", key="cr2020_thickness_formula_ok")
    with q3:
        opening_temp = st.number_input("Temperatura al abrir al tránsito (°C)", min_value=0.0, max_value=150.0, value=65.0, step=1.0, key="cr2020_opening_temp")
        opening_ok = st.checkbox("Apertura al tránsito autorizada según especificación/Administración", key="cr2020_opening_ok")
        qc_reports = st.checkbox("Núcleos/ensayos e informes de calidad archivados", key="cr2020_qc_reports")

    _add(rows, "Compactación", "Densidad y vacíos cumplen criterio aplicable", density_formula_ok, "Alta", f"Densidad {density_pct:.1f}% · Vacíos {air_voids_pct:.1f}%", f"{norm} Sección 405 + fórmula de trabajo", norm_origin)
    _add(rows, "Espesor", "Espesor cumple diseño y criterio de mezcla", thickness_formula_ok, "Alta", f"{layer_thickness_mm:.1f} mm · NMAS {nmas_mm:.1f} mm", f"{norm} Sección 405 + planos/fórmula", norm_origin)
    _add(rows, "Tránsito", "Apertura al tránsito autorizada", opening_ok, "Alta", f"{opening_temp:.1f} °C", f"{norm} Sección 405 + instrucción de la Administración", norm_origin)
    _add(rows, "Calidad", "Ensayos e informes de calidad archivados", qc_reports, "Alta", "Archivados" if qc_reports else "Pendientes", f"{norm} control de calidad / expediente", norm_origin)

    st.markdown("### 5. Regularidad superficial y cierre")
    r1, r2, r3 = st.columns(3)
    with r1:
        iri_applicable = st.checkbox("Aplica control de regularidad/IRI", value=True, key="cr2020_iri_applicable")
        iri_spec_ok = st.checkbox("IRI/MRI cumple la Tabla 405-1 o especificación contractual aplicable", key="cr2020_iri_spec_ok")
    with r2:
        max_moving_mri = st.number_input("Máxima media móvil MRI (m/km)", min_value=0.0, max_value=10.0, value=2.0, step=0.05, key="cr2020_mri_moving")
        max_individual_mri = st.number_input("Máximo valor individual MRI (m/km)", min_value=0.0, max_value=10.0, value=2.5, step=0.05, key="cr2020_mri_individual")
    with r3:
        asbuilt = st.checkbox("Planos conforme a obra actualizados", key="cr2020_asbuilt")
        nonconformities_closed = st.checkbox("No conformidades cerradas o justificadas", key="cr2020_nonconformities_closed")

    _add(rows, "Regularidad", "IRI/MRI cumple criterio contractual", iri_spec_ok if iri_applicable else None, "Alta", f"Media móvil {max_moving_mri:.2f} · individual {max_individual_mri:.2f} m/km", f"{norm} Sección 405.07 / Tabla 405-1", norm_origin, na=not iri_applicable)
    _add(rows, "Documentación", "Planos conforme a obra actualizados", asbuilt, "Media", "Actualizados" if asbuilt else "Pendientes", "Expediente de recepción", "Documento del proyecto")
    _add(rows, "Cierre", "No conformidades cerradas o justificadas", nonconformities_closed, "Alta", "Cerradas" if nonconformities_closed else "Pendientes", "Plan de control de calidad / expediente", "Documento del proyecto")

    df = pd.DataFrame([asdict(r) for r in rows])
    applicable = df[df["estado"] != "No aplica"]
    completed = applicable[applicable["estado"].isin(["Cumple", "No cumple"])]
    compliant = int((applicable["estado"] == "Cumple").sum())
    failures = int((applicable["estado"] == "No cumple").sum())
    critical_failures = int(((applicable["estado"] == "No cumple") & (applicable["severidad"] == "Alta")).sum())
    total = len(applicable)
    pct = 100.0 * compliant / total if total else 0.0

    st.markdown("### Resultado del control")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Controles cumplidos", f"{compliant}/{total}")
    k2.metric("Cumplimiento", f"{pct:.0f}%")
    k3.metric("No conformidades", failures)
    k4.metric("Críticas", critical_failures)

    if critical_failures:
        st.error("Existen no conformidades de severidad alta. No cierre el control hasta resolverlas o justificarlas formalmente.")
    elif failures:
        st.warning("Existen controles no conformes. Revise la evidencia antes del cierre.")
    elif len(completed) < total:
        st.info("No hay incumplimientos registrados, pero todavía existen controles pendientes.")
    else:
        st.success("Todos los controles aplicables registrados están cumplidos; se mantiene requerida la revisión profesional y documental.")

    display_df = df.rename(columns={
        "etapa": "Etapa", "control": "Control", "estado": "Estado", "severidad": "Severidad",
        "evidencia": "Evidencia", "referencia": "Referencia", "origen": "Origen del criterio"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.session_state.pop("download_cr2020_asphalt_checklist", None)
    st.download_button(
        "Descargar checklist constructivo (CSV)",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="checklist_asfalto_cr2020.csv" if norm == "CR-2020" else "checklist_asfalto_cr2010_transitorio.csv",
        mime="text/csv", key="download_cr2020_asphalt_checklist"
    )

    result = {
        "project": project_name,
        "normative_version": norm,
        "decree": "43397-MOPT" if norm == "CR-2020" else "36388-MOPT / verificar contrato",
        "design_method": design_method,
        "project_binder": project_binder,
        "project_spec_reference": project_spec_ref,
        "modified_mix": bool(modified_mix),
        "delivery_temp_c": float(delivery_temp),
        "start_compaction_temp_c": float(start_compaction_temp),
        "end_compaction_temp_c": float(end_compaction_temp),
        "density_pct": float(density_pct),
        "air_voids_pct": float(air_voids_pct),
        "layer_thickness_mm": float(layer_thickness_mm),
        "nmas_mm": float(nmas_mm),
        "opening_temp_c": float(opening_temp),
        "compliant": compliant,
        "total_applicable": total,
        "compliance_pct": pct,
        "nonconformities": failures,
        "critical_nonconformities": critical_failures,
        "checks": df.to_dict(orient="records"),
    }
    st.session_state["asphalt_cr2020_checklist"] = result
    # Compatibilidad con proyectos guardados y versiones anteriores de la aplicación.
    st.session_state["asphalt_cr2010_checklist"] = result
    return result
