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
    """Checklist trazable para mezcla asfáltica basado en CR-2010 actualizado."""
    st.subheader("Control CR-2010 — Mezcla asfáltica")
    st.caption(
        "Control de apoyo para diseño, materiales, transporte, colocación, compactación y recepción. "
        "No sustituye la inspección, ensayos, fórmula de trabajo, tramo de prueba ni aceptación de la Administración."
    )
    st.info(
        "Referencias incorporadas: CR-2010 actualizado — Sección 401 (Marshall), 402 (Superpave), "
        "405 (suministro y colocación de mezcla asfáltica en caliente), 413 (riego de imprimación), "
        "414 (riego de liga), 702.01/702.02 (ligantes) y 703.07 (agregados para mezcla asfáltica)."
    )

    rows: list[AsphaltCheck] = []

    st.markdown("### 1. Diseño, materiales y trazabilidad")
    d1, d2, d3 = st.columns(3)
    with d1:
        design_method = st.selectbox(
            "Método de diseño de mezcla",
            ["Marshall — Sección 401", "Superpave — Sección 402", "Especial — Sección 403", "Reciclada RAP — Sección 404"],
            key="cr2010_mix_method",
        )
        mix_design_approved = st.checkbox("Diseño de mezcla / fórmula de trabajo aprobada", key="cr2010_mix_design_approved")
        trial_section = st.checkbox("Tramo de prueba ejecutado y documentado cuando corresponde", key="cr2010_trial_section")
    with d2:
        binder_cert = st.checkbox("Certificado del cemento asfáltico disponible", key="cr2010_binder_cert")
        aggregate_cert = st.checkbox("Certificados/ensayos de agregados disponibles", key="cr2010_aggregate_cert")
        qc_lab = st.checkbox("Laboratorio de control/verificación identificado", key="cr2010_qc_lab")
    with d3:
        project_binder = st.text_input("Ligante especificado por el proyecto", value="", placeholder="Ej.: AC-30", key="cr2010_project_binder")
        binder_matches = st.checkbox("El certificado coincide con el ligante especificado", key="cr2010_binder_matches")
        project_spec_ref = st.text_input("Referencia particular", value="", placeholder="Ej.: IG-013-21 §10.6 p.74", key="cr2010_project_spec_ref")

    _add(rows, "Diseño", "Método de diseño identificado", bool(design_method), "Alta", design_method, "CR-2010 Secciones 401-404")
    _add(rows, "Diseño", "Fórmula de trabajo/diseño aprobado", mix_design_approved, "Alta", "Aprobado" if mix_design_approved else "Pendiente", "CR-2010 Sección 405.03")
    _add(rows, "Diseño", "Tramo de prueba documentado", trial_section, "Alta", "Documentado" if trial_section else "Pendiente", "CR-2010 405.03.06 / 405.06")
    _add(rows, "Materiales", "Certificado del cemento asfáltico", binder_cert, "Alta", project_binder or "Ligante no indicado", "CR-2010 702.01/702.02 y 107.03")
    _add(rows, "Materiales", "Certificados/ensayos de agregados", aggregate_cert, "Alta", "Documentados" if aggregate_cert else "Pendientes", "CR-2010 703.07 y 107")
    _add(rows, "Calidad", "Laboratorio de control/verificación identificado", qc_lab, "Alta", "Identificado" if qc_lab else "Pendiente", "CR-2010 107 y 405.09")
    _add(rows, "Materiales", "Ligante certificado coincide con la especificación particular", binder_matches if project_binder else None, "Alta", project_binder or "No definido", project_spec_ref or "Contrato/diseño de mezcla", na=not bool(project_binder))

    st.markdown("### 2. Transporte y preparación para colocación")
    t1, t2, t3 = st.columns(3)
    with t1:
        truck_cover = st.checkbox("Vagonetas protegidas con manteado/lona", key="cr2010_truck_cover")
        load_temp_monitored = st.checkbox("Temperatura de cada carga monitoreada", key="cr2010_load_temp_monitored")
        weight_time_log = st.checkbox("Registro de peso bruto, tara, peso neto y hora", key="cr2010_weight_time_log")
    with t2:
        surface_ready = st.checkbox("Capas subyacentes preparadas y aceptadas", key="cr2010_surface_ready")
        weather_suitable = st.checkbox("Condiciones climáticas aptas; sin efectos de lluvia", key="cr2010_weather_suitable")
        prime_required = st.checkbox("Requiere riego de imprimación", key="cr2010_prime_required")
        prime_ok = st.checkbox("Imprimación conforme", key="cr2010_prime_ok")
    with t3:
        tack_required = st.checkbox("Requiere riego de liga", value=True, key="cr2010_tack_required")
        tack_ok = st.checkbox("Riego de liga conforme", key="cr2010_tack_ok")
        delivery_temp = st.number_input("Temperatura justo antes de descarga (°C)", min_value=0.0, max_value=250.0, value=145.0, step=1.0, key="cr2010_delivery_temp")
        formula_temp_ok = st.checkbox("Temperatura de entrega cumple la fórmula de trabajo", key="cr2010_formula_temp_ok")

    _add(rows, "Transporte", "Carga protegida del intemperismo", truck_cover, "Media", "Protegida" if truck_cover else "Pendiente", "CR-2010 405.05.01")
    _add(rows, "Transporte", "Temperatura de cada carga monitoreada", load_temp_monitored, "Alta", "Monitoreada" if load_temp_monitored else "Pendiente", "CR-2010 405.05.01")
    _add(rows, "Transporte", "Peso y hora de carga registrados", weight_time_log, "Media", "Registrados" if weight_time_log else "Pendientes", "CR-2010 405.05.01")
    _add(rows, "Preparación", "Capas subyacentes preparadas", surface_ready, "Alta", "Preparadas" if surface_ready else "Pendiente", "CR-2010 405.05.02")
    _add(rows, "Colocación", "Condiciones climáticas aptas", weather_suitable, "Alta", "Aptas" if weather_suitable else "No confirmadas", "CR-2010 405.05.02(a)")
    _add(rows, "Riegos", "Imprimación conforme", prime_ok if prime_required else None, "Alta", "Requerida" if prime_required else "No requerida", "CR-2010 Sección 413", na=not prime_required)
    _add(rows, "Riegos", "Riego de liga conforme", tack_ok if tack_required else None, "Alta", "Requerido" if tack_required else "No requerido", "CR-2010 Sección 414", na=not tack_required)
    _add(rows, "Colocación", "Temperatura de entrega según fórmula de trabajo", formula_temp_ok, "Alta", f"{delivery_temp:.1f} °C", "CR-2010 405.05.01 / 405.05.02")

    st.markdown("### 3. Temperaturas y proceso de compactación")
    c1, c2, c3 = st.columns(3)
    with c1:
        modified_mix = st.checkbox("Mezcla con ligante modificado", key="cr2010_modified_mix")
        start_compaction_temp = st.number_input("Temperatura al iniciar compactación (°C)", min_value=0.0, max_value=250.0, value=135.0, step=1.0, key="cr2010_start_compaction_temp")
        provider_compaction_temp = st.number_input("Temperatura de compactación definida por proveedor (°C)", min_value=0.0, max_value=250.0, value=140.0, step=1.0, key="cr2010_provider_compaction_temp")
    with c2:
        end_compaction_temp = st.number_input("Temperatura al completar compactación (°C)", min_value=0.0, max_value=250.0, value=90.0, step=1.0, key="cr2010_end_compaction_temp")
        initial_static = st.checkbox("Compactación inicial: rodillo metálico sin vibración", key="cr2010_initial_static")
        intermediate_vibration = st.checkbox("Compactación intermedia: rodillo metálico con vibración", key="cr2010_intermediate_vibration")
    with c3:
        final_pneumatic = st.checkbox("Compactación final: rodillo neumático", key="cr2010_final_pneumatic")
        pneumatic_weight = st.number_input("Peso rodillo neumático (t)", min_value=0.0, max_value=50.0, value=12.0, step=0.5, key="cr2010_pneumatic_weight")
        low_thickness = st.checkbox("Espesor de capa menor de 40 mm", key="cr2010_low_thickness")
        vibration_used_low = st.checkbox("Se usó vibración en capa < 40 mm", key="cr2010_vibration_used_low")

    if modified_mix:
        start_temp_ok = trial_section and formula_temp_ok
        start_evidence = f"{start_compaction_temp:.1f} °C; verificar tramo de prueba aprobado"
        start_ref = "CR-2010 405.05.02(d): mezcla modificada según tramo de prueba"
    else:
        min_start = max(125.0, provider_compaction_temp - 5.0)
        start_temp_ok = start_compaction_temp >= min_start
        start_evidence = f"{start_compaction_temp:.1f} °C; mínimo calculado {min_start:.1f} °C"
        start_ref = "CR-2010 405.05.02(d)"

    _add(rows, "Compactación", "Temperatura de inicio de compactación", start_temp_ok, "Alta", start_evidence, start_ref)
    _add(rows, "Compactación", "Compactación completada antes de alcanzar 85 °C", end_compaction_temp > 85.0, "Alta", f"Final registrada {end_compaction_temp:.1f} °C", "CR-2010 405.06(l)")
    _add(rows, "Compactación", "Rodillo inicial metálico sin vibración", initial_static, "Alta", "Verificado" if initial_static else "Pendiente", "CR-2010 405.06(a)")
    _add(rows, "Compactación", "Rodillo intermedio metálico con vibración", intermediate_vibration if not low_thickness else None, "Media", "Verificado" if intermediate_vibration else "Pendiente", "CR-2010 405.06(b),(j)", na=low_thickness)
    _add(rows, "Compactación", "Rodillo final neumático", final_pneumatic, "Alta", f"{pneumatic_weight:.1f} t", "CR-2010 405.06(c)")
    _add(rows, "Compactación", "Rodillo neumático ≥ 12 t", pneumatic_weight >= 12.0 if final_pneumatic else None, "Alta", f"{pneumatic_weight:.1f} t", "CR-2010 405.06(c)", na=not final_pneumatic)
    _add(rows, "Compactación", "Sin vibración cuando espesor < 40 mm", not vibration_used_low if low_thickness else None, "Alta", "Vibración usada" if vibration_used_low else "Sin vibración", "CR-2010 405.06(j)", na=not low_thickness)

    st.markdown("### 4. Densidad, vacíos, espesor y apertura al tránsito")
    q1, q2, q3 = st.columns(3)
    with q1:
        density_pct = st.number_input("Densidad en sitio (% de máxima teórica)", min_value=0.0, max_value=110.0, value=93.0, step=0.1, key="cr2010_density_pct")
        air_voids_pct = st.number_input("Vacíos de aire de mezcla compactada (%)", min_value=0.0, max_value=30.0, value=8.0, step=0.1, key="cr2010_air_voids_pct")
        ogfc = st.checkbox("Mezcla tipo OGFC", key="cr2010_ogfc")
    with q2:
        layer_thickness_mm = st.number_input("Espesor colocado (mm)", min_value=0.0, max_value=500.0, value=50.0, step=1.0, key="cr2010_layer_thickness_mm")
        nmas_mm = st.number_input("Tamaño máximo nominal del agregado, NMAS (mm)", min_value=0.1, max_value=100.0, value=12.5, step=0.5, key="cr2010_nmas_mm")
        opening_temp = st.number_input("Temperatura al abrir al tránsito (°C)", min_value=0.0, max_value=150.0, value=65.0, step=1.0, key="cr2010_opening_temp")
    with q3:
        cores_taken = st.checkbox("Núcleos / ensayos de compactación documentados", key="cr2010_cores_taken")
        thickness_verified = st.checkbox("Espesor verificado en obra", key="cr2010_thickness_verified")
        qc_reports = st.checkbox("Informes de control de calidad archivados", key="cr2010_qc_reports")

    void_target = 16.0 if ogfc else 8.0
    _add(rows, "Compactación", "Densidad en sitio entre 92% y 94%", 92.0 <= density_pct <= 94.0, "Alta", f"{density_pct:.1f}%", "CR-2010 405.06.01(a)")
    _add(rows, "Compactación", f"Vacíos de aire {void_target:.0f}±1%", (void_target - 1.0) <= air_voids_pct <= (void_target + 1.0), "Alta", f"{air_voids_pct:.1f}%", "CR-2010 405.06.01(e)")
    _add(rows, "Espesor", "Espesor colocado ≥ 3 × NMAS", layer_thickness_mm >= 3.0 * nmas_mm, "Alta", f"{layer_thickness_mm:.1f} mm / mínimo {3*nmas_mm:.1f} mm", "CR-2010 405.06(i)")
    _add(rows, "Tránsito", "Apertura recomendada con mezcla ≤ 70 °C", opening_temp <= 70.0, "Media", f"{opening_temp:.1f} °C", "CR-2010 405.06.01; recomendación de apertura")
    _add(rows, "Calidad", "Núcleos/ensayos de compactación documentados", cores_taken, "Alta", "Documentados" if cores_taken else "Pendientes", "CR-2010 405.06.01 / 405.09")
    _add(rows, "Calidad", "Espesor verificado", thickness_verified, "Alta", "Verificado" if thickness_verified else "Pendiente", "CR-2010 Sección 405 / planos")
    _add(rows, "Documentación", "Informes de control de calidad archivados", qc_reports, "Alta", "Archivados" if qc_reports else "Pendientes", "CR-2010 405.13 y 107")

    st.markdown("### 5. Regularidad superficial y cierre")
    r1, r2, r3 = st.columns(3)
    with r1:
        iri_applicable = st.checkbox("Aplica control de regularidad/IRI", value=True, key="cr2010_iri_applicable")
        road_class = st.selectbox("Clasificación para IRI", ["Otras vías", "Autopista (TPDA > 5000)"], key="cr2010_iri_road_class")
    with r2:
        max_moving_mri = st.number_input("Máxima media móvil MRI (m/km)", min_value=0.0, max_value=10.0, value=2.0, step=0.05, key="cr2010_mri_moving")
        max_individual_mri = st.number_input("Máximo valor individual MRI (m/km)", min_value=0.0, max_value=10.0, value=2.5, step=0.05, key="cr2010_mri_individual")
    with r3:
        asbuilt = st.checkbox("Planos conforme a obra actualizados", key="cr2010_asbuilt")
        nonconformities_closed = st.checkbox("No conformidades cerradas o justificadas", key="cr2010_nonconformities_closed")

    moving_limit = 2.0 if road_class.startswith("Autopista") else 2.5
    _add(rows, "Regularidad", f"Media móvil MRI < {moving_limit:.1f} m/km", max_moving_mri < moving_limit if iri_applicable else None, "Media", f"{max_moving_mri:.2f} m/km", "CR-2010 Tabla 405-1", na=not iri_applicable)
    _add(rows, "Regularidad", "Ningún valor individual MRI > 3,0 m/km", max_individual_mri <= 3.0 if iri_applicable else None, "Alta", f"{max_individual_mri:.2f} m/km", "CR-2010 405.07.02", na=not iri_applicable)
    _add(rows, "Documentación", "Planos conforme a obra actualizados", asbuilt, "Media", "Actualizados" if asbuilt else "Pendientes", "Expediente de recepción")
    _add(rows, "Cierre", "No conformidades cerradas o justificadas", nonconformities_closed, "Alta", "Cerradas" if nonconformities_closed else "Pendientes", "CR-2010 107 / control de calidad")

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
        st.error("Existen no conformidades de severidad alta. El proceso no debe considerarse cerrado hasta resolverlas o justificarlas formalmente.")
    elif failures:
        st.warning("Existen controles no conformes. Revise la evidencia antes del cierre del proceso.")
    elif len(completed) < total:
        st.info("No hay incumplimientos registrados, pero todavía existen controles pendientes.")
    else:
        st.success("Todos los controles aplicables registrados están marcados como cumplidos; aún se requiere revisión profesional y documental.")

    display_df = df.rename(columns={
        "etapa": "Etapa", "control": "Control", "estado": "Estado", "severidad": "Severidad",
        "evidencia": "Evidencia", "referencia": "Referencia"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Descargar checklist CR-2010 (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
        file_name="checklist_asfalto_cr2010.csv", mime="text/csv", key="download_cr2010_asphalt_checklist"
    )

    result = {
        "project": project_name,
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
    st.session_state["asphalt_cr2010_checklist"] = result
    return result
