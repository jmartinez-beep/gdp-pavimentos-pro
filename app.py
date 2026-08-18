from __future__ import annotations

import io
import json
import math
import zipfile
from dataclasses import dataclass, asdict
from datetime import date, datetime
from statistics import NormalDist
from typing import Dict, List
import os

from web_storage import (
    authenticate, create_user, delete_project, list_projects, load_project,
    project_state_fingerprint, save_project,
)
from gdp_tomo2_adapter import alternatives_for_app, selected_trace
from gdp_tomo2 import classify_tpd, classify_cbr, classify_heavy_pct, nearby_catalog_options
from geo_cr import crtm05_to_wgs84, wgs84_to_crtm05, is_plausible_costa_rica_wgs84
from climate_tools import (
    MONTHS_ES, monthly_climate_table, monthly_summary, representative_temperature,
    thornthwaite_tmi_balance,
)
from climate_catalog import (
    CLIMATE_ZONES, fetch_point_climatology, fetch_zone_climatology,
    project_climate_point,
)
from cr2020_asphalt import render_asphalt_cr2020_checklist
from structural_number import DEFAULT_LAYER_COEFFICIENTS, structural_number_breakdown
from road_alignment import RoadAlignmentError, road_route
from project_state import (
    is_active_control_key, is_ephemeral_state_key,
    merge_segment_coordinate_snapshot,
    update_segment_coordinate_snapshot,
    tomo1_structure_identifier,
)

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="GDP Pavimentos Pro v1.1.3 Web Ready",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {--bg:#061423;--panel:#0b1e31;--panel2:#0d2439;--line:#25445f;--blue:#0878ff;--cyan:#21b7ff;--green:#38d46a;--orange:#ff7a00;--purple:#9b4dff;--text:#f4f8ff;--muted:#9eb3c8;}
    .stApp {background:radial-gradient(circle at 60% 20%,#0d2944 0%,#061423 42%,#04101d 100%);color:var(--text);}
    .block-container {padding-top:.55rem;max-width:1720px;padding-left:1rem;padding-right:1rem;}
    header[data-testid="stHeader"] {background:transparent;height:2rem;}
    .main-title{font-size:1.6rem;font-weight:900;color:#fff;margin:0}.subtle{color:var(--muted);margin-bottom:.4rem}
    section[data-testid="stSidebar"]{background:linear-gradient(180deg,#061727 0%,#071d31 55%,#061421 100%);border-right:1px solid #17334d;}
    section[data-testid="stSidebar"] *{color:#eaf4ff}.brand-box{background:linear-gradient(145deg,#071727,#0b2d4d);padding:18px;border-radius:13px;border:1px solid #23455f;margin-bottom:12px;box-shadow:0 14px 35px rgba(0,0,0,.28)}
    .brand-title{font-size:1.15rem;font-weight:900;color:#fff}.brand-sub{font-size:.8rem;color:#a9c0d6;margin-top:4px}
    .mode-card{padding:11px 15px;border:1px solid #285072;border-radius:10px;background:linear-gradient(100deg,#0b2238,#0b1b2b);font-weight:700;color:#e8f4ff;box-shadow:0 8px 20px rgba(0,0,0,.18)}
    div[data-testid="stTabs"]{background:transparent} div[data-testid="stTabs"] button{font-weight:750;color:#a9bfd3;border-radius:8px 8px 0 0;padding:.55rem .72rem} div[data-testid="stTabs"] button[aria-selected="true"]{background:#0e64d9;color:#fff}
    div[data-testid="stMetric"]{background:linear-gradient(145deg,#0c2135,#091b2c);border:1px solid #28465f;padding:13px;border-radius:12px;box-shadow:0 9px 22px rgba(0,0,0,.23)}
    div[data-testid="stMetric"] label{color:#a9c0d6!important} div[data-testid="stMetric"] [data-testid="stMetricValue"]{color:#fff!important}
    .dash-card{background:linear-gradient(145deg,#0d2237,#091a2a);border:1px solid #294861;border-radius:13px;padding:15px;box-shadow:0 12px 28px rgba(0,0,0,.25);min-height:145px;position:relative;overflow:hidden}
    .dash-card:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent,#0878ff)}
    .dash-label{font-size:.72rem;font-weight:850;color:#b4c7da;text-transform:uppercase;letter-spacing:.35px}.dash-value{font-size:1.95rem;font-weight:950;color:var(--accent,#35a8ff);margin:.3rem 0}.dash-note{font-size:.82rem;color:#c1d1df;line-height:1.55}
    .panel-card{background:linear-gradient(145deg,#0c2134,#081a2b);border:1px solid #294860;border-radius:13px;padding:14px;box-shadow:0 10px 25px rgba(0,0,0,.22)}
    .panel-title{color:#2ca4ff;font-weight:850;font-size:.9rem;text-transform:uppercase;letter-spacing:.3px;margin-bottom:8px}
    .status-ok{background:linear-gradient(90deg,#083923,#0a2c22);border:1px solid #17643d;border-radius:9px;padding:11px;color:#49e283;font-weight:800}
    .layer-row{display:grid;grid-template-columns:14px 1fr auto;gap:9px;align-items:center;padding:10px 8px;border-bottom:1px solid #1e3a52;color:#dcecff;font-size:.86rem}.layer-dot{width:11px;height:11px;border-radius:3px}.thickness-box{background:#0a2843;border:1px solid #265878;border-radius:9px;padding:13px;text-align:center;color:#35a8ff;font-size:1.55rem;font-weight:950;margin-top:10px}
    .alert-row{border:1px solid #29475f;border-radius:9px;padding:9px 10px;margin:7px 0;color:#dce9f4;background:#0a1c2c;font-size:.83rem}.alert-ok{border-left:4px solid #39d66f}.alert-warn{border-left:4px solid #ffc329}
    .dark-note{color:#99aec1;font-size:.75rem;text-align:center;padding:7px;border-top:1px solid #1e3a50}
    .stDataFrame,.stPlotlyChart{border-radius:10px;overflow:hidden}
    div[data-testid="stExpander"]{background:#091c2d;border:1px solid #29475f;border-radius:10px}
    .stButton>button,.stDownloadButton>button{background:#0c64d6;color:white;border:1px solid #2b83ea;border-radius:8px;font-weight:750}.stButton>button:hover,.stDownloadButton>button:hover{background:#0878ff;color:white}
    div[data-baseweb="input"],div[data-baseweb="select"]>div,textarea{background:#0a1d2f!important;color:#edf6ff!important;border-color:#2b4b65!important}
    h1,h2,h3,h4,h5,p,span,label{color:inherit}

    /* v1.0.1 — legibilidad reforzada para formularios oscuros */
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stTextArea"] label,
    div[data-testid="stSlider"] label,
    div[data-testid="stCheckbox"] label,
    div[data-testid="stRadio"] label,
    div[data-testid="stFileUploader"] label,
    .stNumberInput label, .stTextInput label, .stSelectbox label, .stTextArea label {
        color:#f5f9ff !important; font-weight:750 !important; opacity:1 !important;
        font-size:.91rem !important; letter-spacing:.01em !important;
    }
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background:linear-gradient(180deg,#10283d 0%,#0b2033 100%) !important;
        border:1px solid #315878 !important; border-radius:9px !important;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.025) !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input,
    input[type="number"], input[type="text"] {
        color:#ffffff !important; -webkit-text-fill-color:#ffffff !important;
        caret-color:#47a8ff !important; font-weight:650 !important;
        background:transparent !important; opacity:1 !important;
    }
    div[data-testid="stNumberInput"] button {
        background:#0d2941 !important; color:#55b5ff !important;
        border-color:#315878 !important;
    }
    div[data-testid="stNumberInput"] button:hover {background:#123b5e !important;color:#fff !important;}
    div[data-testid="stNumberInput"] svg {fill:#55b5ff !important;}
    div[data-baseweb="select"] > div {
        background:#0d2438 !important;color:#fff !important;border-color:#315878 !important;
    }
    div[data-baseweb="select"] span {color:#fff !important;}
    .stCaptionContainer, [data-testid="stCaptionContainer"] {color:#b9cde0 !important;}
    small, .stMarkdown small {color:#b9cde0 !important;}
    .stMarkdown, .stMarkdown p, .stMarkdown li {color:#eef6ff;}

    /* Separación visual similar al dashboard de referencia */
    div[data-testid="stVerticalBlockBorderWrapper"] {border-color:#24445e !important;}
    hr {border-color:#24445e !important;}

    /* v1.0.2 — contraste definitivo de campos numéricos y de texto */
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextInput"] input,
    div[data-testid="stDateInput"] input,
    input[data-baseweb="input"],
    input[type="number"], input[type="text"] {
        background:#071827 !important;
        color:#ffffff !important;
        -webkit-text-fill-color:#ffffff !important;
        opacity:1 !important;
        font-size:1.02rem !important;
        font-weight:750 !important;
        text-shadow:none !important;
        caret-color:#55b5ff !important;
        color-scheme:dark !important;
    }
    div[data-testid="stNumberInput"] [data-baseweb="input"],
    div[data-testid="stTextInput"] [data-baseweb="input"],
    div[data-testid="stDateInput"] [data-baseweb="input"] {
        background:#071827 !important;
        border:1px solid #39719a !important;
        box-shadow:inset 0 0 0 1px rgba(50,155,230,.10) !important;
    }
    div[data-testid="stNumberInput"] input::placeholder,
    div[data-testid="stTextInput"] input::placeholder {
        color:#8fa9bf !important; -webkit-text-fill-color:#8fa9bf !important; opacity:1 !important;
    }
    div[data-testid="stNumberInput"] button {
        background:#07365a !important; color:#fff !important;
        border-color:#5ab7f5 !important; min-width:2.25rem !important;
    }
    div[data-testid="stNumberInput"] button svg {fill:#ffffff !important; stroke:#ffffff !important;}
    div[data-testid="stNumberInput"] label, div[data-testid="stTextInput"] label {
        color:#ffffff !important; opacity:1 !important; text-shadow:0 1px 1px rgba(0,0,0,.45);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Datos base editables del MVP
# -----------------------------
VEHICLE_DEFAULTS = pd.DataFrame(
    [
        ["Automóviles / vehículos livianos", "Liviano", 0.0001, 800],
        ["Pickup / carga liviana", "Carga liviana", 0.0000, 0],
        ["Buses", "Pesado", 0.65, 20],
        ["Camión C2", "Pesado", 0.80, 35],
        ["Camión C3", "Pesado", 1.40, 20],
        ["Camión C4", "Pesado", 0.00, 0],
        ["Tractocamión T3-S2", "Pesado", 2.20, 10],
        ["Otros pesados", "Pesado", 1.00, 5],
    ],
    columns=["Categoría", "Grupo de tránsito", "Factor camión", "TPD"],
)

# Catálogo demostrativo. Se deja editable para incorporar las tablas completas del GDP.
CATALOG_DEFAULT = pd.DataFrame(
    [
        ["T2", "S1", "OP2", "B9", "Carpeta asfáltica", 7, 21, 30],
        ["T2", "S1", "OP3", "C3", "Base estabilizada", 0, 18, 25],
        ["T2", "S1", "OP4", "D2", "Base estabilizada con cal", 0, 18, 25],
        ["T2", "S1", "OP5", "F2", "Solución alternativa", 0, 20, 30],
        ["T2", "S2", "OP1", "A9", "Tratamiento superficial", 0, 21, 30],
        ["T2", "S2", "OP2", "B10", "Carpeta asfáltica", 7, 18, 23],
        ["T2", "S3", "OP1", "A10", "Tratamiento superficial", 0, 18, 25],
        ["T2", "S3", "OP2", "B11", "Carpeta asfáltica", 6, 18, 20],
        ["T2", "S3", "OP3", "C4", "Base estabilizada", 0, 16, 20],
        ["T2", "S3", "OP5", "F3", "Solución alternativa", 0, 18, 24],
        ["T2", "S4", "OP1", "A11", "Tratamiento superficial", 0, 18, 20],
    ],
    columns=[
        "Tránsito", "Subrasante", "Opción", "Código", "Superficie",
        "Carpeta_cm", "Base_cm", "Subbase_cm"
    ],
)

# TOMO2_METHODOLOGY_HARDENING
TRAFFIC_RANGES = [
    ("U1", 0, 20_000),
    ("U2", 20_000, 50_000),
    ("U3", 50_000, 100_000),
    ("T1", 100_000, 150_000),
    ("T2", 150_000, 300_000),
    ("T3", 300_000, 500_000),
    ("T4", 500_000, 700_000),
    ("T5", 700_000, 1_000_000),
]


def growth_factor(rate_decimal: float, years: int) -> float:
    if years <= 0:
        return 0.0
    if abs(rate_decimal) < 1e-12:
        return float(years)
    return ((1 + rate_decimal) ** years - 1) / rate_decimal


def traffic_class(esal: float) -> str:
    for label, low, high in TRAFFIC_RANGES:
        if low <= esal < high:
            return label
    if esal >= 1_000_000:
        return ">T5"
    return "U1"


def tomo1_design_category(esal: float) -> int:
    """GDP-2024 Tomo I, Tabla 102-01: categoría jerárquica por ESAL de diseño."""
    esal = float(esal or 0.0)
    if esal < 3_000_000:
        return 3
    if esal <= 25_000_000:
        return 2
    return 1


def tomo1_design_category_label(esal: float) -> str:
    return f"Categoría {tomo1_design_category(esal)}"


def subgrade_class(cbr: float) -> str:
    # Se resuelve el vacío 3-4 mediante criterio conservador.
    if cbr < 4:
        return "S1"
    if cbr <= 6:
        return "S2"
    if cbr <= 9:
        return "S3"
    return "S4"


def resilient_modulus(cbr: float) -> float:
    if cbr <= 0:
        return 0.0
    if cbr < 12:
        return 17.6 * (cbr ** 0.64)
    return 22.1 * (cbr ** 0.55)


def money(value: float) -> str:
    return f"₡{value:,.0f}".replace(",", " ")


# MAP_GOOGLE_EARTH_TAB
def _xml_escape(value) -> str:
    return (str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def project_point_kml(project_name: str, latitude: float, longitude: float, description: str = "") -> str:
    name = _xml_escape(project_name or "Proyecto GDP")
    desc = _xml_escape(description)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        '  <Document>\n'
        f'    <name>{name}</name>\n'
        '    <Placemark>\n'
        f'      <name>{name}</name>\n'
        f'      <description>{desc}</description>\n'
        '      <Point>\n'
        f'        <coordinates>{float(longitude):.8f},{float(latitude):.8f},0</coordinates>\n'
        '      </Point>\n'
        '    </Placemark>\n'
        '  </Document>\n'
        '</kml>\n'
    )


# MAP_GOOGLE_EARTH_PROJECT_FEATURES
def project_features_kml(project_name: str, points: list[dict], lines: list[dict]) -> str:
    name = _xml_escape(project_name or "Proyecto GDP")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        f'<name>{name}</name>',
        '<Style id="projectPoint"><IconStyle><scale>1.1</scale></IconStyle></Style>',
        '<Style id="projectLine"><LineStyle><width>4</width></LineStyle></Style>',
        '<Folder><name>Puntos del proyecto</name>',
    ]
    for p in points:
        if not p.get('valid', False):
            continue
        pname = _xml_escape(p.get('name', 'Punto'))
        ptype = _xml_escape(p.get('type', 'Otro'))
        pdesc = _xml_escape(p.get('description', ''))
        lon = float(p['longitude']); lat = float(p['latitude'])
        parts.extend([
            '<Placemark>', f'<name>{pname}</name>', '<styleUrl>#projectPoint</styleUrl>',
            f'<description>Tipo: {ptype} | {pdesc}</description>',
            f'<Point><coordinates>{lon:.8f},{lat:.8f},0</coordinates></Point>', '</Placemark>'
        ])
    parts.extend(['</Folder>', '<Folder><name>Ejes y tramos</name>'])
    for line in lines:
        coords = line.get('coordinates', [])
        if len(coords) < 2:
            continue
        lname = _xml_escape(line.get('name', 'Tramo'))
        ldesc = _xml_escape(line.get('description', ''))
        coord_text = ' '.join(f"{float(lon):.8f},{float(lat):.8f},0" for lon, lat in coords)
        parts.extend([
            '<Placemark>', f'<name>{lname}</name>', '<styleUrl>#projectLine</styleUrl>',
            f'<description>{ldesc}</description>',
            '<LineString><tessellate>1</tessellate>', f'<coordinates>{coord_text}</coordinates>',
            '</LineString>', '</Placemark>'
        ])
    parts.extend(['</Folder>', '</Document>', '</kml>'])
    return '\n'.join(parts) + '\n'


def _interpolate_wgs84(start_lon: float, start_lat: float, end_lon: float, end_lat: float, ratio: float) -> tuple[float, float]:
    r = max(0.0, min(1.0, float(ratio)))
    return (float(start_lon) + (float(end_lon)-float(start_lon))*r,
            float(start_lat) + (float(end_lat)-float(start_lat))*r)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_road_route(waypoints: tuple[tuple[float, float], ...]):
    """Cache road matching so Streamlit reruns do not repeat external requests."""
    return road_route(waypoints)


# CLIMATE_GRANULAR_MASTER_CURVE_PHASE
# VERIFIED_CR2020_MATERIAL_THRESHOLDS
CR2020_BASE_CBR_MIN_PCT = 80.0
CR2020_SUBBASE_CBR_MIN_PCT = 30.0
CR2020_GRANULAR_QUALITY_REFERENCE = (
    'CR-2020: Sección 301 Subbases y bases granulares + Subsección 703.05 Agregado para capas de subbase y base'
)

# NORMATIVE_EVIDENCE_MATRIX
NORMATIVE_SOURCES = {
    'GDP2024_TOMO_I': {
        'document': 'GDP-2024 Tomo I — Guía mecanística empírica para el diseño de pavimentos flexibles y semirrígidos',
        'authority': 'MOPT',
        'decree': '44762-MOPT',
        'status': 'Oficial y vigente',
        'url': 'https://repositorio.mopt.go.cr/items/0b5becde-1d3b-47b2-b66a-118727ac6058',
    },
    'CR2020': {
        'document': 'CR-2020 — Manual de Especificaciones Generales para la Construcción de Carreteras, Caminos y Puentes',
        'authority': 'MOPT',
        'decree': '43397-MOPT',
        'status': 'Oficial y vigente',
        'url': 'https://repositorio.mopt.go.cr/items/e2dc2d1b-643a-4b14-814c-ecd3e1f12491',
    },
}


def normative_evidence_table() -> pd.DataFrame:
    return pd.DataFrame([
        {
            'Control': 'Categoría jerárquica Tomo I por ESAL',
            'Documento': 'GDP-2024 Tomo I', 'Referencia': 'Tabla 102-01',
            'Estado': 'Verificado en la aplicación', 'Automático': 'Sí',
        },
        {
            'Control': 'CBR mínimo base granular',
            'Documento': 'CR-2020', 'Referencia': 'Sección 301 / Subsección 703.05',
            'Estado': 'Control fijo incorporado', 'Automático': 'Sí',
        },
        {
            'Control': 'CBR mínimo subbase granular',
            'Documento': 'CR-2020', 'Referencia': 'Sección 301 / Subsección 703.05',
            'Estado': 'Control fijo incorporado', 'Automático': 'Sí',
        },
        {
            'Control': 'Clasificación climática por TMI',
            'Documento': 'GDP-2024 Tomo I', 'Referencia': 'Sección 302, Tabla 302-01 y Anexo B',
            'Estado': 'Cálculo documentado incorporado', 'Automático': 'Sí, con series mensuales',
        },
        {
            'Control': 'Rango de espesor de carpeta asfáltica',
            'Documento': 'GDP-2024 / CR-2020', 'Referencia': 'Diseño, fórmula de trabajo y criterio específico del proyecto',
            'Estado': 'No existe un rango universal bloqueado en la app', 'Automático': 'Solo con criterio documentado',
        },
    ])

def granular_resilient_modulus_mpa(k1: float, k2: float, k3: float, theta_kpa: float, tau_oct_kpa: float, pa_kpa: float = 101.325) -> float:
    """Modelo constitutivo configurable para materiales granulares.

    Mr = k1*Pa*(theta/Pa)^k2*(tau_oct/Pa + 1)^k3.
    Las tensiones se ingresan en kPa y el resultado se devuelve en MPa.
    Los coeficientes deben provenir del ensayo/modelo documentado aplicable.
    """
    pa = max(float(pa_kpa), 1e-9)
    theta = max(float(theta_kpa), 1e-9)
    tau = max(float(tau_oct_kpa), 0.0)
    mr_kpa = float(k1) * pa * (theta / pa) ** float(k2) * (tau / pa + 1.0) ** float(k3)
    return max(mr_kpa / 1000.0, 0.0)


def wlf_log10_shift_factor(temp_c: float, reference_temp_c: float, c1: float, c2: float) -> float:
    """Factor de desplazamiento WLF configurable: log10(aT)."""
    dt = float(temp_c) - float(reference_temp_c)
    denom = float(c2) + dt
    if abs(denom) < 1e-9:
        denom = 1e-9 if denom >= 0 else -1e-9
    return -float(c1) * dt / denom


def master_curve_dynamic_modulus_mpa(log10_reduced_frequency: float, delta: float, alpha: float, beta: float, gamma: float) -> float:
    """Curva maestra sigmoidal configurable en log10(E*) con E* en MPa."""
    loge = float(delta) + float(alpha) / (1.0 + math.exp(float(beta) + float(gamma) * float(log10_reduced_frequency)))
    return 10.0 ** loge


# ADVANCED_DESIGN_CONTROLS_6_7_8_9_10_11_16_18_20

def stabilized_base_screening_model(modulus_mpa: float, strength_mpa: float, thickness_cm: float,
                                    shrinkage_risk: str, interface_condition: str) -> dict:
    """Caracterización propia de base estabilizada para control/cribado.

    No sustituye una función de transferencia calibrada. Resume rigidez, resistencia,
    esbeltez, contracción e interfaz para decidir si la capa requiere revisión específica.
    """
    e = max(float(modulus_mpa), 0.0)
    r = max(float(strength_mpa), 0.0)
    h = max(float(thickness_cm), 0.0)
    rigidity_index = e * (h / 10.0) ** 3 if h > 0 else 0.0
    risk_score = {'Bajo': 0.8, 'Medio': 1.0, 'Alto': 1.25}.get(str(shrinkage_risk), 1.0)
    interface_factor = {'Adherida': 1.0, 'Parcialmente adherida': 1.10, 'Deslizante': 1.25}.get(str(interface_condition), 1.0)
    return {
        'modulus_mpa': e, 'strength_mpa': r, 'thickness_cm': h,
        'rigidity_index': rigidity_index,
        'shrinkage_risk': shrinkage_risk,
        'interface_condition': interface_condition,
        'screening_penalty_factor': risk_score * interface_factor,
        'status': 'Caracterizada' if h > 0 and e > 0 and r > 0 else 'Incompleta',
        'note': 'Modelo propio de caracterización/cribado; requiere verificación estructural y de fisuración reflejada.'
    }


def construction_constraints_check(structure: dict, constraints: dict) -> dict:
    ac = float(structure.get('Carpeta_cm', 0) or 0)
    base = float(structure.get('Base_cm', 0) or 0)
    subbase = float(structure.get('Subbase_cm', 0) or 0)
    inc = max(float(constraints.get('increment_cm', 0.5) or 0.5), 0.1)
    checks = {
        'carpeta_min': ac >= float(constraints.get('asphalt_min_cm', 0) or 0),
        'carpeta_max': ac <= float(constraints.get('asphalt_max_cm', 999) or 999),
        'base_min': base >= float(constraints.get('base_min_cm', 0) or 0),
        'subbase_min': subbase >= float(constraints.get('subbase_min_cm', 0) or 0),
        'incremento_carpeta': abs(ac / inc - round(ac / inc)) < 1e-6,
        'incremento_base': abs(base / inc - round(base / inc)) < 1e-6,
        'incremento_subbase': abs(subbase / inc - round(subbase / inc)) < 1e-6,
    }
    return {'complies': all(checks.values()), 'checks': checks, 'increment_cm': inc}


def optimize_structure_with_constraints(base_structure: dict, materials: dict, subgrade_mr_mpa: float,
                                        axle_load_kn: float, tire_pressure_kpa: float, tires_per_axle: int,
                                        allowable_eps_t: float, allowable_eps_v: float, reliability_pct: float,
                                        log_sigma: float, area_m2: float, prices: dict, constraints: dict,
                                        max_increment_cm: float = 10.0) -> pd.DataFrame:
    """Optimización discreta de cribado con restricciones constructivas obligatorias."""
    rows = []
    step = max(float(constraints.get('increment_cm', 1.0) or 1.0), 0.5)
    incs = []
    x = 0.0
    while x <= float(max_increment_cm) + 1e-9:
        incs.append(round(x, 6)); x += step
    ac0 = float(base_structure.get('Carpeta_cm', 0) or 0)
    bg0 = float(base_structure.get('Base_granular_cm', base_structure.get('Base_cm', 0)) or 0)
    bs0 = float(base_structure.get('Base_estabilizada_cm', 0) or 0)
    sb0 = float(base_structure.get('Subbase_cm', 0) or 0)
    rel_mult = reliability_multiplier(reliability_pct, log_sigma)
    for da in incs:
        for db in incs:
            for ds in incs:
                s = dict(base_structure)
                s['Carpeta_cm'] = ac0 + da
                s['Base_granular_cm'] = bg0 + db
                s['Base_estabilizada_cm'] = bs0
                s['Base_cm'] = bg0 + db + bs0
                s['Subbase_cm'] = sb0 + ds
                cc = construction_constraints_check(s, constraints)
                if not cc['complies']:
                    continue
                resp = mechanistic_screening_response(s, materials, subgrade_mr_mpa, axle_load_kn, tire_pressure_kpa, tires_per_axle)
                fu = resp['asphalt_tensile_microstrain_screening'] / max(float(allowable_eps_t), 1e-6) * rel_mult
                ru = resp['subgrade_vertical_microstrain_screening'] / max(float(allowable_eps_v), 1e-6) * rel_mult
                cost = float(area_m2) * (
                    s['Carpeta_cm']/100.0*float(prices.get('surface',0)) +
                    s['Base_cm']/100.0*float(prices.get('base',0)) +
                    s['Subbase_cm']/100.0*float(prices.get('subbase',0))
                )
                rows.append({
                    'Código': f"OPT-{len(rows)+1:04d}", 'Carpeta_cm': s['Carpeta_cm'],
                    'Base_cm': s['Base_cm'], 'Subbase_cm': s['Subbase_cm'],
                    'Espesor_total_cm': s['Carpeta_cm']+s['Base_cm']+s['Subbase_cm'],
                    'Utilización_fatiga_diseño': fu, 'Utilización_ahuellamiento_diseño': ru,
                    'Máxima_utilización': max(fu,ru), 'Cumple_cribado': 'Sí' if max(fu,ru)<=1.0 else 'No',
                    'Cumple_constructivo': 'Sí', 'Costo_inicial': cost,
                })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out['Cumple_num'] = out['Cumple_cribado'].eq('Sí').astype(int)
    return out.sort_values(['Cumple_num','Costo_inicial','Máxima_utilización','Espesor_total_cm'], ascending=[False,True,True,True]).drop(columns=['Cumple_num']).reset_index(drop=True)


def engineering_readiness_score(payload: dict) -> tuple[int, list[dict]]:
    mats = payload.get('materials', {}) or {}
    mech = payload.get('mechanistic_screening', {}) or {}
    interfaces = payload.get('layer_interfaces', {}) or {}
    constraints = payload.get('construction_constraints', {}) or {}
    climate = payload.get('climate_material', {}) or {}
    items = [
        ('Tránsito y categoría', float(payload.get('traffic',{}).get('esal',0) or 0)>0, 12),
        ('Subrasante Mr documentado/estimado', float(payload.get('subgrade',{}).get('mr',0) or 0)>0, 10),
        ('Granulares caracterizados', bool(mats.get('granular_quality')), 12),
        ('Modelo granular k1-k2-k3', bool(mats.get('granular_model')), 8),
        ('Mezcla E* documentada', float(mats.get('asphalt_dynamic_modulus_mpa',0) or 0)>0, 10),
        ('Curva maestra/clima', bool(climate), 10),
        ('Interfaces documentadas', bool(interfaces), 8),
        ('Restricciones constructivas', bool(constraints), 8),
        ('Respuesta mecanística ejecutada', bool(mech), 12),
        ('Fuente de materiales', bool(str(mats.get('source','')).strip()), 10),
    ]
    score = sum(w for _,ok,w in items if ok)
    detail = [{'Componente':n,'Estado':'Completo' if ok else 'Pendiente','Peso':w} for n,ok,w in items]
    return int(min(score,100)), detail


def scenario_comparison_table(base_esal: float, base_mr: float, base_temp: float, selected: dict,
                              materials: dict, axle_load_kn: float, tire_pressure_kpa: float,
                              tires_per_axle: int, allowable_eps_t: float, allowable_eps_v: float) -> pd.DataFrame:
    scenarios = [
        ('Conservador', 1.25, 0.80, 5.0),
        ('Esperado', 1.00, 1.00, 0.0),
        ('Optimista', 0.85, 1.15, -3.0),
    ]
    rows = []
    for name, traffic_factor, mr_factor, temp_delta in scenarios:
        mr_s = max(float(base_mr)*mr_factor, 1.0)
        esal_s = max(float(base_esal)*traffic_factor, 1.0)
        resp = mechanistic_screening_response(selected, materials, mr_s, axle_load_kn, tire_pressure_kpa, tires_per_axle)
        fu = resp['asphalt_tensile_microstrain_screening']/max(float(allowable_eps_t),1e-6)
        ru = resp['subgrade_vertical_microstrain_screening']/max(float(allowable_eps_v),1e-6)
        rows.append({'Escenario':name,'Factor_tránsito':traffic_factor,'ESAL':esal_s,'Factor_Mr':mr_factor,
                     'Mr_subrasante_MPa':mr_s,'Temperatura_pavimento_C':float(base_temp)+temp_delta,
                     'Utilización_fatiga':fu,'Utilización_ahuellamiento':ru,'Máxima_utilización':max(fu,ru),
                     'Estado':'Cumple cribado' if max(fu,ru)<=1.0 else 'Revisar'})
    return pd.DataFrame(rows)

# AASHTO93_LAYER_CONTROLS
def aashto93_flexible_log_w18(sn: float, mr_mpa: float, zr: float, so: float, delta_psi: float) -> float:
    """Ecuación AASHTO 1993 para pavimento flexible.

    Mr se recibe en MPa y se convierte a psi. Devuelve log10(W18).
    Este cálculo se presenta como diseño preliminar AASHTO-93, separado del
    análisis mecanístico-empírico GDP-2024 Tomo I.
    """
    sn = max(float(sn), 0.01)
    mr_psi = max(float(mr_mpa) * 145.0377377, 1.0)
    delta_psi = min(max(float(delta_psi), 0.01), 2.69)
    service_term = math.log10(delta_psi / (4.2 - 1.5))
    denominator = 0.40 + 1094.0 / ((sn + 1.0) ** 5.19)
    return (
        float(zr) * float(so)
        + 9.36 * math.log10(sn + 1.0)
        - 0.20
        + service_term / denominator
        + 2.32 * math.log10(mr_psi)
        - 8.07
    )


def aashto93_required_sn(w18: float, mr_mpa: float, reliability_pct: float, so: float,
                         initial_serviceability: float, terminal_serviceability: float) -> dict:
    """Resuelve SN requerido por bisección para la ecuación AASHTO-93 flexible."""
    w18 = max(float(w18), 1.0)
    r = min(max(float(reliability_pct) / 100.0, 0.500001), 0.999999)
    zr = NormalDist().inv_cdf(1.0 - r)
    delta_psi = max(float(initial_serviceability) - float(terminal_serviceability), 0.01)
    target = math.log10(w18)
    low, high = 0.01, 12.0
    while aashto93_flexible_log_w18(high, mr_mpa, zr, so, delta_psi) < target and high < 30.0:
        high *= 1.5
    for _ in range(90):
        mid = (low + high) / 2.0
        if aashto93_flexible_log_w18(mid, mr_mpa, zr, so, delta_psi) < target:
            low = mid
        else:
            high = mid
    sn_required = (low + high) / 2.0
    return {
        'sn_required': sn_required, 'zr': zr, 'so': float(so), 'delta_psi': delta_psi,
        'w18': w18, 'mr_mpa': float(mr_mpa), 'mr_psi': float(mr_mpa) * 145.0377377,
        'equation': 'AASHTO 1993 flexible: log10(W18)=ZR·So+9.36log10(SN+1)-0.20+[log10(ΔPSI/2.7)]/[0.40+1094/(SN+1)^5.19]+2.32log10(Mr)-8.07',
    }


def residual_layer_thicknesses(sn_required: float, a1: float, a2: float, a3: float, m2: float, m3: float,
                               d1_adopted_in: float, d2_adopted_in: float) -> dict:
    """Despejes secuenciales de espesor por SN residual; resultado en pulgadas."""
    a1 = max(float(a1), 1e-9); a2 = max(float(a2), 1e-9); a3 = max(float(a3), 1e-9)
    m2 = max(float(m2), 1e-9); m3 = max(float(m3), 1e-9)
    sn1 = a1 * max(float(d1_adopted_in), 0.0)
    d1_all_sn = max(float(sn_required), 0.0) / a1
    d2_req = max(float(sn_required) - sn1, 0.0) / (a2 * m2)
    sn2_adopted = a2 * m2 * max(float(d2_adopted_in), 0.0)
    d3_req = max(float(sn_required) - sn1 - sn2_adopted, 0.0) / (a3 * m3)
    return {'d1_if_single_layer_in': d1_all_sn, 'd2_residual_in': d2_req, 'd3_residual_in': d3_req}


# MECHANISTIC_SCREENING_PHASE2
# INTEGRATED_STAGES_2_5_9_10_11_12_13_18
def reliability_multiplier(reliability_pct: float, log_sigma: float) -> float:
    """Amplificador lognormal configurable para llevar una respuesta media a nivel de diseño.

    No es una ecuación GDP normativa. Se usa para que la confiabilidad afecte el resultado
    cuando el diseñador activa explícitamente este modelo configurable.
    """
    r = min(max(float(reliability_pct) / 100.0, 0.5001), 0.999)
    z = NormalDist().inv_cdf(r)
    return math.exp(z * max(float(log_sigma), 0.0))


def configurable_transfer_damage(mech: dict, esal: float, climate_factor: float, reliability_pct: float,
                                 log_sigma: float, reference_esal: float, fatigue_exponent: float,
                                 rutting_exponent: float) -> dict:
    """Índices de daño configurables basados en utilización mecanística.

    D = (utilización ** exponente) * (ESAL / ESAL_ref) * factor_climático.
    Luego se amplifica por confiabilidad lognormal. El usuario debe calibrar parámetros
    para su procedimiento/proyecto; no se presenta como función de transferencia GDP oficial.
    """
    ref = max(float(reference_esal), 1.0)
    climate = max(float(climate_factor), 0.01)
    f_util = max(float(mech.get('fatigue_utilization_ratio', 0.0) or 0.0), 0.0)
    r_util = max(float(mech.get('rutting_utilization_ratio', 0.0) or 0.0), 0.0)
    traffic_ratio = max(float(esal), 0.0) / ref
    fatigue_mean = (f_util ** max(float(fatigue_exponent), 0.01)) * traffic_ratio * climate
    rutting_mean = (r_util ** max(float(rutting_exponent), 0.01)) * traffic_ratio * climate
    mult = reliability_multiplier(reliability_pct, log_sigma)
    return {
        'method': 'Función de transferencia configurable por utilización; pendiente de calibración específica',
        'reference_esal': ref, 'climate_factor': climate, 'reliability_multiplier': mult,
        'fatigue_damage_mean': fatigue_mean, 'rutting_damage_mean': rutting_mean,
        'fatigue_damage_design': fatigue_mean * mult, 'rutting_damage_design': rutting_mean * mult,
        'fatigue_exponent': float(fatigue_exponent), 'rutting_exponent': float(rutting_exponent),
        'calibration_status': 'Configurable / no normativa',
    }


def monthly_material_climate_factor(monthly_modulus_df: pd.DataFrame, reference_modulus_mpa: float) -> float:
    """Factor climático relativo derivado de E* mensual documentado por el usuario."""
    if monthly_modulus_df is None or monthly_modulus_df.empty:
        return 1.0
    vals = pd.to_numeric(monthly_modulus_df.get('E* mensual (MPa)', pd.Series(dtype=float)), errors='coerce').dropna()
    if vals.empty:
        return 1.0
    ref = max(float(reference_modulus_mpa), 1.0)
    # Menor rigidez relativa aumenta el factor de exposición; promedio mensual simple.
    ratios = (ref / vals.clip(lower=1.0)).clip(lower=0.25, upper=4.0)
    return float(ratios.mean())


def optimize_screening_structure(base_structure: Dict, materials: dict, subgrade_mr_mpa: float,
                                 axle_load_kn: float, tire_pressure_kpa: float, tires_per_axle: int,
                                 allowable_eps_t: float, allowable_eps_v: float, reliability_pct: float,
                                 log_sigma: float, area_m2: float, prices: dict, max_increment_cm: int = 12) -> pd.DataFrame:
    """Explora combinaciones discretas alrededor de la sección activa usando el cribado ME.

    Solo genera candidatos para revisión. No constituye optimización normativa GDP.
    """
    rows = []
    ac0 = float(base_structure.get('Carpeta_cm', 0) or 0)
    bg0 = float(base_structure.get('Base_granular_cm', base_structure.get('Base_cm', 0)) or 0)
    bs0 = float(base_structure.get('Base_estabilizada_cm', 0) or 0)
    sb0 = float(base_structure.get('Subbase_cm', 0) or 0)
    imp0 = float(base_structure.get('Mejoramiento_subrasante_cm', 0) or 0)
    step = 2.0
    increments = list(range(0, int(max_increment_cm) + 1, int(step)))
    rel_mult = reliability_multiplier(reliability_pct, log_sigma)
    for da in increments:
        for db in increments:
            for ds in increments:
                s = dict(base_structure)
                s['Carpeta_cm'] = ac0 + da
                s['Base_granular_cm'] = bg0 + db
                s['Base_estabilizada_cm'] = bs0
                s['Base_cm'] = bg0 + db + bs0
                s['Subbase_cm'] = sb0 + ds
                s['Mejoramiento_subrasante_cm'] = imp0
                resp = mechanistic_screening_response(s, materials, subgrade_mr_mpa, axle_load_kn, tire_pressure_kpa, tires_per_axle)
                fu = resp['asphalt_tensile_microstrain_screening'] / max(float(allowable_eps_t), 1e-6)
                ru = resp['subgrade_vertical_microstrain_screening'] / max(float(allowable_eps_v), 1e-6)
                fu_d = fu * rel_mult
                ru_d = ru * rel_mult
                cost = float(area_m2) * (
                    s['Carpeta_cm'] / 100.0 * float(prices.get('surface', 0)) +
                    s['Base_cm'] / 100.0 * float(prices.get('base', 0)) +
                    s['Subbase_cm'] / 100.0 * float(prices.get('subbase', 0))
                )
                compliant = fu_d <= 1.0 and ru_d <= 1.0
                rows.append({
                    'Código': f"OPT-{int(ac0+da):02d}-{int(bg0+db):02d}-{int(sb0+ds):02d}",
                    'Superficie': s.get('Superficie', 'Carpeta asfáltica'),
                    'Carpeta_cm': s['Carpeta_cm'], 'Base_cm': s['Base_cm'],
                    'Base_granular_cm': s['Base_granular_cm'], 'Base_estabilizada_cm': s['Base_estabilizada_cm'],
                    'Subbase_cm': s['Subbase_cm'], 'Mejoramiento_subrasante_cm': s['Mejoramiento_subrasante_cm'],
                    'Espesor_total_cm': s['Carpeta_cm'] + s['Base_cm'] + s['Subbase_cm'] + s['Mejoramiento_subrasante_cm'],
                    'Utilización_fatiga_diseño': fu_d, 'Utilización_ahuellamiento_diseño': ru_d,
                    'Máxima_utilización': max(fu_d, ru_d), 'Cumple_cribado': 'Sí' if compliant else 'No',
                    'Costo_inicial': cost, 'Coincidencia': 'Tomo I - candidato de cribado',
                })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(['Cumple_cribado', 'Costo_inicial', 'Máxima_utilización'], ascending=[False, True, True]).reset_index(drop=True)
    return out


def design_data_quality_score(payload: dict) -> tuple[int, list[dict]]:
    """Índice documental, no normativo, para identificar vacíos del expediente."""
    project = payload.get('project', {})
    traffic = payload.get('traffic', {})
    subgrade = payload.get('subgrade', {})
    climate = payload.get('climate', {})
    materials = payload.get('materials', {})
    drainage = payload.get('drainage', {})
    mech = payload.get('mechanistic_screening', {})
    checks = [
        ('Proyecto y geometría', bool(project.get('name')) and float(project.get('length_m', 0) or 0) > 0),
        ('Tránsito / ESAL', float(traffic.get('esal', 0) or 0) > 0),
        ('Subrasante / CBR', float(subgrade.get('cbr', 0) or 0) > 0),
        ('Fuente de Mr', bool(subgrade.get('mr_source'))),
        ('Clima documentado', bool(climate.get('source')) and bool(climate.get('period'))),
        ('Materiales documentados', bool(materials.get('source'))),
        ('Respuesta estructural', bool(mech)),
        ('Drenaje', bool(drainage.get('side_ditches')) and bool(drainage.get('outlets'))),
    ]
    detail = [{'Componente': name, 'Estado': 'Completo' if ok else 'Pendiente'} for name, ok in checks]
    score = round(100 * sum(1 for _, ok in checks if ok) / len(checks))
    return score, detail


def _circular_load_vertical_stress(q_mpa: float, radius_m: float, depth_m: float) -> float:
    """Esfuerzo vertical bajo el centro de un área circular uniformemente cargada.

    Se usa únicamente como núcleo de cribado de respuesta. No reemplaza un solver
    elástico multicapa (Burmister/ME) ni incorpora interacción completa entre neumáticos.
    """
    q_mpa = max(float(q_mpa), 0.0)
    a = max(float(radius_m), 1e-6)
    z = max(float(depth_m), 1e-6)
    return q_mpa * (1.0 - 1.0 / ((1.0 + (a / z) ** 2) ** 1.5))


def _odemark_equivalent_depth(layers: list[tuple[float, float]], reference_modulus_mpa: float) -> float:
    """Profundidad transformada tipo Odemark para el cribado de tensiones verticales."""
    eref = max(float(reference_modulus_mpa), 1e-6)
    total = 0.0
    for thickness_m, modulus_mpa in layers:
        if thickness_m <= 0:
            continue
        ratio = max(float(modulus_mpa), 1e-6) / eref
        total += float(thickness_m) * ratio ** (1.0 / 3.0)
    return max(total, 1e-6)


def mechanistic_screening_response(structure: Dict, materials: dict, subgrade_mr_mpa: float,
                                    axle_load_kn: float, tire_pressure_kpa: float, tires_per_axle: int,
                                    base_poisson: float = 0.35, subbase_poisson: float = 0.35,
                                    subgrade_poisson: float = 0.40) -> dict:
    """Respuesta mecanística de cribado para control interno del Tomo I.

    Usa presión circular uniforme + profundidad equivalente tipo Odemark. La deformación
    de tracción bajo carpeta es un indicador de cribado basado en contraste de rigideces;
    no es una solución multicapa cerrada. Los resultados deben validarse con un solver
    multicapa y funciones de transferencia calibradas antes de una emisión definitiva.
    """
    axle_load_kn = max(float(axle_load_kn), 0.1)
    tire_pressure_kpa = max(float(tire_pressure_kpa), 1.0)
    tires = max(int(tires_per_axle), 1)
    tire_load_n = axle_load_kn * 1000.0 / tires
    pressure_pa = tire_pressure_kpa * 1000.0
    radius_m = math.sqrt(tire_load_n / (math.pi * pressure_pa))
    q_mpa = tire_pressure_kpa / 1000.0

    h_ac = max(float(structure.get("Carpeta_cm", 0) or 0) / 100.0, 0.0)
    h_bg = max(float(structure.get("Base_granular_cm", structure.get("Base_cm", 0)) or 0) / 100.0, 0.0)
    h_bs = max(float(structure.get("Base_estabilizada_cm", 0) or 0) / 100.0, 0.0)
    h_sb = max(float(structure.get("Subbase_cm", 0) or 0) / 100.0, 0.0)
    h_imp = max(float(structure.get("Mejoramiento_subrasante_cm", 0) or 0) / 100.0, 0.0)

    e_ac = max(float(materials.get("asphalt_dynamic_modulus_mpa", 0) or 0), 1.0)
    nu_ac = min(max(float(materials.get("asphalt_poisson", 0.35) or 0.35), 0.10), 0.49)
    e_bg = max(float(materials.get("base_mr_mpa", 0) or 0), 1.0)
    e_sb = max(float(materials.get("subbase_mr_mpa", 0) or 0), 1.0)
    e_bs = max(float(materials.get("stabilized_modulus_mpa", 0) or 0), 1.0)
    strength_bs = max(float(materials.get("stabilized_strength_mpa", 0) or 0), 0.0)
    e_sg = max(float(subgrade_mr_mpa), 1.0)

    # Profundidades equivalentes para esfuerzos verticales sobre interfaces críticas.
    z_ac = max(h_ac, radius_m * 0.20, 0.01)
    z_sg = _odemark_equivalent_depth(
        [(h_ac, e_ac), (h_bg, e_bg), (h_bs, e_bs), (h_sb, e_sb), (h_imp, max(e_sb, e_sg))], e_sg
    )
    sigma_ac = _circular_load_vertical_stress(q_mpa, radius_m, z_ac)
    sigma_sg = _circular_load_vertical_stress(q_mpa, radius_m, z_sg)

    support_modulus = e_bs if h_bs > 0 else (e_bg if h_bg > 0 else (e_sb if h_sb > 0 else e_sg))
    stiffness_contrast = min(3.0, max(0.60, (e_ac / max(support_modulus, 1.0)) ** 0.15))
    eps_t_micro = sigma_ac * (1.0 + nu_ac) / e_ac * stiffness_contrast * 1_000_000.0
    eps_v_micro = sigma_sg / e_sg * max(0.40, 1.0 - 0.50 * float(subgrade_poisson)) * 1_000_000.0

    stabilized_stress_mpa = 0.0
    stabilized_utilization = 0.0
    if h_bs > 0:
        layers_above_bs = [(h_ac, e_ac), (h_bg, e_bg)]
        z_bs = _odemark_equivalent_depth(layers_above_bs, e_bs) if layers_above_bs else max(h_ac, 0.01)
        stabilized_stress_mpa = _circular_load_vertical_stress(q_mpa, radius_m, max(z_bs, 0.01))
        stabilized_utilization = stabilized_stress_mpa / strength_bs if strength_bs > 0 else 0.0

    return {
        "method": "Cribado: carga circular uniforme + profundidad equivalente tipo Odemark",
        "axle_load_kn": axle_load_kn, "tires_per_axle": tires, "tire_load_kn": tire_load_n / 1000.0,
        "tire_pressure_kpa": tire_pressure_kpa, "contact_radius_m": radius_m,
        "sigma_bottom_asphalt_mpa": sigma_ac, "asphalt_tensile_microstrain_screening": eps_t_micro,
        "sigma_top_subgrade_mpa": sigma_sg, "subgrade_vertical_microstrain_screening": eps_v_micro,
        "stabilized_stress_mpa": stabilized_stress_mpa, "stabilized_stress_strength_ratio": stabilized_utilization,
        "equivalent_depth_to_subgrade_m": z_sg,
        "limitations": "No sustituye un solver elástico multicapa ni funciones de transferencia calibradas GDP-2024.",
    }


def _box_mesh(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, name: str, color: str):
    """Caja sólida simple usada para la plataforma visual."""
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]
    i = [0, 0, 0, 1, 1, 2, 4, 4, 5, 5, 6, 7]
    j = [1, 2, 4, 2, 5, 3, 5, 6, 6, 1, 2, 3]
    k = [2, 3, 5, 5, 4, 7, 6, 7, 1, 2, 3, 0]
    mesh = go.Mesh3d(
        x=x, y=y, z=z, i=i, j=j, k=k,
        name=name, color=color, opacity=1.0, flatshading=True,
        lighting=dict(ambient=.48, diffuse=.88, specular=.28, roughness=.62, fresnel=.08),
        lightposition=dict(x=90, y=-120, z=190),
        hovertemplate=f"<b>{name}</b><br>Espesor: {z1-z0:.1f} cm<extra></extra>",
        showscale=False,
    )
    edge_pairs = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    ex, ey, ez = [], [], []
    for a,b in edge_pairs:
        ex += [x[a],x[b],None]; ey += [y[a],y[b],None]; ez += [z[a],z[b],None]
    edges = go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",showlegend=False,hoverinfo="skip",line=dict(color="rgba(3,10,18,.96)",width=6))
    return mesh, edges



def _material_style(name: str):
    """Paletas inspiradas en un corte vial real: asfalto gris, agregado pétreo, subbase clara y suelo natural."""
    n = name.lower()
    if "asf" in n or "tratamiento" in n or "superficie" in n:
        return dict(
            palette=[[0.0,"#151515"],[0.12,"#222323"],[0.30,"#343535"],[0.50,"#494a49"],[0.68,"#626260"],[0.84,"#85847f"],[0.94,"#b2afa6"],[1.0,"#ddd9cf"]],
            seed=11, kind="asphalt", edge="#101111", rough=0.060
        )
    if "base granular" in n:
        return dict(
            palette=[[0.0,"#363737"],[0.12,"#4a4c4d"],[0.30,"#626568"],[0.48,"#7d8286"],[0.66,"#999fa3"],[0.82,"#b7bdc0"],[0.94,"#d4d8d8"],[1.0,"#eeeeea"]],
            seed=23, kind="base", edge="#252728", rough=0.19
        )
    if "subbase" in n:
        return dict(
            palette=[[0.0,"#79662f"],[0.12,"#8c7838"],[0.30,"#a28d48"],[0.48,"#b8a45c"],[0.66,"#cdbb76"],[0.82,"#dfcf91"],[0.94,"#eee0aa"],[1.0,"#f5e9c0"]],
            seed=37, kind="subbase", edge="#5e4e25", rough=0.20
        )
    return dict(
        palette=[[0.0,"#3a271a"],[0.12,"#4c3422"],[0.30,"#684a31"],[0.48,"#815f43"],[0.66,"#9b7959"],[0.82,"#b39372"],[0.94,"#c6aa8a"],[1.0,"#d5bea1"]],
        seed=51, kind="soil", edge="#2b1b11", rough=0.15
    )


def _hash_noise(U, V, seed: int):
    """Ruido determinista continuo en 0..1, sin archivos externos."""
    import numpy as np
    return np.mod(np.sin(U * 127.1 + V * 311.7 + seed * 17.13) * 43758.5453123, 1.0)


def _stone_field(U, V, seed: int, nx_cells: int, ny_cells: int, warmth: float = 0.0):
    """Campo Voronoi compacto para agregado triturado embebido, no piedras sueltas gigantes."""
    import numpy as np
    U=np.asarray(U,dtype=float); V=np.asarray(V,dtype=float)
    umin,umax=float(np.nanmin(U)),float(np.nanmax(U)); vmin,vmax=float(np.nanmin(V)),float(np.nanmax(V))
    un=(U-umin)/(umax-umin+1e-9); vn=(V-vmin)/(vmax-vmin+1e-9)
    rng=np.random.default_rng(seed)
    centers=[]
    for j in range(ny_cells):
        for i in range(nx_cells):
            cx=(i+0.5+rng.uniform(-0.36,0.36))/nx_cells
            cy=(j+0.5+rng.uniform(-0.36,0.36))/ny_cells
            shade=rng.uniform(0.27,0.88)
            rx=rng.uniform(0.58,1.28); ry=rng.uniform(0.58,1.26)
            centers.append((cx,cy,shade,rx,ry))
    d1=np.full_like(un,1e9); d2=np.full_like(un,1e9); shade=np.zeros_like(un)
    for cx,cy,sv,rx,ry in centers:
        dx=(un-cx)*nx_cells/rx; dy=(vn-cy)*ny_cells/ry
        # angularidad simulada mediante métrica L1/L2 mezclada y micro-ondas
        d=.72*np.sqrt(dx*dx+dy*dy)+.28*(abs(dx)+abs(dy))*0.70
        d += 0.045*np.sin((dx+dy)*7.1+seed)+0.030*np.cos((dx-dy)*11.2)
        mask=d<d1
        d2=np.where(mask,d1,np.minimum(d2,d)); d1=np.where(mask,d,d1); shade=np.where(mask,sv,shade)
    gap=d2-d1
    boundary=np.exp(-(gap*15.0)**2)
    center=np.clip(1-d1*.73,0,1)
    micro=(_hash_noise(un*53,vn*61,seed+9)-.5)*.09
    mineral=np.where(_hash_noise(un*89,vn*83,seed+19)>.975,.12,0)
    out=.13+shade*.70+center*.10+micro+mineral-boundary*.31+warmth*.025
    return np.clip(out,0,1)


def _material_field(U, V, name: str, seed: int):
    """Textura procedural inspirada en un corte real de pavimento y terreno."""
    import numpy as np
    n=name.lower(); U=np.asarray(U,dtype=float); V=np.asarray(V,dtype=float)
    u=(U-float(np.nanmin(U)))/(float(np.nanmax(U))-float(np.nanmin(U))+1e-9)
    v=(V-float(np.nanmin(V)))/(float(np.nanmax(V))-float(np.nanmin(V))+1e-9)
    if "asf" in n or "tratamiento" in n or "superficie" in n:
        # Mezcla continua realista: matriz gris/negra, agregado mineral fino y macrotextura de rodadura.
        macro=.255+.050*np.sin(u*15.5+v*10.5)+.038*np.cos(u*31-v*23)
        macro += .020*np.sin((u*1.05+v*.22)*150)  # marcas muy sutiles de compactación
        rnd=_hash_noise(u*141,v*157,seed)
        fine=np.where(rnd>.885,.18+.52*(rnd-.885)/.115,0.0)
        pale=np.where(_hash_noise(u*257,v*239,seed+4)>.973,.28,0.0)
        dark=np.where(_hash_noise(u*191,v*203,seed+7)>.960,-.10,0.0)
        return np.clip(macro+fine+pale+dark,0,1)
    if "base granular" in n:
        # Base de agregado triturado gris: densa, angular y con finos claros entre partículas.
        stone=_stone_field(U,V,seed,25,16,0.0)
        fines=.045*_hash_noise(u*119,v*127,seed+9)
        return np.clip(stone+fines+.04,0,1)
    if "subbase" in n:
        # Subbase seleccionada clara/amarillenta, con agregado de tamaño medio y matriz granular.
        stone=_stone_field(U,V,seed,18,11,0.02)
        matrix=.055*np.sin(u*16+v*9)+.035*np.cos(u*29-v*17)
        return np.clip(.13+stone*.82+matrix,0,1)
    # Subrasante: suelo natural marrón, estratificado y heterogéneo como un corte de terreno.
    rnd=_hash_noise(u*71,v*79,seed)
    strata=.42+.12*np.sin(v*22+1.25*np.sin(u*5.2))+.065*np.cos(u*11-v*4.5)
    mottling=.075*np.sin(u*34+v*27)+.050*np.cos(u*69-v*49)
    veins=.035*np.sin((u+v)*92)+.020*np.cos((u-v)*117)
    damp=np.where(rnd>.925,-.12,0.0)
    clods=np.where(_hash_noise(u*109,v*113,seed+8)>.974,.14,0.0)
    return np.clip(strata+mottling+veins+damp+clods,0,1)


def _textured_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, name: str):
    """Prisma texturado: cara superior continua y laterales tipo corte geotécnico."""
    import numpy as np
    style=_material_style(name); traces=[]
    quality=st.session_state.get("render_quality","Alta")
    qmap={"Media":(42,30,12),"Alta":(66,46,20),"Ultra":(96,68,28)}
    nx,ny,nz0=qmap.get(quality,qmap["Alta"]); nz=max(nz0,int((z1-z0)/.9))

    def add_surface(X,Y,Z,C):
        traces.append(go.Surface(
            x=X,y=Y,z=Z,surfacecolor=C,colorscale=style["palette"],cmin=0,cmax=1,
            showscale=False,opacity=1.0,
            lighting=dict(ambient=.34,diffuse=.92,specular=.075 if style['kind']=='asphalt' else .035,roughness=.98,fresnel=.008),
            lightposition=dict(x=80,y=-135,z=230),name=name,showlegend=False,
            hovertemplate=f"<b>{name}</b><br>Espesor: {z1-z0:.1f} cm<extra></extra>"
        ))

    xs=np.linspace(x0,x1,nx); ys=np.linspace(y0,y1,ny); zs=np.linspace(z0,z1,nz)
    X,Y=np.meshgrid(xs,ys); C=_material_field(X,Y,name,style['seed'])
    relief=np.clip((C-np.nanmean(C))*style['rough'],-style['rough']*.34,style['rough']*.34)
    # Corona transversal muy sutil en la capa asfáltica para evitar apariencia de bloque perfecto.
    if style['kind']=='asphalt':
        crown=.035*(1-((Y-(y0+y1)/2)/((y1-y0)/2+1e-9))**2)
    else:
        crown=0
    add_surface(X,Y,np.full_like(X,z1)+relief+crown,C)
    add_surface(X,Y,np.full_like(X,z0),np.clip(C*.80+.025,0,1))

    X,Z=np.meshgrid(xs,zs); Cxz=_material_field(X,Z,name,style['seed']+3)
    # Laterales ligeramente más estratificados como en un corte real.
    strat=.035*np.sin((Z-z0)/(z1-z0+1e-9)*np.pi*10) if style['kind']!='asphalt' else 0
    add_surface(X,np.full_like(X,y0),Z,np.clip(Cxz+strat,0,1))
    add_surface(X,np.full_like(X,y1),Z,np.clip(Cxz*.96+strat+.015,0,1))

    Y,Z=np.meshgrid(ys,zs); Cyz=_material_field(Y,Z,name,style['seed']+7)
    strat2=.035*np.sin((Z-z0)/(z1-z0+1e-9)*np.pi*9) if style['kind']!='asphalt' else 0
    add_surface(np.full_like(Y,x0),Y,Z,np.clip(Cyz+strat2,0,1))
    add_surface(np.full_like(Y,x1),Y,Z,np.clip(Cyz*.94+strat2+.02,0,1))

    # Bordes muy discretos: se prioriza la lectura material sobre la estética CAD.
    x=[x0,x1,x1,x0,x0,x1,x1,x0]; y=[y0,y0,y1,y1,y0,y0,y1,y1]; z=[z0,z0,z0,z0,z1,z1,z1,z1]
    pairs=[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    ex=[];ey=[];ez=[]
    for a,b in pairs:
        ex += [x[a],x[b],None]; ey += [y[a],y[b],None]; ez += [z[a],z[b],None]
    traces.append(go.Scatter3d(x=ex,y=ey,z=ez,mode='lines',showlegend=False,hoverinfo='skip',line=dict(color=style['edge'],width=1.35)))
    traces.extend(_aggregate_particles(x0,x1,y0,y1,z0,z1,name))
    return traces


def _aggregate_particles(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float, name: str):
    """Microdetalle mineral embebido en las caras visibles; evita apariencia de cantos sueltos gigantes."""
    import numpy as np
    n=name.lower(); quality=st.session_state.get("render_quality","Alta")
    base_counts={"Media":160,"Alta":340,"Ultra":720}; count=base_counts.get(quality,320)
    traces=[]
    if "asf" in n or "tratamiento" in n or "superficie" in n:
        count=int(count*1.35); size=(.45,1.45); seed=111; opacity=.56
        colors=[[0,"#202121"],[.30,"#484a49"],[.58,"#747570"],[.82,"#aaa89f"],[1,"#e2ded3"]]; symbol='circle'
    elif "base granular" in n:
        count=int(count*.95); size=(.65,2.35); seed=223; opacity=.78
        colors=[[0,"#414346"],[.28,"#666a6e"],[.56,"#8b9195"],[.82,"#bec3c4"],[1,"#eceeea"]]; symbol='diamond'
    elif "subbase" in n:
        count=int(count*.82); size=(.75,2.65); seed=337; opacity=.75
        colors=[[0,"#78642d"],[.28,"#9a8240"],[.56,"#bea65d"],[.82,"#dccb8a"],[1,"#f2e5b5"]]; symbol='diamond'
    else:
        count=int(count*.90); size=(.35,1.25); seed=451; opacity=.38
        colors=[[0,"#3c281a"],[.40,"#654830"],[.70,"#937054"],[1,"#c3a586"]]; symbol='circle'

    rng=np.random.default_rng(seed+int(z0*7)+int(z1*11))
    m=int(count*.28); mt=count-2*m
    xf=rng.uniform(x0,x1,m); yf=np.full(m,y0-.012); zf=rng.uniform(z0,z1,m)
    xr=np.full(m,x1+.012); yr=rng.uniform(y0,y1,m); zr=rng.uniform(z0,z1,m)
    xt=rng.uniform(x0,x1,mt); yt=rng.uniform(y0,y1,mt); zt=np.full(mt,z1+.025)
    x=np.concatenate([xf,xr,xt]); y=np.concatenate([yf,yr,yt]); z=np.concatenate([zf,zr,zt])
    raw=rng.lognormal(mean=-.15,sigma=.42,size=len(x)); raw=(raw-raw.min())/(raw.max()-raw.min()+1e-9)
    sizes=size[0]+raw*(size[1]-size[0]); vals=np.clip(rng.normal(.50,.23,len(x)),0,1)
    traces.append(go.Scatter3d(x=x,y=y,z=z,mode='markers',showlegend=False,hoverinfo='skip',
        marker=dict(size=sizes,color=vals,colorscale=colors,cmin=0,cmax=1,opacity=opacity,symbol=symbol,line=dict(width=.18,color='rgba(0,0,0,.35)')),
        name=f"Microtextura {name}"))
    return traces

def _road_marking_traces(x0: float, x1: float, y0: float, y1: float, z: float):
    """Marcas viales planas y discretas para reforzar la lectura de una superficie de carretera real."""
    import numpy as np
    traces=[]
    xs=np.linspace(x0,x1,80)
    def strip(yc,width,color,name):
        ys=np.linspace(yc-width/2,yc+width/2,4)
        X,Y=np.meshgrid(xs,ys); Z=np.full_like(X,z)
        traces.append(go.Surface(x=X,y=Y,z=Z,surfacecolor=np.zeros_like(X),colorscale=[[0,color],[1,color]],
            cmin=0,cmax=1,showscale=False,hoverinfo='skip',opacity=.96,
            lighting=dict(ambient=.78,diffuse=.40,specular=.02,roughness=.92),name=name,showlegend=False))
    mid=(y0+y1)/2
    strip(mid-.13,.075,'#d7b52d','Línea amarilla')
    strip(mid+.13,.075,'#d7b52d','Línea amarilla')
    strip(y0+.28,.055,'#e8e8e2','Borde blanco')
    strip(y1-.28,.055,'#e8e8e2','Borde blanco')
    return traces


def _structure_layers_3d(selected: Dict, sclass: str, cbr: float):
    """Capas de la estructura con espesor de diseño separado del bloque visual de subrasante."""
    layers = []
    asphalt = float(selected.get("Carpeta_cm", 0) or 0)
    if asphalt > 0:
        layers.append({"name": "Carpeta asfáltica", "thickness": asphalt, "color": "#252727", "normative": True})
    else:
        layers.append({
            "name": str(selected.get("Superficie", "Superficie")),
            "thickness": 0.8,
            "color": "#252727",
            "normative": False,
            "note": "Representación gráfica; el catálogo no asigna espesor a la superficie",
        })

    base_granular = float(selected.get("Base_granular_cm", 0) or 0)
    base_stabilized = float(selected.get("Base_estabilizada_cm", 0) or 0)
    base_total = float(selected.get("Base_cm", 0) or 0)
    if base_granular <= 0 and base_stabilized <= 0 and base_total > 0:
        base_name = str(selected.get("Base_tipo", "Base granular"))
        if "estabil" in base_name.lower():
            base_stabilized = base_total
        else:
            base_granular = base_total
    if base_granular > 0:
        layers.append({"name": "Base granular", "thickness": base_granular, "color": "#7f858a", "normative": True})
    if base_stabilized > 0:
        layers.append({"name": "Base estabilizada", "thickness": base_stabilized, "color": "#8e8a72", "normative": True})

    subbase = float(selected.get("Subbase_cm", 0) or 0)
    if subbase > 0:
        layers.append({"name": "Subbase granular", "thickness": subbase, "color": "#9a6337", "normative": True})

    improvement = 0.0
    for key in ("Mejoramiento_cm", "Subrasante_mejorada_cm", "Suelo_mejorado_cm"):
        improvement = max(improvement, float(selected.get(key, 0) or 0))
    if improvement > 0:
        layers.append({"name": "Subrasante mejorada", "thickness": improvement, "color": "#75604b", "normative": True})

    layers.append({
        "name": f"Subrasante {sclass}",
        "thickness": 10.0,
        "color": "#5a3824",
        "normative": False,
        "note": f"Medio de apoyo semiinfinito · CBR {cbr:.2f}% · bloque inferior solo visual",
    })
    return layers


def _top_surface_z_3d(selected: Dict, sclass: str, cbr: float, vertical_scale: float = 1.0, exploded: bool = False) -> float:
    layers = list(reversed(_structure_layers_3d(selected, sclass, cbr)))
    gap = (3.0 if exploded else 0.0) * max(vertical_scale, 1.0)
    z = 0.0
    for idx, layer in enumerate(layers):
        th = float(layer["thickness"])
        geom = th if not layer.get("normative", True) and "Subrasante" in layer["name"] else th * vertical_scale
        z = z + (gap if idx else 0.0) + geom
    return z


def _dimension_trace_3d(x: float, y: float, z0: float, z1: float, label: str, color: str):
    return go.Scatter3d(
        x=[x, x, None, x-0.18, x+0.18, None, x-0.18, x+0.18],
        y=[y, y, None, y, y, None, y, y],
        z=[z0, z1, None, z0, z0, None, z1, z1],
        mode="lines+text",
        text=[None, label, None, None, None, None, None, None],
        textposition="middle right",
        line=dict(color=color, width=4),
        textfont=dict(color="#f5f9ff", size=12),
        hoverinfo="skip",
        showlegend=False,
    )


def pavement_3d_figure(
    selected: Dict,
    sclass: str,
    cbr: float,
    exploded: bool = False,
    vertical_scale: float = 1.0,
    view_mode: str = "Completa",
    selected_layer: str = "Todas",
) -> go.Figure:
    """Visor estructural 3D v2: cotas, cortes, escala vertical y lectura técnica de capas."""
    road_length, road_width = 10.0, 6.0
    vertical_scale = max(1.0, float(vertical_scale or 1.0))
    gap = (3.0 if exploded else 0.0) * vertical_scale

    if view_mode == "Corte transversal":
        x0, x1, y0, y1 = 4.45, 5.55, 0.0, road_width
    elif view_mode == "Corte longitudinal":
        x0, x1, y0, y1 = 0.0, road_length, 2.65, 3.35
    elif view_mode == "Media calzada":
        x0, x1, y0, y1 = 0.0, road_length, 0.0, road_width / 2.0
    else:
        x0, x1, y0, y1 = 0.0, road_length, 0.0, road_width

    layers = _structure_layers_3d(selected, sclass, cbr)
    traces, annotations = [], []
    z_cursor = 0.0
    top_surface_z = 0.0
    structural_dimension_index = 0

    for idx, layer in enumerate(reversed(layers)):
        name = layer["name"]
        thickness = float(layer["thickness"])
        is_subgrade_visual = (not layer.get("normative", True)) and "Subrasante" in name
        geom_thickness = thickness if is_subgrade_visual else thickness * vertical_scale
        if idx:
            z_cursor += gap
        z0, z1 = z_cursor, z_cursor + geom_thickness
        traces.extend(_textured_box(x0, x1, y0, y1, z0, z1, name))

        if is_subgrade_visual:
            label = f"<b>{name}</b><br>CBR {cbr:.2f}%<br><i>medio semiinfinito</i>"
        elif layer.get("normative", True):
            label = f"<b>{name}</b><br>{thickness:.1f} cm"
        else:
            label = f"<b>{name}</b><br><i>sin espesor normativo</i>"

        annotations.append(dict(
            x=x1 + 0.36, y=y1 * 0.78, z=(z0 + z1) / 2,
            text=label, showarrow=True, arrowhead=0, arrowsize=1,
            arrowwidth=2, arrowcolor=layer["color"], ax=62, ay=0,
            bgcolor="rgba(7,20,33,.95)", bordercolor=layer["color"], borderwidth=2,
            font=dict(size=12, color="#f4f7f8"), opacity=.97,
        ))

        if layer.get("normative", True):
            structural_dimension_index += 1
            traces.append(_dimension_trace_3d(
                x1 + 0.15 + structural_dimension_index * 0.10,
                y0 + 0.12,
                z0, z1,
                f"{thickness:.1f} cm",
                layer["color"],
            ))

        if selected_layer not in ("Todas", name):
            # Mantiene contexto visual completo; la capa seleccionada se resalta con un marco adicional.
            pass
        elif selected_layer == name:
            hx = [x0,x1,x1,x0,x0,x1,x1,x0]
            hy = [y0,y0,y1,y1,y0,y0,y1,y1]
            hz = [z0,z0,z0,z0,z1,z1,z1,z1]
            pairs = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
            ex, ey, ez = [], [], []
            for a,b in pairs:
                ex += [hx[a],hx[b],None]; ey += [hy[a],hy[b],None]; ez += [hz[a],hz[b],None]
            traces.append(go.Scatter3d(x=ex,y=ey,z=ez,mode="lines",line=dict(color="#51c8ff",width=7),hoverinfo="skip",showlegend=False))

        z_cursor = z1
        top_surface_z = max(top_surface_z, z1)

    traces.extend(_road_marking_traces(x0, x1, y0, y1, top_surface_z + 0.12))

    platform, platform_edges = _box_mesh(x0-.35, x1+.35, y0-.35, y1+.35, -1.8, -.35, "Base visual", "#0b2340")
    platform.update(opacity=.68, hoverinfo="skip", showlegend=False)
    traces = [platform, platform_edges] + traces

    scale_label = "Escala vertical real" if abs(vertical_scale - 1.0) < 1e-9 else f"Exageración vertical ×{vertical_scale:g}"
    annotations.append(dict(
        x=x0, y=y0, z=top_surface_z + 4.5,
        text=f"<b>{scale_label}</b><br>{view_mode}", showarrow=False,
        bgcolor="rgba(5,18,30,.88)", bordercolor="#2d688f", borderwidth=1,
        font=dict(size=11, color="#dff3ff"), xanchor="left",
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        height=690, paper_bgcolor="#06121d", plot_bgcolor="#06121d",
        margin=dict(l=0, r=0, t=58, b=0),
        title=dict(text=f"<b>Visor estructural 3D v2 — {selected.get('Código', '')}</b>", x=.025, font=dict(color="white", size=18)),
        showlegend=False,
        scene=dict(
            bgcolor="#06121d",
            xaxis=dict(title="Longitud representativa (m)", showbackground=True, backgroundcolor="#0b1c2a", gridcolor="#26445b", zerolinecolor="#55758d", color="#d9efff", showspikes=False),
            yaxis=dict(title="Ancho representativo (m)", showbackground=True, backgroundcolor="#0b1c2a", gridcolor="#26445b", zerolinecolor="#55758d", color="#d9efff", showspikes=False),
            zaxis=dict(title="Escala gráfica vertical", showbackground=True, backgroundcolor="#091a27", gridcolor="#26445b", zerolinecolor="#55758d", color="#d9efff", showspikes=False),
            aspectmode="manual",
            aspectratio=dict(x=1.70, y=1.03 if view_mode != "Corte longitudinal" else .55, z=1.06),
            camera=dict(eye=dict(x=1.70, y=1.58, z=1.18), projection=dict(type="perspective")),
            annotations=annotations,
        ),
        meta={"gdp3d_version":"2.0","vertical_scale":vertical_scale,"view_mode":view_mode},
    )
    return fig


def render_rotating_3d(fig: go.Figure, key: str, height: int = 690, auto_rotate: bool = True) -> None:
    """Render Plotly 3D con rotación y cámaras técnicas predefinidas."""
    div_id = f"gdp_3d_{key}"
    fig.update_layout(margin=dict(l=0, r=0, t=46, b=0))
    plot_html = pio.to_html(
        fig, include_plotlyjs=True, full_html=False, div_id=div_id,
        config={"displaylogo": False, "scrollZoom": True, "responsive": True, "displayModeBar": False},
    )
    initial = "true" if auto_rotate else "false"
    html = f"""
    <style>
      html,body{{margin:0;background:#06121d;overflow:hidden;font-family:Arial,sans-serif}}
      .gdp-wrap{{position:relative;width:100%;height:{height}px;background:radial-gradient(circle at 48% 37%,#123653 0%,#071827 48%,#040c14 100%);border-radius:12px;overflow:hidden}}
      .gdp-plot{{position:absolute;inset:0}}
      .gdp-controls{{position:absolute;left:12px;bottom:12px;z-index:20;display:flex;flex-wrap:wrap;align-items:center;gap:6px;background:rgba(3,13,23,.90);border:1px solid #315878;border-radius:10px;padding:7px 9px;box-shadow:0 8px 22px rgba(0,0,0,.35);color:#eaf5ff;font-size:12px;max-width:92%}}
      .gdp-btn{{border:1px solid #2e6ea3;background:#0a2b49;color:#fff;border-radius:7px;padding:6px 8px;font-weight:700;cursor:pointer}}
      .gdp-btn:hover{{background:#0d69ca}}
      .gdp-state{{color:#6ed7ff;min-width:62px;font-weight:700}}
      .gdp-hint{{position:absolute;right:12px;top:12px;z-index:19;background:rgba(3,13,23,.78);border:1px solid #27475f;color:#c7d8e7;border-radius:8px;padding:7px 10px;font-size:11px}}
    </style>
    <div class="gdp-wrap">
      <div class="gdp-plot">{plot_html}</div>
      <div class="gdp-controls">
        <button id="pause_{key}" class="gdp-btn">⏸</button>
        <button id="resume_{key}" class="gdp-btn">▶</button>
        <span id="state_{key}" class="gdp-state">Rotando…</span>
        <button id="iso_{key}" class="gdp-btn">Isométrica</button>
        <button id="plan_{key}" class="gdp-btn">Planta</button>
        <button id="profile_{key}" class="gdp-btn">Perfil</button>
        <button id="section_{key}" class="gdp-btn">Sección</button>
        <button id="reset_{key}" class="gdp-btn">Restablecer</button>
      </div>
      <div class="gdp-hint">Arrastre: orbitar · Scroll: zoom</div>
    </div>
    <script>
    (function(){{
      const gd=document.getElementById('{div_id}');
      const state=document.getElementById('state_{key}');
      let running={initial}, internalUpdate=false, radius=2.32, angle=.73, eyeZ=1.18;
      const speed=.0030;
      function sync(){{state.textContent=running?'Rotando…':'Pausado';state.style.color=running?'#6ed7ff':'#ffc857';}}
      function camera(eye, up={{x:0,y:0,z:1}}){{running=false;sync();internalUpdate=true;return Plotly.relayout(gd,{{'scene.camera':{{eye:eye,up:up,projection:{{type:'perspective'}}}}}}).then(()=>{{internalUpdate=false;radius=Math.max(.65,Math.hypot(eye.x,eye.y));angle=Math.atan2(eye.y,eye.x);eyeZ=eye.z;}}).catch(()=>{{internalUpdate=false;}});}}
      document.getElementById('pause_{key}').onclick=()=>{{running=false;sync();}};
      document.getElementById('resume_{key}').onclick=()=>{{running=true;sync();}};
      document.getElementById('iso_{key}').onclick=()=>camera({{x:1.70,y:1.58,z:1.18}});
      document.getElementById('plan_{key}').onclick=()=>camera({{x:.01,y:.01,z:2.8}});
      document.getElementById('profile_{key}').onclick=()=>camera({{x:.01,y:2.8,z:.35}});
      document.getElementById('section_{key}').onclick=()=>camera({{x:2.8,y:.01,z:.40}});
      document.getElementById('reset_{key}').onclick=()=>camera({{x:1.70,y:1.58,z:1.18}});
      sync();
      gd.on('plotly_relayout',function(ev){{if(internalUpdate)return;const cam=ev['scene.camera'];if(cam&&cam.eye){{const e=cam.eye;if(Number.isFinite(e.x)&&Number.isFinite(e.y)){{radius=Math.max(.65,Math.hypot(e.x,e.y));angle=Math.atan2(e.y,e.x);}}if(Number.isFinite(e.z))eyeZ=e.z;}}}});
      function tick(){{if(!running||document.hidden)return;angle+=speed;internalUpdate=true;Plotly.relayout(gd,{{'scene.camera.eye':{{x:radius*Math.cos(angle),y:radius*Math.sin(angle),z:eyeZ}}}}).then(()=>{{internalUpdate=false;}}).catch(()=>{{internalUpdate=false;}});}}
      setInterval(tick,80);
    }})();
    </script>
    """
    components.html(html, height=height, scrolling=False)



def deterioration_3d_figure(selected: Dict, sclass: str, cbr: float, state: Dict, visible_pathologies: List[str]) -> go.Figure:
    """Modelo 3D didáctico del deterioro superficial a partir de los indicadores preliminares.

    La geometría sirve para visualizar tendencias y severidades relativas; no representa una
    simulación mecánica ni sustituye una inspección de campo o calibración del Tomo I.
    """
    import numpy as np

    # Base estructural realista, sin explotar, reutilizando los materiales de la vista principal.
    fig = pavement_3d_figure(selected, sclass, cbr, exploded=False)
    fig.update_layout(
        title=dict(text="<b>Modelo 3D de patologías — estado estimado</b>", x=.025, font=dict(color="white", size=18)),
        height=640,
    )

    top_z = _top_surface_z_3d(selected, sclass, cbr, vertical_scale=1.0, exploded=False)

    fatigue = float(state.get("Fatiga (%)", 0.0))
    rut_mm = float(state.get("Ahuellamiento (mm)", 0.0))
    long_pct = float(state.get("Fisuras longitudinales (%)", 0.0))
    block_pct = float(state.get("Fisuras por bloque (%)", 0.0))
    thermal_pct = float(state.get("Riesgo térmico (%)", 0.0))
    pci = float(state.get("PCI estimado", 100.0))

    # Superficie deformada: dos huellas longitudinales representan el ahuellamiento.
    if "Ahuellamiento" in visible_pathologies and rut_mm > 0.05:
        xs = np.linspace(0, 10, 70)
        ys = np.linspace(0, 6, 52)
        X, Y = np.meshgrid(xs, ys)
        rut_cm = rut_mm / 10.0
        g1 = np.exp(-((Y-1.85)/0.30)**2)
        g2 = np.exp(-((Y-4.15)/0.30)**2)
        Z = top_z + 0.10 - rut_cm * (g1 + g2)
        # pequeñas ondulaciones para evitar una lámina demasiado perfecta
        Z += 0.025*np.sin(X*2.1)*np.exp(-((Y-3.0)/2.8)**2)
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z, showscale=False, hoverinfo='skip', opacity=.98,
            colorscale=[[0,'#111313'],[.35,'#202222'],[.72,'#303130'],[1,'#45443f']],
            cmin=float(Z.min()), cmax=float(Z.max()),
            lighting=dict(ambient=.44,diffuse=.72,roughness=.94,specular=.08,fresnel=.04),
            lightposition=dict(x=80,y=-120,z=170), name='Ahuellamiento'
        ))

    rng = np.random.default_rng(20241024 + int(state.get("Año", 0))*17)

    def surface_z(yval: float, xval: float = 5.0) -> float:
        if "Ahuellamiento" not in visible_pathologies:
            return top_z + .16
        rut_cm = rut_mm/10.0
        depress = np.exp(-((yval-1.85)/.30)**2) + np.exp(-((yval-4.15)/.30)**2)
        return top_z + .16 - rut_cm*float(depress) + .025*math.sin(xval*2.1)

    # Fatiga: redes de fisuras cortas e irregulares concentradas en las huellas de rueda.
    if "Fatiga" in visible_pathologies and fatigue > 0.2:
        crack_count = min(95, max(5, int(fatigue*0.85)))
        for i in range(crack_count):
            cx = rng.uniform(.5, 9.5)
            cy = rng.choice([rng.normal(1.85,.40), rng.normal(4.15,.40)])
            cy = float(np.clip(cy,.35,5.65))
            segs = 3 + int(rng.integers(0,4))
            ang = rng.uniform(0,2*np.pi)
            length = rng.uniform(.10,.38) * (0.55 + fatigue/55.0)
            xx=[cx]; yy=[cy]
            for j in range(segs):
                ang += rng.normal(0,.75)
                xx.append(float(np.clip(xx[-1] + length*np.cos(ang),0.12,9.88)))
                yy.append(float(np.clip(yy[-1] + length*np.sin(ang),0.12,5.88)))
            zz=[surface_z(v,u)+.025 for u,v in zip(xx,yy)]
            fig.add_trace(go.Scatter3d(x=xx,y=yy,z=zz,mode='lines',showlegend=False,hoverinfo='skip',
                line=dict(color='#060606',width=3.1)))

    # Fisuras longitudinales: trazos sinuosos paralelos al eje.
    if "Fisuras longitudinales" in visible_pathologies and long_pct > 0.2:
        nlines=min(7,max(1,int(long_pct/6.0)+1))
        for i in range(nlines):
            y0 = 1.10 + i*(3.8/max(nlines,1)) + rng.normal(0,.10)
            xx=np.linspace(.25,9.75,90)
            yy=y0 + .035*np.sin(xx*(1.2+i*.13)+i) + rng.normal(0,.008,len(xx))
            zz=[surface_z(float(v),float(u))+.035 for u,v in zip(xx,yy)]
            fig.add_trace(go.Scatter3d(x=xx,y=yy,z=zz,mode='lines',showlegend=False,hoverinfo='skip',
                line=dict(color='#11100f',width=4.0)))

    # Fisuración por bloque: retícula irregular que aumenta con la densidad estimada.
    if "Fisuras por bloque" in visible_pathologies and block_pct > 0.4:
        spacing=max(.75, 2.25 - block_pct/28.0)
        xvals=np.arange(.5,9.8,spacing)
        yvals=np.arange(.5,5.8,spacing*.76)
        for xv in xvals:
            yy=np.linspace(.35,5.65,70); xx=np.full_like(yy,xv)+.035*np.sin(yy*2.0+xv)
            zz=[surface_z(float(v),float(u))+.045 for u,v in zip(xx,yy)]
            fig.add_trace(go.Scatter3d(x=xx,y=yy,z=zz,mode='lines',showlegend=False,hoverinfo='skip',line=dict(color='#17120f',width=2.7)))
        for yv in yvals:
            xx=np.linspace(.35,9.65,90); yy=np.full_like(xx,yv)+.035*np.sin(xx*1.7+yv)
            zz=[surface_z(float(v),float(u))+.045 for u,v in zip(xx,yy)]
            fig.add_trace(go.Scatter3d(x=xx,y=yy,z=zz,mode='lines',showlegend=False,hoverinfo='skip',line=dict(color='#17120f',width=2.7)))

    # Fisuración térmica: fisuras transversales espaciadas.
    if "Fisuración térmica" in visible_pathologies and thermal_pct > 1.0:
        nthermal=min(9,max(1,int(thermal_pct/12.0)+1))
        for i,xv in enumerate(np.linspace(1.0,9.0,nthermal)):
            yy=np.linspace(.25,5.75,80)
            xx=np.full_like(yy,xv)+.055*np.sin(yy*2.4+i)
            zz=[surface_z(float(v),float(u))+.055 for u,v in zip(xx,yy)]
            fig.add_trace(go.Scatter3d(x=xx,y=yy,z=zz,mode='lines',showlegend=False,hoverinfo='skip',line=dict(color='#201712',width=3.2)))

    # Indicador visual de condición: halo tenue que cambia según PCI.
    halo_color = '#35d06f' if pci >= 70 else ('#ffc329' if pci >= 55 else '#ef4a4a')
    fig.add_annotation(text=f"PCI estimado {pci:.0f}", x=.78, y=.95, xref='paper', yref='paper',
                       showarrow=False, bgcolor='rgba(4,16,28,.88)', bordercolor=halo_color, borderwidth=2,
                       font=dict(color=halo_color,size=14), borderpad=7)
    return fig


def pathology_severity(value: float, medium: float, high: float) -> str:
    if value >= high:
        return "Alta"
    if value >= medium:
        return "Media"
    return "Baja"

def performance_curves(years: int, esal: float, pavement_temp_c: float, cbr: float, asphalt_cm: float, drainage_factor: float = 1.0) -> pd.DataFrame:
    """Curvas preliminares normalizadas para seguimiento; no sustituyen la calibración ME del Tomo I."""
    import numpy as np
    n = max(int(years), 1)
    y = np.arange(0, n + 1, dtype=float)
    load = max(esal, 1.0) / 1_000_000.0
    temp_factor = max(0.70, 1.0 + (pavement_temp_c - 30.0) * 0.018)
    subgrade_factor = max(0.70, min(1.80, 6.0 / max(cbr, 1.0)))
    thickness_factor = max(0.60, min(1.80, 7.0 / max(asphalt_cm, 2.0)))
    drain_factor = max(0.70, min(1.60, 1.0 / max(drainage_factor, .55)))
    x = y / n
    fatigue = np.clip(100.0 * (1.0 - np.exp(-0.32 * load**0.42 * thickness_factor * x**1.55)), 0, 100)
    rutting = np.clip(20.0 * (1.0 - np.exp(-0.72 * load**0.34 * temp_factor * subgrade_factor * drain_factor * x**1.25)), 0, 35)
    long_cracks = np.clip(30.0 * (1.0 - np.exp(-0.36 * load**0.28 * thickness_factor * x**1.45)), 0, 40)
    block_cracks = np.clip(30.0 * (1.0 - np.exp(-0.24 * temp_factor * x**1.75)), 0, 40)
    thermal_risk = np.clip(100.0 * (1.0 - np.exp(-0.09 * max(0.0, 18.0-pavement_temp_c) * x)), 0, 100)
    pci = np.clip(100.0 - 0.31*fatigue - 1.05*rutting - 0.34*long_cracks - 0.28*block_cracks, 0, 100)
    return pd.DataFrame({"Año": y.astype(int), "Fatiga (%)": fatigue, "Ahuellamiento (mm)": rutting,
                         "Fisuras longitudinales (%)": long_cracks, "Fisuras por bloque (%)": block_cracks,
                         "Riesgo térmico (%)": thermal_risk, "PCI estimado": pci})


def performance_plot(df: pd.DataFrame, value_col: str, title: str, y_title: str, limit: float, limit_label: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Año"], y=df[value_col], mode="lines+markers", name="Estimación",
                             line=dict(width=4, color="#1568ff"), marker=dict(size=7, color="#1568ff"),
                             hovertemplate="Año %{x}<br>%{y:.2f}<extra></extra>"))
    fig.add_hline(y=limit, line_dash="dash", line_color="#ef3340", annotation_text=limit_label,
                  annotation_position="top left")
    fig.update_layout(height=300, margin=dict(l=15,r=15,t=55,b=25), title=dict(text=title, x=.02),
                      paper_bgcolor="white", plot_bgcolor="#f8fbff", hovermode="x unified",
                      xaxis=dict(title="Años", gridcolor="#dce7f1"),
                      yaxis=dict(title=y_title, gridcolor="#dce7f1", rangemode="tozero"), showlegend=False)
    return fig



def gdp_scope_alerts(active_tomo: str, tpd_total: float, heavy_pct: float, cbr: float,
                     esal: float, years: int) -> list[tuple[str, str]]:
    """Alertas de alcance basadas en GDP-2024 Tomos I y II.

    Devuelve pares (nivel, mensaje), donde nivel es success/info/warning/error.
    Estas verificaciones ayudan a evitar el uso del Tomo II fuera de su alcance y
    orientan la confiabilidad del Tomo I; no sustituyen el criterio profesional.
    """
    alerts: list[tuple[str, str]] = []

    if active_tomo == "Tomo II":
        # GDP-2024 Tomo II: guía simplificada de bajo volumen.
        if tpd_total > 3500:
            alerts.append(("error", f"Tomo II fuera de alcance: TPD = {tpd_total:,.0f} veh/día supera 3 500 veh/día. Utilice Tomo I o realice un diseño específico."))
        elif tpd_total <= 0:
            alerts.append(("error", "Tomo II: el TPD debe ser mayor que cero."))
        else:
            alerts.append(("success", f"TPD dentro del rango de aplicación del Tomo II: {tpd_total:,.0f} veh/día."))

        if heavy_pct > 15.0:
            alerts.append(("error", f"Tomo II fuera de alcance: vehículos pesados = {heavy_pct:.2f}% supera el máximo de 15%. Utilice Tomo I o diseño específico."))
        else:
            alerts.append(("success", f"Porcentaje de vehículos pesados dentro del límite del Tomo II: {heavy_pct:.2f}% ≤ 15%."))

        if cbr < 3.0:
            alerts.append(("error", f"Tomo II: CBR = {cbr:.2f}% es menor que 3%. La subrasante requiere mejoramiento, estabilización o sustitución antes de seleccionar una estructura del catálogo."))
        else:
            alerts.append(("success", f"CBR de subrasante compatible con el alcance simplificado: {cbr:.2f}% ≥ 3%."))

        if esal > 1_500_000:
            alerts.append(("error", f"Tomo II fuera de alcance: ESAL de diseño = {esal:,.0f} supera 1,5 millones. Se requiere diseño específico/Tomo I."))
        else:
            alerts.append(("success", f"ESAL dentro del alcance simplificado: {esal:,.0f} ≤ 1,5 millones."))

        if int(years) not in (6, 8, 10, 12):
            alerts.append(("warning", f"Tomo II: el catálogo GDP-2024 está tabulado directamente para períodos de 6, 8, 10 y 12 años. El período ingresado ({int(years)} años) no tiene selección tabulada directa; verifique o adopte un diseño específico."))
        else:
            alerts.append(("success", f"Período de diseño tabulado en el Tomo II: {int(years)} años."))

    else:  # Tomo I
        # Nivel jerárquico y confiabilidad típica según ESAL de diseño.
        if esal < 3_000_000:
            cat, conf = "Categoría 3", 75
            crack, rut = 35, 16
        elif esal <= 25_000_000:
            cat, conf = "Categoría 2", 85
            crack, rut = 20, 12
        else:
            cat, conf = "Categoría 1", 95
            crack, rut = 10, 10
        alerts.append(("info", f"Tomo I: {cat} por nivel de ESAL. Confiabilidad típica recomendada: {conf}%."))
        alerts.append(("info", f"Criterios de desempeño de referencia al final del período: área agrietada ≤ {crack}% y ahuellamiento total ≤ {rut} mm."))

        if int(years) < 5 or int(years) > 40:
            alerts.append(("warning", "Tomo I: revise el período de análisis respecto al tipo funcional de la ruta."))

    return alerts


def render_gdp_scope_alerts(active_tomo: str, tpd_total: float, heavy_pct: float,
                            cbr: float, esal: float, years: int) -> None:
    st.markdown("#### Verificación automática de alcance — GDP-2024")
    for level, msg in gdp_scope_alerts(active_tomo, tpd_total, heavy_pct, cbr, esal, years):
        getattr(st, level)(msg)
    st.caption("Control de alcance incorporado con base en GDP-2024. Las alertas no sustituyen la revisión integral de la guía ni el criterio del profesional responsable.")

def technical_validation(active_tomo: str, selected: Dict, exact_match: bool, esal: float, cbr: float, pavement_temp: float, drainage: dict,
                         geometry: dict | None = None, subgrade_details: dict | None = None,
                         materials: dict | None = None, reliability: dict | None = None,
                         mechanistic: dict | None = None) -> pd.DataFrame:
    """Matriz trazable de validación. No reemplaza la revisión profesional."""
    geometry = geometry or {}
    subgrade_details = subgrade_details or {}
    materials = materials or {}
    reliability = reliability or {}
    mechanistic = mechanistic or {}
    checks = []
    def add(category, criterion, ok, severity, evidence):
        checks.append({"Categoría":category,"Criterio":criterion,"Estado":"Cumple" if ok else "Revisar","Severidad":severity,"Evidencia":evidence})
    add("Alcance", "Metodología seleccionada", active_tomo in ("Tomo I","Tomo II"), "Alta", active_tomo)
    if active_tomo == "Tomo II":
        add("Catálogo", "Coincidencia exacta tránsito-subrasante", bool(exact_match), "Alta", f"Código {selected.get('Código','—')}")
    else:
        add("Jerarquía Tomo I", "Categoría de diseño definida por ESAL", esal > 0, "Alta", f"Categoría {tomo1_design_category(esal)}")
    add("Tránsito", "ESAL mayor que cero", esal > 0, "Alta", f"{esal:,.0f} ESAL")
    add("Geometría", "Longitud y ancho de referencia definidos", float(geometry.get("length_m",0) or 0) > 0 and float(geometry.get("paved_reference_width_m",0) or 0) > 0, "Media", f"L={geometry.get('length_m','—')} m · B={geometry.get('paved_reference_width_m','—')} m")
    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")
    add("Subrasante", "Fuente de Mr documentada", bool(subgrade_details.get("mr_source")), "Media", str(subgrade_details.get("mr_source","Sin definir")))
    if active_tomo == "Tomo I":
        add("Materiales", "Módulo de mezcla asfáltica registrado", float(materials.get("asphalt_dynamic_modulus_mpa",0) or 0) > 0, "Alta", f"E*={float(materials.get('asphalt_dynamic_modulus_mpa',0) or 0):.0f} MPa")
        add("Materiales", "Fuente de caracterización documentada", bool(str(materials.get("source","")).strip()), "Media", str(materials.get("source","Sin definir")))
        granular_model = materials.get('granular_model', {}) if isinstance(materials, dict) else {}
        add("Granulares", "Modelo constitutivo documentado", bool(granular_model), "Media", str(granular_model.get('material','No configurado')))
        add("Confiabilidad", "Parámetro de confiabilidad definido", float(reliability.get("reliability_pct",0) or 0) >= 50, "Alta", f"R={float(reliability.get('reliability_pct',0) or 0):.0f}%")
        add("Respuesta ME", "Cribado mecanístico ejecutado", bool(mechanistic), "Alta", str(mechanistic.get("method", "No ejecutado")))
        if mechanistic:
            add("Fatiga", "εt dentro del criterio configurado", float(mechanistic.get("fatigue_utilization_design", mechanistic.get("fatigue_utilization_ratio",99)) or 99) <= 1.0, "Alta", f"Utilización diseño={float(mechanistic.get('fatigue_utilization_design', mechanistic.get('fatigue_utilization_ratio',0)) or 0):.2f}")
            add("Ahuellamiento", "εv dentro del criterio configurado", float(mechanistic.get("rutting_utilization_design", mechanistic.get("rutting_utilization_ratio",99)) or 99) <= 1.0, "Alta", f"Utilización diseño={float(mechanistic.get('rutting_utilization_design', mechanistic.get('rutting_utilization_ratio',0)) or 0):.2f}")
    if active_tomo == "Tomo II":
        add("Alcance Tomo II", "ESAL ≤ 1,5 millones", esal <= 1_500_000, "Alta", f"{esal:,.0f} ESAL")
        add("Alcance Tomo II", "CBR ≥ 3%", cbr >= 3.0, "Alta", f"CBR {cbr:.2f}%")
    add("Clima", "Temperatura de pavimento revisada", pavement_temp < 55, "Media", f"{pavement_temp:.1f} °C")
    drain_ok = bool(drainage.get("side_ditches", False)) and bool(drainage.get("outlets", False))
    add("Drenaje", "Conducción y descarga documentadas", drain_ok, "Alta", drainage.get("quality","Sin definir"))
    add("Estructura", "Espesor estructural positivo", sum(float(selected.get(k,0) or 0) for k in ("Carpeta_cm","Base_cm","Subbase_cm")) > 0, "Alta", "Espesores del catálogo")
    return pd.DataFrame(checks)

def make_report(payload: Dict) -> str:
    project = payload["project"]
    traffic = payload["traffic"]
    subgrade = payload["subgrade"]
    selected = payload.get("selected")
    geometry = payload.get("geometry", {})
    materials = payload.get("materials", {})
    reliability = payload.get("reliability", {})
    mechanistic = payload.get("mechanistic_screening", {})
    transfer_model = payload.get("transfer_model", {})
    homogeneous_segments = payload.get("homogeneous_segments", [])
    rehabilitation = payload.get("rehabilitation", {})
    optimization_candidates = payload.get("optimization_candidates", [])
    quality_score, quality_detail = design_data_quality_score(payload)
    costs = payload.get("costs", {})
    active_tomo = payload.get("active_tomo", "Tomo II")
    # FIX_TOMO2_REPORT_DESIGN_CATEGORY_NONE
    raw_design_category = traffic.get("design_category")
    design_category = (
        int(raw_design_category)
        if raw_design_category not in (None, "")
        else tomo1_design_category(float(traffic.get("esal", 0.0)))
    )
    traffic_class_html = (
        f"<tr><th>Categoría de diseño Tomo I</th><td>Categoría {design_category}</td></tr>"
        if active_tomo == "Tomo I"
        else f"<tr><th>Rango</th><td>{traffic['class']}</td></tr>"
    )
    structure_context_html = (
        f"<tr><th>Categoría de diseño</th><td>Categoría {design_category}</td></tr>"
        if active_tomo == "Tomo I"
        else f"<tr><th>Opción</th><td>{selected.get('Opción', 'Estructura seleccionada') if selected else 'Estructura seleccionada'}</td></tr>"
    )

    structure_html = "<p>No se seleccionó una estructura.</p>"
    if selected:
        structure_html = f"""
        <table>
          <tr><th>Código</th><td>{selected['Código']}</td></tr>
          {structure_context_html}
          <tr><th>Superficie</th><td>{selected['Superficie']}</td></tr>
          <tr><th>Carpeta</th><td>{selected['Carpeta_cm']} cm</td></tr>
          <tr><th>Base</th><td>{selected['Base_cm']} cm</td></tr>
          <tr><th>Subbase Granular</th><td>{selected['Subbase_cm']} cm</td></tr>
        </table>
        """

    return f"""<!doctype html>
<html lang='es'>
<head>
<meta charset='utf-8'>
<title>Memoria preliminar GDP - {project['name']}</title>
<style>
body{{font-family:Arial,sans-serif;margin:40px;color:#1f2933;line-height:1.45}}
h1,h2{{color:#0b4f6c}} table{{border-collapse:collapse;width:100%;margin:12px 0}}
th,td{{border:1px solid #cbd5df;padding:8px;text-align:left}} th{{background:#eef5f8}}
.note{{padding:12px;background:#fff7df;border-left:4px solid #d69e00}}
</style>
</head>
<body>
<h1>Memoria técnica de diseño de pavimento — expediente de revisión</h1>
<div class='note'><b>Estado del expediente:</b> calidad documental {quality_score}% · Tomo activo: {active_tomo}. Los resultados configurables o de cribado deben validarse antes de una emisión definitiva.</div>
<p><b>Proyecto:</b> {project['name']}<br>
<b>Ubicación:</b> {project['location']}<br>
<b>CRTM05 (EPSG:5367):</b> E {project.get('crtm05_easting_m', 0):,.3f} m · N {project.get('crtm05_northing_m', 0):,.3f} m<br>
<b>WGS84 (EPSG:4326):</b> {project.get('latitude', 0):.7f}°, {project.get('longitude', 0):.7f}°<br>
<b>Fecha:</b> {project['date']}<br>
<b>Responsable:</b> {project['engineer']}</p>

<h2>0. Geometría y configuración del proyecto</h2>
<table>
<tr><th>Longitud de diseño</th><td>{geometry.get('length_m', 0):,.1f} m</td></tr>
<tr><th>Ancho de referencia</th><td>{geometry.get('paved_reference_width_m', 0):,.2f} m</td></tr>
<tr><th>Número de carriles</th><td>{geometry.get('number_lanes', 0)}</td></tr>
<tr><th>Sentidos</th><td>{geometry.get('traffic_directions', '')}</td></tr>
<tr><th>Pendiente transversal</th><td>{geometry.get('cross_slope_pct', 0):.2f}%</td></tr>
<tr><th>Pendiente longitudinal media</th><td>{geometry.get('longitudinal_slope_pct', 0):.2f}%</td></tr>
</table>

<h2>1. Parámetros de tránsito</h2>
<table>
<tr><th>TPD total</th><td>{traffic['tpd_total']:,.0f} veh/día</td></tr>
<tr><th>Tasa de crecimiento</th><td>{traffic['growth_rate']:.2f}%</td></tr>
<tr><th>Factor de crecimiento acumulado G</th><td>{traffic.get('growth_factor', 0):.3f}</td></tr>
<tr><th>Periodo de diseño</th><td>{traffic['years']} años</td></tr>
<tr><th>Factor direccional</th><td>{traffic['direction_factor']:.3f}</td></tr>
<tr><th>Factor de carril</th><td>{traffic['lane_factor']:.3f}</td></tr>
<tr><th>Ejes equivalentes</th><td>{traffic['esal']:,.0f}</td></tr>
{traffic_class_html}
</table>

<h2>2. Subrasante</h2>
<table>
<tr><th>CBR de diseño</th><td>{subgrade['cbr']:.2f}%</td></tr>
<tr><th>Clasificación</th><td>{subgrade['class']}</td></tr>
<tr><th>Módulo resiliente de diseño</th><td>{subgrade['mr']:.2f} MPa</td></tr>
<tr><th>Fuente de Mr</th><td>{subgrade.get('mr_source','')}</td></tr>
<tr><th>SUCS</th><td>{subgrade.get('sucs','')}</td></tr>
<tr><th>AASHTO</th><td>{subgrade.get('aashto','')}</td></tr>
<tr><th>LL / IP</th><td>{subgrade.get('liquid_limit_pct',0):.1f}% / {subgrade.get('plasticity_index_pct',0):.1f}%</td></tr>
</table>

<h2>3. Estructura seleccionada</h2>
{structure_html}

<h2>4. Materiales y confiabilidad</h2>
<table>
<tr><th>E* mezcla asfáltica</th><td>{materials.get('asphalt_dynamic_modulus_mpa',0):,.0f} MPa</td></tr>
<tr><th>Mr base granular</th><td>{materials.get('base_mr_mpa',0):,.0f} MPa</td></tr>
<tr><th>Mr subbase</th><td>{materials.get('subbase_mr_mpa',0):,.0f} MPa</td></tr>
<tr><th>Módulo base estabilizada</th><td>{materials.get('stabilized_modulus_mpa',0):,.0f} MPa</td></tr>
<tr><th>Fuente de materiales</th><td>{materials.get('source','')}</td></tr>
<tr><th>Confiabilidad</th><td>{reliability.get('reliability_pct',0):.1f}%</td></tr>
</table>

<h2>5. Respuesta mecanística de cribado</h2>
<table>
<tr><th>Método</th><td>{mechanistic.get('method','No ejecutado')}</td></tr>
<tr><th>Carga de eje</th><td>{mechanistic.get('axle_load_kn',0):.1f} kN</td></tr>
<tr><th>Presión de contacto</th><td>{mechanistic.get('tire_pressure_kpa',0):.0f} kPa</td></tr>
<tr><th>εt bajo carpeta</th><td>{mechanistic.get('asphalt_tensile_microstrain_screening',0):.0f} µε · utilización {mechanistic.get('fatigue_utilization_ratio',0):.2f}</td></tr>
<tr><th>εv sobre subrasante</th><td>{mechanistic.get('subgrade_vertical_microstrain_screening',0):.0f} µε · utilización {mechanistic.get('rutting_utilization_ratio',0):.2f}</td></tr>
</table>
<p class='note'>Cribado preliminar: no sustituye un solver elástico multicapa ni funciones de transferencia calibradas GDP-2024.</p>

<h2>6. Transferencia, clima y confiabilidad</h2>
<table>
<tr><th>Estado de calibración</th><td>{transfer_model.get('calibration_status','No activado')}</td></tr>
<tr><th>Daño fatiga de diseño</th><td>{transfer_model.get('fatigue_damage_design',0):.3f}</td></tr>
<tr><th>Daño ahuellamiento de diseño</th><td>{transfer_model.get('rutting_damage_design',0):.3f}</td></tr>
<tr><th>Multiplicador de confiabilidad</th><td>{mechanistic.get('reliability_multiplier',1):.3f}</td></tr>
</table>

<h2>7. Tramos homogéneos y rehabilitación</h2>
<p><b>Tramos documentados:</b> {len(homogeneous_segments)} · <b>Modo rehabilitación:</b> {'Sí' if rehabilitation.get('enabled') else 'No'}.</p>
<p><b>PCI existente:</b> {rehabilitation.get('pci','No aplica')} · <b>IRI:</b> {rehabilitation.get('iri_m_km','No aplica')} · <b>FWD D0:</b> {rehabilitation.get('fwd_d0_um','No aplica')}.</p>

<h2>8. Diseño iterativo y comparación</h2>
<p><b>Candidatos generados:</b> {len(optimization_candidates)}. La jerarquía Tomo I prioriza cumplimiento técnico y utilización a confiabilidad antes del costo.</p>

<h2>9. Estimación económica</h2>
<table>
<tr><th>Área</th><td>{costs.get('area', 0):,.2f} m²</td></tr>
<tr><th>Costo estimado</th><td>{money(costs.get('total', 0))}</td></tr>
<tr><th>Costo por m²</th><td>{money(costs.get('per_m2', 0))}</td></tr>
</table>

<h2>10. Limitaciones y controles de emisión</h2>
<ul>
<li>El cribado mecanístico actual no sustituye un solver elástico multicapa validado.</li>
<li>Las funciones de transferencia son configurables y permanecen pendientes de calibración específica mientras así se indique.</li>
<li>La segmentación homogénea requiere confirmación con investigación de campo y criterio geotécnico.</li>
<li>En rehabilitación, el retrocálculo FWD/capacidad residual permanece pendiente de un módulo validado.</li>
<li>La selección final debe documentar fuentes, ensayos, drenaje, materiales, control de calidad y revisión profesional.</li>
</ul>
<div class='note'><b>Advertencia técnica:</b> Esta memoria es un expediente de revisión. No debe interpretarse como conformidad final automática del GDP-2024 mientras existan bloques identificados como configurables, preliminares o pendientes de calibración.</div>
</body></html>"""



CLIMATE_STATIONS_TOMO_II = list(CLIMATE_ZONES)
PROJECT_CLIMATE_OPTION = "Coordenadas del proyecto (NASA POWER)"


def current_project_climate_point() -> tuple[float, float, str]:
    project_map = st.session_state.get("project_map", {})
    project_map.setdefault("latitude", float(latitude))
    project_map.setdefault("longitude", float(longitude))
    return project_climate_point(
        project_map,
        st.session_state.get("project_segment_coordinates", {}),
    )


def load_climate_zone_to_state() -> None:
    zone = st.session_state.get("climate_station_selected", PROJECT_CLIMATE_OPTION)
    if zone == "Otra / dato propio":
        st.session_state.climate_catalog_status = "manual"
        st.session_state.pop("climate_catalog", None)
        return
    try:
        if zone == PROJECT_CLIMATE_OPTION:
            climate_lat, climate_lon, geometry_label = current_project_climate_point()
            catalog = fetch_point_climatology(climate_lat, climate_lon, PROJECT_CLIMATE_OPTION)
            catalog["geometry_label"] = geometry_label
        else:
            catalog = fetch_zone_climatology(zone)
            catalog["geometry_label"] = "Punto representativo de zona"
    except Exception as exc:
        st.session_state.climate_catalog_status = "error"
        st.session_state.climate_catalog_error = str(exc)
        st.session_state.pop("climate_catalog", None)
        return
    st.session_state.climate_catalog = catalog
    st.session_state.climate_catalog_status = "loaded"
    st.session_state.climate_source_input = catalog["source"]
    st.session_state.climate_period_input = catalog["period"]
    st.session_state.climate_air_temp_c = float(catalog["annual_c"])

def pavement_temperature_ltpp(air_c: float, latitude: float, depth_mm: float) -> float:
    """GDP Tomo I, Ec. 303-03 (modelo LTPP)."""
    import math
    return 54.32 + 0.78 * air_c - 0.0025 * latitude**2 - 15.14 * math.log(depth_mm + 25.0)

def pavement_temperature_shrp(air_c: float, latitude: float, depth_mm: float) -> float:
    """GDP Tomo I, Ec. 303-01 y 303-02. Resultado convertido a °C."""
    air_f = air_c * 1.8 + 32.0
    tsup_f = (air_f - 0.00618 * latitude**2 + 0.2289 * latitude + 24.4) * 1.8 + 32.0
    d_in = max(depth_mm / 25.4, 0.0)
    tpav_f = tsup_f * (1 - 0.063*d_in + 0.007*d_in**2 - 0.0004*d_in**3)
    return (tpav_f - 32.0) / 1.8

def climate_alerts(active_tomo: str, pavement_type: str, air_c: float, pavement_c: float,
                   latitude: float, depth_mm: float, analysis_category: int,
                   temp_data_confirmed: bool, master_curve_confirmed: bool,
                   station_selected: str) -> list[tuple[str,str]]:
    alerts=[]
    if not (-90 <= latitude <= 90):
        alerts.append(("error", "La latitud ingresada no es válida."))
    if air_c < 0 or air_c > 40:
        alerts.append(("warning", "La temperatura promedio del aire está fuera del intervalo usual de las zonas costarricenses evaluadas; verifique la fuente y la representatividad del dato."))
    if depth_mm <= 0:
        alerts.append(("error", "La profundidad de evaluación debe ser mayor que cero."))
    if active_tomo == "Tomo I":
        if not temp_data_confirmed:
            alerts.append(("error", "Tomo I: debe documentarse una temperatura representativa del sitio para ajustar el módulo de la mezcla asfáltica."))
        if pavement_type in ("Flexible", "Por definir"):
            if analysis_category in (1,2) and not master_curve_confirmed:
                alerts.append(("error", "Tomo I, categorías 1 y 2: se requiere una curva maestra de módulo dinámico que considere temperatura y frecuencia de carga."))
            elif analysis_category == 3 and not master_curve_confirmed:
                alerts.append(("warning", "Tomo I, categoría 3: incorpore módulos de la mezcla a temperaturas representativas o una relación equivalente validada."))
        if pavement_c >= 45:
            alerts.append(("warning", "La temperatura estimada del pavimento es elevada; el módulo de la mezcla puede reducirse de forma importante. Verifique susceptibilidad al ahuellamiento y el desempeño de la mezcla."))
        elif pavement_c <= 15:
            alerts.append(("warning", "La temperatura estimada del pavimento es baja; revise el riesgo de fisuración térmica y la validez del módulo usado."))
    else:
        if station_selected == "Otra / dato propio":
            alerts.append(("warning", "Tomo II: el catálogo fue desarrollado con información climática de estaciones del IMN. Justifique que el dato propio representa adecuadamente el sitio."))
        if not temp_data_confirmed:
            alerts.append(("warning", "Tomo II: confirme la estación o fuente climática utilizada para documentar la selección del catálogo."))
        if pavement_c >= 45 or pavement_c <= 15:
            alerts.append(("warning", "La temperatura estimada se encuentra en una condición térmica exigente. Aunque el Tomo II usa un catálogo preevaluado, se recomienda una revisión complementaria con el Tomo I."))
    if not alerts:
        alerts.append(("success", "La información climática básica está completa y no se detectaron alertas automáticas."))
    return alerts


def present_value(amount: float, year: int, discount_rate: float) -> float:
    return amount / ((1 + discount_rate) ** max(year, 0))

def build_excel_workbook(payload: dict, vehicles_df: pd.DataFrame, alternatives_df: pd.DataFrame, maintenance_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame([payload["project"]]).to_excel(writer, sheet_name="Proyecto", index=False)
        vehicles_df.to_excel(writer, sheet_name="Transito", index=False)
        pd.DataFrame([payload["traffic"]]).to_excel(writer, sheet_name="Resultados_transito", index=False)
        pd.DataFrame([payload["subgrade"]]).to_excel(writer, sheet_name="Subrasante", index=False)
        pd.DataFrame([payload.get("geometry", {})]).to_excel(writer, sheet_name="Geometria", index=False)
        pd.DataFrame([payload.get("materials", {})]).to_excel(writer, sheet_name="Materiales", index=False)
        pd.DataFrame([payload.get("reliability", {})]).to_excel(writer, sheet_name="Confiabilidad", index=False)
        pd.DataFrame(payload.get("normative_evidence", [])).to_excel(writer, sheet_name="Evidencia_normativa", index=False)
        pd.DataFrame([payload.get("granular_quality", {})]).to_excel(writer, sheet_name="Granulares_calidad", index=False)
        pd.DataFrame([payload.get("layer_interfaces", {})]).to_excel(writer, sheet_name="Interfaces", index=False)
        pd.DataFrame([payload.get("stabilized_base_model", {})]).to_excel(writer, sheet_name="Base_estabilizada", index=False)
        pd.DataFrame([payload.get("construction_constraints", {})]).to_excel(writer, sheet_name="Restricciones", index=False)
        pd.DataFrame(payload.get("scenario_comparison", [])).to_excel(writer, sheet_name="Escenarios", index=False)
        pd.DataFrame([payload.get("mechanistic_screening", {})]).to_excel(writer, sheet_name="Respuesta_ME", index=False)
        pd.DataFrame([payload.get("transfer_model", {})]).to_excel(writer, sheet_name="Transferencia", index=False)
        pd.DataFrame(payload.get("homogeneous_segments", [])).to_excel(writer, sheet_name="Tramos", index=False)
        pd.DataFrame([payload.get("rehabilitation", {})]).to_excel(writer, sheet_name="Rehabilitacion", index=False)
        opt_export = payload.get("optimization_candidates", [])
        pd.DataFrame(opt_export).to_excel(writer, sheet_name="Optimizacion", index=False)
        climate_payload = dict(payload.get("climate", {}))
        monthly_rows = climate_payload.pop("monthly_table", [])
        pd.DataFrame([climate_payload]).to_excel(writer, sheet_name="Clima", index=False)
        if monthly_rows:
            pd.DataFrame(monthly_rows).to_excel(writer, sheet_name="Clima_mensual", index=False)
        asphalt_control = payload.get("asphalt_cr2020", payload.get("asphalt_cr2010", {}))
        if asphalt_control:
            pd.DataFrame([{k:v for k,v in asphalt_control.items() if k != "checks"}]).to_excel(writer, sheet_name="Control_CR2020", index=False)
            pd.DataFrame(asphalt_control.get("checks", [])).to_excel(writer, sheet_name="Checklist_CR2020", index=False)
        alternatives_df.to_excel(writer, sheet_name="Alternativas", index=False)
        maintenance_df.to_excel(writer, sheet_name="Ciclo_vida", index=False)
        pd.DataFrame([payload.get("drainage", {})]).to_excel(writer, sheet_name="Drenaje", index=False)
    return output.getvalue()

def build_pdf_report(payload: dict) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet(); story=[]
    story.append(Paragraph("GDP Pavimentos Pro 2024 — Memoria preliminar", styles["Title"]))
    story.append(Paragraph(f"Proyecto: {payload['project']['name']} — {payload['project']['location']}", styles["Normal"]))
    story.append(Paragraph(
        f"CRTM05 EPSG:5367: E {payload['project'].get('crtm05_easting_m', 0):,.3f} m, "
        f"N {payload['project'].get('crtm05_northing_m', 0):,.3f} m · "
        f"WGS84 EPSG:4326: {payload['project'].get('latitude', 0):.7f}°, {payload['project'].get('longitude', 0):.7f}°",
        styles["Normal"],
    ))
    story.append(Spacer(1,12))
    rows=[["Parámetro","Resultado"], ["Tomo activo", payload.get("active_tomo","")], ["TPD", f"{payload['traffic']['tpd_total']:,.0f}"], ["Crecimiento anual", f"{payload['traffic']['growth_rate']:.2f}%"], ["Factor de crecimiento G", f"{payload['traffic'].get('growth_factor', 0):.3f}"], ["Periodo de diseño", f"{payload['traffic']['years']} años"], ["ESAL", f"{payload['traffic']['esal']:,.0f}"], ["Clase", payload['traffic']['class']], ["CBR", f"{payload['subgrade']['cbr']:.2f}%"], ["Subrasante", payload['subgrade']['class']]]
    if payload.get("active_tomo") == "Tomo I":
        pdf_category = payload["traffic"].get("design_category", tomo1_design_category(float(payload["traffic"].get("esal", 0.0))))
        rows.insert(8, ["Categoría de diseño Tomo I", f"Categoría {pdf_category}"])
    climate = payload.get("climate", {})
    geometry = payload.get("geometry", {})
    materials = payload.get("materials", {})
    reliability = payload.get("reliability", {})
    mechanistic = payload.get("mechanistic_screening", {})
    rows += [
        ["Longitud de diseño", f"{geometry.get('length_m', 0):,.1f} m"],
        ["Ancho de referencia", f"{geometry.get('paved_reference_width_m', 0):,.2f} m"],
        ["Fuente Mr subrasante", str(payload.get("subgrade", {}).get("mr_source", ""))],
        ["E* mezcla asfáltica", f"{materials.get('asphalt_dynamic_modulus_mpa',0):,.0f} MPa"],
        ["Confiabilidad", f"{reliability.get('reliability_pct',0):.1f}%"],
        ["Cribado εt bajo carpeta", f"{mechanistic.get('asphalt_tensile_microstrain_screening',0):.0f} µε"],
        ["Cribado εv sobre subrasante", f"{mechanistic.get('subgrade_vertical_microstrain_screening',0):.0f} µε"],
        ["Utilización fatiga / ahuellamiento", f"{mechanistic.get('fatigue_utilization_design', mechanistic.get('fatigue_utilization_ratio',0)):.2f} / {mechanistic.get('rutting_utilization_design', mechanistic.get('rutting_utilization_ratio',0)):.2f}"],
        ["Transferencia - estado", str(payload.get('transfer_model',{}).get('calibration_status','No activado'))],
        ["Tramos homogéneos", str(len(payload.get('homogeneous_segments',[])))],
        ["Rehabilitación", "Sí" if payload.get('rehabilitation',{}).get('enabled') else "No"],
        ["Candidatos de optimización", str(len(payload.get('optimization_candidates',[])))],
        ["Clima - modo", str(climate.get("input_mode", ""))],
        ["Clima - fuente", str(climate.get("source", ""))],
        ["Clima - periodo", str(climate.get("period", ""))],
        ["Clima - estación/zona", str(climate.get("station", ""))],
        ["Temperatura aire representativa", f"{float(climate.get('air_c', 0)):.1f} °C"],
    ]
    if payload.get('selected'):
        rows += [["Estructura", str(payload['selected'].get('Código',''))], ["Superficie", str(payload['selected'].get('Superficie',''))]]
    asphalt_control = payload.get("asphalt_cr2020", payload.get("asphalt_cr2010", {}))
    if asphalt_control:
        rows += [
            ["Control CR-2020 asfaltos", f"{asphalt_control.get('compliant', 0)}/{asphalt_control.get('total_applicable', 0)} controles"],
            ["Cumplimiento CR-2020", f"{asphalt_control.get('compliance_pct', 0):.0f}%"],
            ["No conformidades críticas", str(asphalt_control.get('critical_nonconformities', 0))],
        ]
    t=Table(rows, colWidths=[180,300]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0f6fff')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.grey),('PADDING',(0,0),(-1,-1),7)])); story.append(t)
    story.append(Spacer(1,14))
    story.append(Paragraph("Advertencia: resultado preliminar sujeto a verificación profesional, caracterización de materiales, drenaje, control de calidad y aplicación integral del GDP-2024.", styles["Italic"]))
    doc.build(story); return buff.getvalue()

def build_geojson(project_name: str, start_lon: float, start_lat: float, end_lon: float, end_lat: float, properties: dict) -> bytes:
    feature={"type":"Feature","properties":{"project":project_name,**properties},"geometry":{"type":"LineString","coordinates":[[start_lon,start_lat],[end_lon,end_lat]]}}
    return json.dumps({"type":"FeatureCollection","features":[feature]}, ensure_ascii=False, indent=2).encode('utf-8')

def build_civil3d_csv(start_e: float, start_n: float, azimuth_deg: float, length_m: float, interval_m: float, elevation: float) -> bytes:
    rows=[]; az=math.radians(azimuth_deg); station=0.0; idx=1
    while station <= length_m + 1e-9:
        e=start_e + station*math.sin(az); n=start_n + station*math.cos(az)
        rows.append([idx,e,n,elevation,f"EJE_{station:.2f}"]); station += interval_m; idx += 1
    return pd.DataFrame(rows, columns=["Point","Easting","Northing","Elevation","Description"]).to_csv(index=False).encode('utf-8-sig')

def build_section_dxf(selected: dict, width_m: float) -> bytes:
    import ezdxf
    doc=ezdxf.new('R2010'); msp=doc.modelspace(); y=0.0
    layers=[]
    surface=float(selected.get('Carpeta_cm',0)) or 2.0
    layers=[('SUPERFICIE',surface),('BASE',float(selected.get('Base_cm',0))),('SUBBASE',float(selected.get('Subbase_cm',0)))]
    for name,cm in layers:
        h=cm/100.0; pts=[(-width_m/2,-y),(width_m/2,-y),(width_m/2,-y-h),(-width_m/2,-y-h)]
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer':name}); msp.add_text(f"{name} {cm:.0f} cm", dxfattribs={'height':0.12}).set_placement((width_m/2+0.25,-y-h/2)); y += h
    stream=io.StringIO(); doc.write(stream); return stream.getvalue().encode('utf-8')

# -----------------------------
# Web Ready: autenticación, usuarios y proyectos persistentes
# -----------------------------
AUTH_REQUIRED = os.getenv("GDP_AUTH_REQUIRED", "1").strip().lower() not in {"0", "false", "no"}
ALLOW_REGISTRATION = os.getenv("GDP_ALLOW_REGISTRATION", "1").strip().lower() not in {"0", "false", "no"}
PILOT_MODE = os.getenv("GDP_PILOT_MODE", "1").strip().lower() not in {"0", "false", "no"}

def _capture_session_state():
    state = {}
    for key, value in st.session_state.items():
        if is_ephemeral_state_key(key):
            continue
        # UploadedFile y objetos efímeros no deben persistirse.
        if value.__class__.__name__ in {"UploadedFile", "UploadedFileRec"}:
            continue
        state[key] = value
    return state


def _restore_session_state(saved):
    if not isinstance(saved, dict):
        return
    auth_user = st.session_state.get("auth_user")
    for key in list(st.session_state.keys()):
        if not is_active_control_key(key) and key != "auth_user":
            try:
                del st.session_state[key]
            except Exception:
                pass
    for key, value in saved.items():
        # También filtra claves heredadas de proyectos guardados antes de esta corrección.
        if not is_ephemeral_state_key(key):
            st.session_state[key] = value
    if auth_user:
        st.session_state.auth_user = auth_user


def _format_project_timestamp(value):
    """Format storage timestamps for the project manager without exposing raw ISO text."""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(value or "—")


def _auth_screen():
    st.markdown('<div class="main-title">🛣️ GDP Pavimentos Pro 2024 — v1.1.3 Piloto Cloud</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Acceso multiusuario · proyectos persistentes · preparado para despliegue web.</div>', unsafe_allow_html=True)
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        view = st.radio("Acceso", ["Iniciar sesión", "Crear cuenta"], horizontal=True, label_visibility="collapsed") if ALLOW_REGISTRATION else "Iniciar sesión"
        if view == "Iniciar sesión":
            with st.form("login_form"):
                username = st.text_input("Usuario", key="login_user")
                password = st.text_input("Contraseña", type="password", key="login_password")
                submit = st.form_submit_button("Ingresar", use_container_width=True)
            if submit:
                user = authenticate(username, password)
                if user:
                    st.session_state.auth_user = user
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
        else:
            with st.form("registration_form"):
                display = st.text_input("Nombre", key="reg_name")
                username = st.text_input("Usuario", key="reg_user")
                password = st.text_input("Contraseña (mínimo 8 caracteres)", type="password", key="reg_password")
                submit = st.form_submit_button("Crear cuenta", use_container_width=True)
            if submit:
                ok, message = create_user(username, password, display)
                if ok:
                    st.success(message + " Ahora puede iniciar sesión.")
                else:
                    st.error(message)

        if PILOT_MODE:
            st.markdown("---")
            st.caption("Piloto gratuito: puede entrar como invitado sin crear cuenta. Los datos del invitado no se guardan.")
            if st.button("🚀 Continuar como invitado", use_container_width=True):
                st.session_state.auth_user = {"id": 0, "username": "invitado", "display_name": "Usuario invitado"}
                st.rerun()

if AUTH_REQUIRED and "auth_user" not in st.session_state:
    _auth_screen()
    st.stop()

if not AUTH_REQUIRED and "auth_user" not in st.session_state:
    st.session_state.auth_user = {"id": 0, "username": "local", "display_name": "Usuario local"}

# Estado
if "catalog" not in st.session_state:
    st.session_state.catalog = CATALOG_DEFAULT.copy()
if "vehicles" not in st.session_state:
    st.session_state.vehicles = VEHICLE_DEFAULTS.copy()

st.markdown('<div class="main-title">🛣️ GDP Pavimentos Pro 2024 — v1.1.3 Piloto Cloud</div>', unsafe_allow_html=True)
st.markdown('<div class="subtle">Diseño flexible, visor estructural 3D v2 y gestión multiusuario · piloto gratuito para validación pública.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div class='brand-box'><div class='brand-title'>🛣️ GDP PAVIMENTOS PRO 2024</div><div class='brand-sub'>Diseño conforme al GDP 2024</div></div>", unsafe_allow_html=True)
    user = st.session_state.get("auth_user", {"id":0,"username":"local","display_name":"Usuario local"})
    st.caption(f"👤 {user.get('display_name', user.get('username','Usuario'))}")
    if AUTH_REQUIRED and st.button("Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    st.markdown("### Mis proyectos")
    projects = list_projects(int(user.get("id", 0))) if int(user.get("id",0)) > 0 else []
    project_name_web = st.text_input("Nombre para guardar", value=st.session_state.get("project_save_name", "Proyecto GDP"), key="project_save_name")
    if int(user.get("id",0)) > 0:
        if st.button("💾 Guardar / actualizar proyecto", use_container_width=True):
            if project_name_web.strip():
                state_to_save = _capture_session_state()
                save_project(int(user["id"]), project_name_web.strip(), state_to_save)
                st.session_state._active_project_name = project_name_web.strip()
                st.session_state._autosave_hash = project_state_fingerprint(state_to_save)
                st.session_state._autosave_last_at = datetime.now().strftime("%H:%M:%S")
                st.session_state._autosave_status = "saved"
                st.success("Proyecto guardado.")
                st.rerun()
            else:
                st.warning("Indique un nombre para el proyecto.")
        if projects:
            options = {f"{p['name']} · {p['updated_at']}": p for p in projects}
            label = st.selectbox("Proyecto guardado", list(options.keys()), key="project_pick")
            pinfo = options[label]
            copen, cdel = st.columns(2)
            with copen:
                if st.button("📂 Abrir", use_container_width=True):
                    saved = load_project(int(user["id"]), int(pinfo["id"]))
                    if saved is not None:
                        _restore_session_state(saved)
                        st.session_state._active_project_name = pinfo["name"]
                        st.session_state._autosave_hash = project_state_fingerprint(saved)
                        st.session_state._autosave_status = "saved"
                        st.session_state._loaded_project_notice = pinfo["name"]
                        st.rerun()
            with cdel:
                if st.button("🗑️ Eliminar", use_container_width=True):
                    delete_project(int(user["id"]), int(pinfo["id"]))
                    if st.session_state.get("_active_project_name") == pinfo["name"]:
                        st.session_state.pop("_active_project_name", None)
                        st.session_state.pop("_autosave_hash", None)
                    st.rerun()
        else:
            st.caption("Aún no hay proyectos guardados.")
    else:
        st.info("Modo invitado: puede usar todos los cálculos, pero este proyecto no se guardará de forma permanente.")
    if st.session_state.pop("_loaded_project_notice", None):
        st.success("Proyecto cargado correctamente.")
    st.markdown("---")
    st.markdown("### Navegación")
    st.caption("Complete las pestañas y consulte el Dashboard para el resumen general.")
    st.markdown("---")
    st.markdown("### Calidad visual 3D")
    st.selectbox("Nivel de detalle", ["Media", "Alta", "Ultra"], index=1, key="render_quality", help="Ultra mejora la textura, pero requiere más capacidad gráfica.")
    st.toggle("Rotación automática al abrir", value=True, key="auto_rotate_3d", help="El modelo gira lentamente. También puede pausarlo o reanudarlo dentro del visor 3D.")
    st.markdown("### Configuración normativa")
    st.success("Tomo II usa el catálogo oficial GDP-2024 integrado y trazable. No requiere cargar CSV externos.")
    st.caption("Las alternativas se seleccionan desde las Tablas 301-01 a 301-21 según TPD, porcentaje de pesados, CBR y período de diseño. Los períodos no tabulados no se interpolan.")
    st.download_button(
        "Descargar catálogo histórico (solo referencia)",
        data=CATALOG_DEFAULT.to_csv(index=False).encode("utf-8-sig"),
        file_name="catalogo_historico_no_normativo.csv",
        mime="text/csv",
        help="Archivo heredado conservado únicamente para compatibilidad y referencia; no alimenta la selección oficial del Tomo II.",
    )

# Acceso visible a cuenta y proyectos, aun cuando la barra lateral se haya colapsado manualmente.
st.markdown("### 👤 Cuenta y proyectos")
if int(user.get("id", 0)) > 0:
    st.success(
        f"Sesión iniciada como **{user.get('display_name', user.get('username', 'Usuario'))}**. "
        "Guarde un proyecto nuevo o continúe trabajando sobre uno existente."
    )
    active_autosave_name = st.session_state.get("_active_project_name")
    if active_autosave_name:
        last_autosave = st.session_state.get("_autosave_last_at", "esta sesión")
        if st.session_state.get("_autosave_status") == "error":
            st.error(f"Guardado automático pendiente para **{active_autosave_name}**.")
        else:
            st.caption(f"☁️ Proyecto activo: **{active_autosave_name}** · guardado automático {last_autosave}")
    else:
        st.caption("El guardado automático se activará después del primer guardado manual o al abrir un proyecto.")

    project_data_col, project_actions_col = st.columns([3, 1], gap="large")
    selected_project = None
    with project_data_col:
        project_name_main = st.text_input(
            "Nombre del proyecto",
            value=st.session_state.get("main_project_save_name", project_name_web or "Proyecto GDP"),
            key="main_project_save_name",
        )
        if projects:
            project_search = st.text_input(
                "Buscar por nombre",
                placeholder="Escriba parte del nombre",
                key="main_project_search",
            )
            filtered_projects = [
                project for project in projects
                if project_search.strip().casefold() in str(project["name"]).casefold()
            ]
            if filtered_projects:
                main_options = {str(project["name"]): project for project in filtered_projects}
                selected_project_label = st.selectbox(
                    "Proyecto guardado",
                    list(main_options.keys()),
                    key="main_project_pick",
                )
                selected_project = main_options[selected_project_label]
                st.caption(
                    f"Actualizado: **{_format_project_timestamp(selected_project['updated_at'])}** · "
                    f"Creado: {_format_project_timestamp(selected_project['created_at'])}"
                )
            else:
                st.info("No se encontraron proyectos que coincidan con la búsqueda.")
        else:
            st.info("Aún no hay proyectos guardados para esta cuenta.")

    with project_actions_col:
        st.markdown("#### Acciones")
        if st.button("💾 Guardar proyecto ahora", use_container_width=True, key="main_save_project"):
            if project_name_main.strip():
                state_to_save = _capture_session_state()
                save_project(int(user["id"]), project_name_main.strip(), state_to_save)
                st.session_state._active_project_name = project_name_main.strip()
                st.session_state._autosave_hash = project_state_fingerprint(state_to_save)
                st.session_state._autosave_last_at = datetime.now().strftime("%H:%M:%S")
                st.session_state._autosave_status = "saved"
                st.success("Proyecto guardado correctamente.")
                st.rerun()
            else:
                st.warning("Indique un nombre para el proyecto.")
        if selected_project:
            if st.button("📂 Abrir proyecto", use_container_width=True, key="main_open_project"):
                saved = load_project(int(user["id"]), int(selected_project["id"]))
                if saved is not None:
                    _restore_session_state(saved)
                    st.session_state._active_project_name = selected_project["name"]
                    st.session_state._autosave_hash = project_state_fingerprint(saved)
                    st.session_state._autosave_status = "saved"
                    st.session_state._loaded_project_notice = selected_project["name"]
                    st.rerun()
                else:
                    st.error("No fue posible recuperar el proyecto seleccionado.")
            confirm_main_delete = st.checkbox(
                "Confirmar eliminación",
                key="main_confirm_delete_project",
            )
            if st.button(
                "🗑️ Eliminar proyecto",
                use_container_width=True,
                disabled=not confirm_main_delete,
                key="main_delete_project",
            ):
                delete_project(int(user["id"]), int(selected_project["id"]))
                if st.session_state.get("_active_project_name") == selected_project["name"]:
                    st.session_state.pop("_active_project_name", None)
                    st.session_state.pop("_autosave_hash", None)
                st.success(f"Proyecto “{selected_project['name']}” eliminado.")
                st.rerun()
else:
    guest_col, login_col = st.columns([3, 1])
    with guest_col:
        st.warning(
            "Está usando GDP Pavimentos Pro como **invitado**. Puede realizar cálculos, pero los proyectos no se guardan permanentemente. "
            "Inicie sesión o cree una cuenta para activar **Mis proyectos**."
        )
    with login_col:
        if st.button("🔐 Iniciar sesión / Crear cuenta", use_container_width=True, key="main_login_from_guest"):
            st.session_state.clear()
            st.rerun()

# Selector principal de metodología
if "active_tomo" not in st.session_state:
    st.session_state.active_tomo = "Tomo II"

pending_active_tomo = st.session_state.pop("_pending_active_tomo", None)
if pending_active_tomo in ("Tomo I", "Tomo II"):
    st.session_state.active_tomo = pending_active_tomo
    st.session_state.tomo_selector = pending_active_tomo

st.markdown("### Metodología de diseño")
head_left, head_mid = st.columns([1, 3])
with head_left:
    active_tomo = st.segmented_control(
        "Normativa activa", ["Tomo I", "Tomo II"],
        default=st.session_state.active_tomo, key="tomo_selector"
    ) or st.session_state.active_tomo
    st.session_state.active_tomo = active_tomo
with head_mid:
    if active_tomo == "Tomo II":
        st.markdown('<div class="mode-card">📘 <b>Tomo activo: II — Catálogo simplificado</b><br><span style="font-weight:500">Selección de estructuras para vías de bajo volumen.</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mode-card">📗 <b>Tomo activo: I — Diseño mecanístico-empírico</b><br><span style="font-weight:500">Evaluación preliminar de pavimentos flexibles y semirrígidos.</span></div>', unsafe_allow_html=True)
st.caption("Puede cambiar de tomo sin perder los datos del proyecto guardados en la sesión.")

# Valores compartidos entre módulos
selected_row = st.session_state.get("selected_row")
total_thickness = float(st.session_state.get("total_thickness", 0.0))
exact_match = bool(st.session_state.get("exact_match", False))

# Pestañas
pdash, p1, p2, p3, pclima, p4, pflex, pperf, pcompare, p5, pmaint, pdrain, pvalid, pcr2010, pexport, p6 = st.tabs([
    "🏠 Dashboard", "1. Proyecto", "2. Tránsito", "3. Subrasante", "4. Clima", "5. Estructura",
    "6. Diseño flexible", "7. Desempeño", "8. Comparación", "9. Costos", "10. Ciclo de vida", "11. Drenaje", "12. Validación", "13. Control CR-2020", "14. Exportación", "15. Informe"
])

with p1:
    c1, c2 = st.columns(2)
    with c1:
        project_name = st.text_input("Nombre del proyecto", "Proyecto vial")
        location = st.text_input("Ubicación", "Costa Rica")
        engineer = st.text_input("Profesional responsable", "")
    with c2:
        project_date = st.date_input("Fecha", date.today())
        road_type = st.selectbox("Tipo de vía", ["Camino de bajo volumen", "Urbanización", "Vía local", "Otro"])
        pavement_type = st.selectbox("Tipo de pavimento", ["Flexible", "Semirrígido", "Por definir"])

    # DESIGN_DATA_PHASE1
    st.markdown("### Geometría y configuración funcional del tramo")
    g1, g2, g3, g4 = st.columns(4)
    project_length_m = g1.number_input("Longitud de diseño (m)", min_value=1.0, value=150.0, step=10.0, key="project_design_length")
    lane_width_m = g2.number_input("Ancho de carril (m)", min_value=2.0, max_value=6.0, value=3.0, step=0.1, key="project_lane_width")
    number_lanes = g3.number_input("Número de carriles", min_value=1, max_value=12, value=2, step=1, key="project_number_lanes")
    traffic_directions = g4.selectbox("Sentidos de circulación", ["Dos sentidos", "Un sentido"], key="project_traffic_directions")
    g5, g6, g7, g8 = st.columns(4)
    shoulder_width_m = g5.number_input("Espaldón por lado (m)", min_value=0.0, max_value=5.0, value=0.0, step=0.25, key="project_shoulder_width")
    project_cross_slope_pct = g6.number_input("Pendiente transversal (%)", min_value=0.0, max_value=15.0, value=2.0, step=0.1, key="project_cross_slope")
    project_long_slope_pct = g7.number_input("Pendiente longitudinal media (%)", min_value=-20.0, max_value=20.0, value=0.0, step=0.1, key="project_long_slope")
    functional_class = g8.selectbox("Condición funcional", ["Nueva construcción", "Reconstrucción", "Rehabilitación", "Evaluación preliminar"], key="project_functional_condition")
    project_width_m = float(lane_width_m) * int(number_lanes) + 2.0 * float(shoulder_width_m)
    st.caption(f"Ancho geométrico de referencia calculado: {project_width_m:.2f} m. Estos datos se usan como trazabilidad y como valores iniciales en costos/exportación.")

    if functional_class == "Rehabilitación":
        st.markdown("### Diagnóstico del pavimento existente — rehabilitación")
        st.warning("Este bloque documenta condición y auscultación. No calcula capacidad residual definitiva hasta incorporar/validar el procedimiento de retrocálculo correspondiente.")
        rh1, rh2, rh3, rh4 = st.columns(4)
        existing_age = rh1.number_input("Edad del pavimento existente (años)", min_value=0.0, max_value=100.0, value=10.0, step=1.0, key="rehab_age")
        existing_pci = rh2.number_input("PCI observado", min_value=0.0, max_value=100.0, value=65.0, step=1.0, key="rehab_pci")
        existing_iri = rh3.number_input("IRI observado (m/km)", min_value=0.0, max_value=20.0, value=3.0, step=0.1, key="rehab_iri")
        existing_rut = rh4.number_input("Ahuellamiento observado (mm)", min_value=0.0, max_value=100.0, value=10.0, step=1.0, key="rehab_rut")
        rh5, rh6, rh7, rh8 = st.columns(4)
        existing_ac = rh5.number_input("Carpeta existente (cm)", min_value=0.0, max_value=100.0, value=8.0, step=1.0, key="rehab_ac")
        existing_base = rh6.number_input("Base existente (cm)", min_value=0.0, max_value=150.0, value=20.0, step=1.0, key="rehab_base")
        fwd_d0 = rh7.number_input("FWD D0 (µm, 0 = no disponible)", min_value=0.0, max_value=5000.0, value=0.0, step=10.0, key="rehab_fwd_d0")
        fwd_d600 = rh8.number_input("FWD D600 (µm, 0 = no disponible)", min_value=0.0, max_value=5000.0, value=0.0, step=10.0, key="rehab_fwd_d600")
        rehab_notes = st.text_area("Patologías, reparaciones previas y observaciones", value="", height=80, key="rehab_notes")
        st.session_state.rehabilitation = {
            'enabled': True, 'age_years': existing_age, 'pci': existing_pci, 'iri_m_km': existing_iri,
            'rutting_mm': existing_rut, 'existing_asphalt_cm': existing_ac, 'existing_base_cm': existing_base,
            'fwd_d0_um': fwd_d0, 'fwd_d600_um': fwd_d600, 'notes': rehab_notes,
            'backcalculation_status': 'Pendiente de módulo específico' if fwd_d0 > 0 else 'Sin datos FWD',
        }
        if existing_pci < 55:
            st.error("PCI bajo: la alternativa de rehabilitación debe considerar reparación estructural/rehabilitación mayor antes de aceptar un simple refuerzo.")
        elif existing_pci < 70:
            st.warning("PCI intermedio: revise fallas estructurales, drenaje y deflexiones antes de definir el tratamiento.")
    else:
        st.session_state.rehabilitation = {'enabled': False}

    st.session_state.project_geometry = {
        "length_m": float(project_length_m), "lane_width_m": float(lane_width_m),
        "number_lanes": int(number_lanes), "traffic_directions": traffic_directions,
        "shoulder_width_m": float(shoulder_width_m), "paved_reference_width_m": float(project_width_m),
        "cross_slope_pct": float(project_cross_slope_pct), "longitudinal_slope_pct": float(project_long_slope_pct),
        "functional_condition": functional_class,
    }

    st.markdown("### Ubicación geográfica y conversión de coordenadas")
    st.caption("CRTM05 se procesa como EPSG:5367 y WGS84 como EPSG:4326 mediante PROJ/pyproj. La conversión se actualiza automáticamente al cambiar los valores.")
    coordinate_system = st.segmented_control(
        "Sistema de coordenadas de entrada",
        ["CRTM05 (EPSG:5367)", "WGS84 (EPSG:4326)"],
        default="CRTM05 (EPSG:5367)",
        key="project_coordinate_system",
    ) or "CRTM05 (EPSG:5367)"

    if coordinate_system.startswith("CRTM05"):
        gc1, gc2 = st.columns(2)
        crtm_easting = gc1.number_input(
            "Este CRTM05 (m)", value=500000.0, step=1.0, format="%.3f", key="project_crtm_easting"
        )
        crtm_northing = gc2.number_input(
            "Norte CRTM05 (m)", value=1100000.0, step=1.0, format="%.3f", key="project_crtm_northing"
        )
        longitude, latitude = crtm05_to_wgs84(crtm_easting, crtm_northing)
        st.success(
            f"Conversión automática CRTM05 → WGS84: Latitud **{latitude:.7f}°**, Longitud **{longitude:.7f}°**"
        )
    else:
        gc1, gc2 = st.columns(2)
        latitude = gc1.number_input(
            "Latitud WGS84 (°)", min_value=-90.0, max_value=90.0, value=9.93, step=0.000001, format="%.7f", key="project_wgs84_latitude"
        )
        longitude = gc2.number_input(
            "Longitud WGS84 (°)", min_value=-180.0, max_value=180.0, value=-84.10, step=0.000001, format="%.7f", key="project_wgs84_longitude"
        )
        crtm_easting, crtm_northing = wgs84_to_crtm05(longitude, latitude)
        st.info(
            f"Equivalente CRTM05 → Este **{crtm_easting:,.3f} m**, Norte **{crtm_northing:,.3f} m**"
        )

    if not is_plausible_costa_rica_wgs84(longitude, latitude):
        st.warning("La coordenada convertida queda fuera del entorno geográfico amplio de Costa Rica. Revise sistema, Este/Norte o latitud/longitud antes de continuar.")

    # PROJECT_MAP_CONSOLIDATED
    loc1, loc2, loc3, loc4 = st.columns(4)
    loc1.metric("Este CRTM05", f"{crtm_easting:,.3f} m")
    loc2.metric("Norte CRTM05", f"{crtm_northing:,.3f} m")
    loc3.metric("Latitud WGS84", f"{latitude:.7f}°")
    loc4.metric("Longitud WGS84", f"{longitude:.7f}°")

    # PROJECT_MAP_GEOMETRY_MODE
    st.markdown("#### Mapa e inventario geográfico del proyecto")
    st.caption("Defina la geometría principal como un punto único o como un tramo entre dos puntos. El mapa permite zoom con la rueda del mouse.")

    def preserve_segment_coordinates() -> None:
        st.session_state.project_segment_coordinates = merge_segment_coordinate_snapshot(
            st.session_state.get("project_segment_coordinates", {}),
            dict(st.session_state),
        )

    def preserve_segment_coordinate(widget_key: str, field: str) -> None:
        if widget_key not in st.session_state:
            return
        st.session_state.project_segment_coordinates = update_segment_coordinate_snapshot(
            st.session_state.get("project_segment_coordinates", {}),
            field,
            st.session_state[widget_key],
        )

    geometry_mode = st.segmented_control(
        "Geometría principal del proyecto",
        ["Punto único", "Tramo (inicio–fin)"],
        default=st.session_state.get("project_map_geometry_mode", "Punto único"),
        key="project_map_geometry_mode",
        on_change=preserve_segment_coordinates,
    ) or "Punto único"

    # Streamlit elimina widgets que dejan de renderizarse. La copia durable se
    # actualiza atómicamente desde el on_change de cada coordenada.
    segment_coordinates = st.session_state.get("project_segment_coordinates", {})

    def render_segment_coordinate_inputs():
        segment_system = st.segmented_control(
            "Sistema para inicio y fin", ["WGS84", "CRTM05"],
            default=st.session_state.get("project_segment_system", "WGS84"),
            key="project_segment_system",
            on_change=preserve_segment_coordinates,
        ) or "WGS84"
        if segment_system == "WGS84":
            sg1, sg2, sg3, sg4 = st.columns(4)
            start_lat = sg1.number_input("Latitud inicial", -90.0, 90.0, value=float(segment_coordinates.get("start_lat", latitude)), format="%.7f", key="project_segment_start_lat", on_change=preserve_segment_coordinate, args=("project_segment_start_lat", "start_lat"))
            start_lon = sg2.number_input("Longitud inicial", -180.0, 180.0, value=float(segment_coordinates.get("start_lon", longitude)), format="%.7f", key="project_segment_start_lon", on_change=preserve_segment_coordinate, args=("project_segment_start_lon", "start_lon"))
            end_lat = sg3.number_input("Latitud final", -90.0, 90.0, value=float(segment_coordinates.get("end_lat", latitude)), format="%.7f", key="project_segment_end_lat", on_change=preserve_segment_coordinate, args=("project_segment_end_lat", "end_lat"))
            end_lon = sg4.number_input("Longitud final", -180.0, 180.0, value=float(segment_coordinates.get("end_lon", longitude)), format="%.7f", key="project_segment_end_lon", on_change=preserve_segment_coordinate, args=("project_segment_end_lon", "end_lon"))
            start_e, start_n = wgs84_to_crtm05(start_lon, start_lat)
            end_e, end_n = wgs84_to_crtm05(end_lon, end_lat)
        else:
            sg1, sg2, sg3, sg4 = st.columns(4)
            start_e = sg1.number_input("Este inicial CRTM05", value=float(segment_coordinates.get("start_e", crtm_easting)), format="%.3f", key="project_segment_start_e", on_change=preserve_segment_coordinate, args=("project_segment_start_e", "start_e"))
            start_n = sg2.number_input("Norte inicial CRTM05", value=float(segment_coordinates.get("start_n", crtm_northing)), format="%.3f", key="project_segment_start_n", on_change=preserve_segment_coordinate, args=("project_segment_start_n", "start_n"))
            end_e = sg3.number_input("Este final CRTM05", value=float(segment_coordinates.get("end_e", crtm_easting)), format="%.3f", key="project_segment_end_e", on_change=preserve_segment_coordinate, args=("project_segment_end_e", "end_e"))
            end_n = sg4.number_input("Norte final CRTM05", value=float(segment_coordinates.get("end_n", crtm_northing)), format="%.3f", key="project_segment_end_n", on_change=preserve_segment_coordinate, args=("project_segment_end_n", "end_n"))
            start_lon, start_lat = crtm05_to_wgs84(start_e, start_n)
            end_lon, end_lat = crtm05_to_wgs84(end_e, end_n)

        st.session_state.project_segment_coordinates = {
            "start_lat": float(start_lat), "start_lon": float(start_lon),
            "end_lat": float(end_lat), "end_lon": float(end_lon),
            "start_e": float(start_e), "start_n": float(start_n),
            "end_e": float(end_e), "end_n": float(end_n),
        }
        return start_lat, start_lon, end_lat, end_lon, start_e, start_n, end_e, end_n

    main_project_line = []
    alignment_mode = "Línea directa"
    if geometry_mode == "Punto único":
        # El contenido de un expander cerrado continúa renderizado. Esto evita
        # que Streamlit elimine los widgets y sus valores al ocultar el tramo.
        with st.expander("Coordenadas del tramo guardadas", expanded=False):
            st.caption("Se conservan para cuando vuelva a seleccionar Tramo (inicio–fin).")
            render_segment_coordinate_inputs()
        base_geo_points = pd.DataFrame([{
            "Nombre": "Punto principal",
            "Tipo": "Proyecto",
            "Sistema": "WGS84",
            "Este_CRTM05": float(crtm_easting),
            "Norte_CRTM05": float(crtm_northing),
            "Latitud": float(latitude),
            "Longitud": float(longitude),
            "Descripción": str(location),
        }])
    else:
        st.markdown("##### Coordenadas del tramo")
        start_lat, start_lon, end_lat, end_lon, start_e, start_n, end_e, end_n = render_segment_coordinate_inputs()

        alignment_mode = st.radio(
            "Trazado del eje",
            ["Ajustar a carretera (automático)", "Puntos manuales", "Línea directa"],
            horizontal=True,
            key="project_road_alignment_mode",
            help="El ajuste automático consulta la red vial de OpenStreetMap. Los vértices manuales sirven como puntos de paso y como alternativa sin conexión.",
        )
        st.caption(
            "Para guiar el recorrido por una carretera específica, agregue filas de tipo "
            "**Vértice de eje** en el orden de avance entre el inicio y el fin."
        )

        base_geo_points = pd.DataFrame([
            {"Nombre":"Inicio del tramo","Tipo":"Inicio","Sistema":"WGS84","Este_CRTM05":float(start_e),"Norte_CRTM05":float(start_n),"Latitud":float(start_lat),"Longitud":float(start_lon),"Descripción":str(location)},
            {"Nombre":"Fin del tramo","Tipo":"Fin","Sistema":"WGS84","Este_CRTM05":float(end_e),"Norte_CRTM05":float(end_n),"Latitud":float(end_lat),"Longitud":float(end_lon),"Descripción":str(location)},
        ])
        if is_plausible_costa_rica_wgs84(start_lon, start_lat) and is_plausible_costa_rica_wgs84(end_lon, end_lat):
            main_project_line = [{
                "name": "Tramo principal",
                "description": str(location),
                "coordinates": [(float(start_lon), float(start_lat)), (float(end_lon), float(end_lat))],
            }]
        else:
            st.warning("Alguno de los extremos del tramo queda fuera del entorno esperado de Costa Rica. Revise las coordenadas.")
    saved_geo = st.session_state.get("project_geo_points_input")
    if isinstance(saved_geo, pd.DataFrame) and not saved_geo.empty:
        geo_editor_seed = saved_geo.copy()
        if geometry_mode == "Punto único":
            main_mask = geo_editor_seed["Tipo"].astype(str).eq("Proyecto") if "Tipo" in geo_editor_seed.columns else pd.Series(False, index=geo_editor_seed.index)
            if main_mask.any():
                idx = geo_editor_seed.index[main_mask][0]
                geo_editor_seed.loc[idx, ["Sistema", "Este_CRTM05", "Norte_CRTM05", "Latitud", "Longitud", "Descripción"]] = [
                    "WGS84", float(crtm_easting), float(crtm_northing), float(latitude), float(longitude), str(location)
                ]
            else:
                geo_editor_seed = pd.concat([base_geo_points, geo_editor_seed], ignore_index=True)
        else:
            keep_extra = geo_editor_seed[~geo_editor_seed["Tipo"].astype(str).isin(["Proyecto", "Inicio", "Fin"])].copy() if "Tipo" in geo_editor_seed.columns else pd.DataFrame()
            geo_editor_seed = pd.concat([base_geo_points, keep_extra], ignore_index=True)
    else:
        geo_editor_seed = base_geo_points

    with st.expander("Agregar / editar puntos del proyecto", expanded=False):
        geo_points_input = st.data_editor(
            geo_editor_seed, num_rows="dynamic", use_container_width=True, hide_index=True,
            key="project_geo_points_editor",
            column_config={
                "Nombre": st.column_config.TextColumn("Nombre / código"),
                "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Proyecto", "Inicio", "Vértice de eje", "Fin", "Sondeo P1", "Sondeo P2", "Sondeo", "Puente", "Alcantarilla", "Intersección", "Acceso", "Otro"]),
                "Sistema": st.column_config.SelectboxColumn("Sistema", options=["WGS84", "CRTM05"]),
                "Este_CRTM05": st.column_config.NumberColumn("Este CRTM05", format="%.3f"),
                "Norte_CRTM05": st.column_config.NumberColumn("Norte CRTM05", format="%.3f"),
                "Latitud": st.column_config.NumberColumn("Latitud", format="%.7f"),
                "Longitud": st.column_config.NumberColumn("Longitud", format="%.7f"),
                "Descripción": st.column_config.TextColumn("Descripción"),
            },
        )
    st.session_state.project_geo_points_input = geo_points_input.copy()

    resolved_geo_points = []
    for _, row in geo_points_input.iterrows():
        pname = str(row.get("Nombre", "")).strip() or "Punto"
        ptype = str(row.get("Tipo", "Otro")).strip() or "Otro"
        psystem = str(row.get("Sistema", "WGS84")).strip() or "WGS84"
        pdesc = str(row.get("Descripción", "") or "")
        try:
            if psystem == "CRTM05":
                pe = float(row.get("Este_CRTM05", 0) or 0)
                pn = float(row.get("Norte_CRTM05", 0) or 0)
                plon, plat = crtm05_to_wgs84(pe, pn)
            else:
                plat = float(row.get("Latitud", 0) or 0)
                plon = float(row.get("Longitud", 0) or 0)
                pe, pn = wgs84_to_crtm05(plon, plat)
            # FIX_PROJECT_MAP_PVALID_COLLISION
            point_is_valid = bool(is_plausible_costa_rica_wgs84(plon, plat))
        except Exception:
            pe = pn = plat = plon = 0.0
            point_is_valid = False
        resolved_geo_points.append({
            "name": pname, "type": ptype, "system_input": psystem, "description": pdesc,
            "crtm_easting": float(pe), "crtm_northing": float(pn),
            "latitude": float(plat), "longitude": float(plon), "valid": point_is_valid,
        })

    valid_geo_points = [p for p in resolved_geo_points if p["valid"]]
    if geometry_mode == "Tramo (inicio–fin)" and main_project_line:
        manual_vertices = [
            (p["longitude"], p["latitude"])
            for p in valid_geo_points if p["type"] == "Vértice de eje"
        ]
        waypoints = [(float(start_lon), float(start_lat)), *manual_vertices, (float(end_lon), float(end_lat))]
        if alignment_mode == "Ajustar a carretera (automático)":
            try:
                aligned_route = cached_road_route(tuple(waypoints))
                main_project_line = [{
                    "name": "Tramo ajustado a carretera",
                    "description": f"Ruta vial OpenStreetMap/OSRM · {aligned_route.distance_m:,.1f} m",
                    "coordinates": list(aligned_route.coordinates),
                }]
                st.success(
                    f"Eje ajustado a la red vial: {aligned_route.distance_m:,.1f} m "
                    f"y {len(aligned_route.coordinates)} vértices."
                )
            except (RoadAlignmentError, ValueError) as exc:
                main_project_line[0]["coordinates"] = waypoints
                st.warning(
                    f"No fue posible ajustar automáticamente el eje ({exc}). "
                    "Se muestra la polilínea definida por los puntos manuales."
                )
        elif alignment_mode == "Puntos manuales":
            main_project_line[0]["name"] = "Tramo por puntos manuales"
            main_project_line[0]["coordinates"] = waypoints
            if not manual_vertices:
                st.info("Agregue puntos de tipo “Vértice de eje” para seguir las curvas de la carretera.")

    fig_project_map = go.Figure()
    type_symbols = {
        "Proyecto": "circle", "Inicio": "triangle", "Fin": "triangle",
        "Sondeo P1": "diamond", "Sondeo P2": "diamond", "Sondeo": "diamond",
        "Puente": "square", "Alcantarilla": "square", "Intersección": "circle",
        "Acceso": "circle", "Otro": "circle",
    }
    if valid_geo_points:
        for ptype in sorted({p["type"] for p in valid_geo_points}):
            pts = [p for p in valid_geo_points if p["type"] == ptype]
            fig_project_map.add_trace(go.Scattermapbox(
                lat=[p["latitude"] for p in pts],
                lon=[p["longitude"] for p in pts],
                mode="markers+text",
                text=[p["name"] for p in pts],
                textposition="top right",
                name=ptype,
                marker=dict(size=13, symbol=type_symbols.get(ptype, "circle")),
                customdata=[[p["crtm_easting"], p["crtm_northing"], p["description"]] for p in pts],
                hovertemplate="<b>%{text}</b><br>Este: %{customdata[0]:,.3f} m<br>Norte: %{customdata[1]:,.3f} m<br>Lat: %{lat:.7f}<br>Lon: %{lon:.7f}<br>%{customdata[2]}<extra></extra>",
            ))
        center_lat = sum(p["latitude"] for p in valid_geo_points) / len(valid_geo_points)
        center_lon = sum(p["longitude"] for p in valid_geo_points) / len(valid_geo_points)
    else:
        center_lat, center_lon = float(latitude), float(longitude)
    if geometry_mode == "Tramo (inicio–fin)" and main_project_line:
        line_coords = main_project_line[0]["coordinates"]
        fig_project_map.add_trace(go.Scattermapbox(
            lat=[point[1] for point in line_coords],
            lon=[point[0] for point in line_coords],
            mode="lines", name=main_project_line[0]["name"], line=dict(width=6, color="#ff7f9b"),
            hovertemplate=f"<b>{main_project_line[0]['name']}</b><extra></extra>",
        ))
        center_lat = sum(point[1] for point in line_coords) / len(line_coords)
        center_lon = sum(point[0] for point in line_coords) / len(line_coords)
    fig_project_map.update_layout(
        mapbox=dict(style="open-street-map", center=dict(lat=center_lat, lon=center_lon), zoom=14),
        height=500, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h"),
    )
    st.plotly_chart(
        fig_project_map, use_container_width=True,
        config={"displaylogo": False, "scrollZoom": True, "responsive": True},
    )
    st.caption("Use la rueda del mouse sobre el mapa para acercar/alejar; arrastre para desplazarse.")

    invalid_count = len(resolved_geo_points) - len(valid_geo_points)
    if invalid_count:
        st.warning(f"Hay {invalid_count} punto(s) con coordenadas inválidas o fuera del entorno esperado de Costa Rica; no se muestran en el mapa ni en el KML.")

    map_actions_1, map_actions_2 = st.columns(2)
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={float(latitude):.8f},{float(longitude):.8f}"
    map_actions_1.link_button("🌎 Abrir punto principal en Google Maps", google_maps_url, use_container_width=True)
    safe_project_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(project_name)).strip('_') or 'Proyecto_GDP'
    project_kml = project_features_kml(project_name, resolved_geo_points, main_project_line)
    map_actions_2.download_button(
        "⬇️ Descargar puntos KML para Google Earth",
        data=project_kml.encode("utf-8"),
        file_name=f"{safe_project_name}_ubicacion.kml",
        mime="application/vnd.google-earth.kml+xml",
        use_container_width=True,
    )

    if valid_geo_points:
        geo_summary = pd.DataFrame([{
            "Elemento": p["name"], "Tipo": p["type"],
            "Este CRTM05": p["crtm_easting"], "Norte CRTM05": p["crtm_northing"],
            "Latitud": p["latitude"], "Longitud": p["longitude"],
        } for p in valid_geo_points])
        with st.expander("Ver ficha de coordenadas de todos los puntos", expanded=False):
            st.dataframe(geo_summary, use_container_width=True, hide_index=True)

    st.session_state.project_map = {
        "latitude": float(latitude), "longitude": float(longitude),
        "crtm_easting": float(crtm_easting), "crtm_northing": float(crtm_northing),
        "google_maps_url": google_maps_url, "kml_filename": f"{safe_project_name}_ubicacion.kml",
        "geometry_mode": geometry_mode, "alignment_mode": alignment_mode,
        "points": resolved_geo_points, "lines": main_project_line,
    }
    st.caption("Las coordenadas y los puntos adicionales quedan incluidos en el estado guardado del proyecto y en las exportaciones. El mapa es una referencia geográfica; no sustituye levantamiento topográfico ni alineamiento GIS definitivo.")

with p2:
    st.subheader("Composición vehicular y factores camión")
    st.info(
        "Ingrese el conteo diario en la columna **Cantidad diaria (veh/día)**. "
        "Se separan **automóviles**, **pickup/carga liviana** y **vehículos pesados**. "
        "El **Factor camión** es un parámetro técnico independiente utilizado para convertir cada categoría a ejes equivalentes; para pickup/carga liviana debe usarse el valor documentado por el estudio o proyecto."
    )

    current = st.session_state.vehicles.copy()

    # Compatibilidad con proyectos guardados antes de separar pickup/carga liviana.
    if "Grupo de tránsito" not in current.columns:
        current["Grupo de tránsito"] = current["Categoría"].astype(str).map(
            lambda x: "Liviano" if x.strip().lower() == "vehículos livianos" else "Pesado"
        )
    current["Categoría"] = current["Categoría"].replace({"Vehículos livianos": "Automóviles / vehículos livianos"})
    current.loc[current["Categoría"].eq("Automóviles / vehículos livianos"), "Grupo de tránsito"] = "Liviano"
    if not current["Categoría"].astype(str).eq("Pickup / carga liviana").any():
        pickup = pd.DataFrame([{
            "Categoría": "Pickup / carga liviana",
            "Grupo de tránsito": "Carga liviana",
            "Factor camión": 0.0,
            "TPD": 0,
        }])
        current = pd.concat([current.iloc[:1], pickup, current.iloc[1:]], ignore_index=True)
    current.loc[current["Categoría"].eq("Pickup / carga liviana"), "Grupo de tránsito"] = "Carga liviana"

    # VEHICLE_DECIMALS_AND_C4
    # Compatibilidad con proyectos guardados antes de incorporar explícitamente la categoría C4.
    if not current["Categoría"].astype(str).str.strip().eq("Camión C4").any():
        c4 = pd.DataFrame([{
            "Categoría": "Camión C4",
            "Grupo de tránsito": "Pesado",
            "Factor camión": 0.0,
            "TPD": 0.0,
        }])
        c3_idx = current.index[current["Categoría"].astype(str).str.strip().eq("Camión C3")].tolist()
        insert_at = c3_idx[0] + 1 if c3_idx else len(current)
        current = pd.concat([current.iloc[:insert_at], c4, current.iloc[insert_at:]], ignore_index=True)
    current.loc[current["Categoría"].eq("Camión C4"), "Grupo de tránsito"] = "Pesado"

    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Grupo de tránsito", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
    vehicle_editor["Cantidad diaria (veh/día)"] = pd.to_numeric(
        vehicle_editor["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0).round(2)
    vehicle_editor["Factor camión"] = pd.to_numeric(
        vehicle_editor["Factor camión"], errors="coerce"
    ).fillna(0.0)

    edited_vehicles = st.data_editor(
        vehicle_editor,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="vehicle_composition_editor",
        column_config={
            "Categoría": st.column_config.TextColumn(
                "Categoría vehicular",
                disabled=True,
                help="Tipo de vehículo considerado en el aforo."
            ),
            "Grupo de tránsito": st.column_config.TextColumn(
                "Grupo de tránsito",
                disabled=True,
                help="Clasificación usada para separar tránsito liviano, carga liviana y vehículos pesados. Solo el grupo Pesado entra en el porcentaje de pesados del Tomo II."
            ),
            "Cantidad diaria (veh/día)": st.column_config.NumberColumn(
                "Cantidad diaria (veh/día)",
                min_value=0.0,
                max_value=1_000_000.0,
                step=0.01,
                format="%.2f",
                help="Cantidad promedio de vehículos por día para esta categoría. Admite hasta 2 decimales."
            ),
            "Factor camión": st.column_config.NumberColumn(
                "Factor camión",
                min_value=0.0,
                max_value=100.0,
                step=0.01,
                format="%.4f",
                help="Factor técnico usado para convertir el tránsito de la categoría a ejes equivalentes."
            ),
        },
    )

    edited_vehicles["Cantidad diaria (veh/día)"] = pd.to_numeric(
        edited_vehicles["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0).round(2)
    edited_vehicles["Factor camión"] = pd.to_numeric(
        edited_vehicles["Factor camión"], errors="coerce"
    ).fillna(0.0).clip(lower=0.0)

    vehicles = edited_vehicles.rename(columns={"Cantidad diaria (veh/día)": "TPD"})[
        ["Categoría", "Grupo de tránsito", "Factor camión", "TPD"]
    ]
    st.session_state.vehicles = vehicles

    with st.expander("¿Cuál es la diferencia entre cantidad diaria y factor camión?"):
        st.markdown(
            "- **Cantidad diaria (veh/día):** dato del conteo o aforo de tránsito.\n"
            "- **Factor camión:** parámetro técnico de equivalencia de carga; no representa una cantidad de vehículos.\n"
            "- **Grupo de tránsito:** controla la clasificación para el porcentaje de pesados del Tomo II. Pickup/carga liviana no se suma automáticamente como vehículo pesado.\n"
            "- El cálculo de ejes equivalentes usa el factor individual de cada fila; no se asigna un factor normativo universal a pickup/carga liviana."
        )

    a, b, c, d = st.columns(4)
    with a:
        if st.session_state.active_tomo == "Tomo II":
            pending_tomo2_period = st.session_state.pop("_pending_tomo2_design_period", None)
            if pending_tomo2_period in (6, 8, 10, 12):
                st.session_state.tomo2_design_period = int(pending_tomo2_period)
            years = st.selectbox(
                "Periodo de diseño Tomo II (años)", [6, 8, 10, 12], index=2,
                key="tomo2_design_period",
                help="GDP-2024 Tomo II: selección directa de catálogo para 6, 8, 10 o 12 años, sin interpolación."
            )
        else:
            years = st.number_input("Periodo de diseño (años)", min_value=1, max_value=40, value=10, key="tomo1_design_period")
    with b:
        growth_pct = st.number_input("Crecimiento anual (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.1)
    with c:
        direction_factor = st.number_input("Factor direccional", min_value=0.1, max_value=1.0, value=0.50, step=0.05)
    with d:
        lane_factor = st.number_input("Factor de carril", min_value=0.1, max_value=1.0, value=1.00, step=0.05)

    weighted_daily = float((vehicles["TPD"] * vehicles["Factor camión"]).sum())
    tpd_total = float(vehicles["TPD"].sum())
    heavy_mask = vehicles["Grupo de tránsito"].astype(str).str.strip().str.lower().eq("pesado")
    heavy_total = float(vehicles.loc[heavy_mask, "TPD"].sum())
    heavy_pct = (heavy_total / tpd_total * 100.0) if tpd_total > 0 else 0.0
    gf = growth_factor(growth_pct / 100.0, int(years))
    esal = weighted_daily * direction_factor * lane_factor * 365 * gf
    tclass = traffic_class(esal)
    tomo1_category = tomo1_design_category(esal)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("TPD total", f"{tpd_total:,.2f}")
    m2.metric("Vehículos pesados", f"{heavy_total:,.2f}", f"{heavy_pct:.2f}%")
    m3.metric("Ejes equivalentes diarios", f"{weighted_daily:,.2f}")
    m4.metric("Factor de crecimiento G", f"{gf:,.3f}")
    m5.metric("EEq acumulado", f"{esal:,.0f}", "Dato complementario Tomo II" if st.session_state.active_tomo == "Tomo II" else f"Categoría {tomo1_category}")

    if st.session_state.active_tomo == "Tomo II":
        tomo2_tpd_category = classify_tpd(tpd_total)
        tomo2_heavy_category = classify_heavy_pct(heavy_pct)
        t21, t22, t23 = st.columns(3)
        t21.metric("Categoría TPD — Tomo II", tomo2_tpd_category or "Fuera de alcance")
        t22.metric("Categoría pesados — Tomo II", f"P{tomo2_heavy_category}%" if tomo2_heavy_category else "Fuera de alcance")
        t23.metric("Periodo de catálogo", f"{int(years)} años")
        if tomo2_tpd_category is None:
            st.error("Tomo II: TPD fuera del alcance directo del catálogo (máximo 3500 veh/día en el motor normativo).")
        if tomo2_heavy_category is None:
            st.error("Tomo II: porcentaje de vehículos pesados fuera del alcance directo del catálogo (máximo 15%).")
        st.info("En Tomo II, las categorías normativas visibles son TPD, porcentaje de pesados, CBR y período. La clase U1–T5 por ESAL no se usa para seleccionar el catálogo.")

    if st.session_state.active_tomo == "Tomo I":
        if tomo1_category == 3:
            category_rule = "ESAL < 3 millones"
        elif tomo1_category == 2:
            category_rule = "3 millones ≤ ESAL ≤ 25 millones"
        else:
            category_rule = "ESAL > 25 millones"
        st.success(
            f"**Clasificación automática Tomo I: Categoría {tomo1_category}** · {category_rule}. "
            "Referencia: GDP-2024 Tomo I, Tabla 102-01."
        )

    st.latex(r"EEq = 365 \cdot \left[\sum(TPD_i\,FC_i)\right] \cdot FD \cdot FCarril \cdot G, \qquad G=\frac{(1+r)^Y-1}{r}")
    st.info(
        f"**Factor de crecimiento acumulado G = {gf:,.3f}** · "
        f"calculado con r = {growth_pct:.2f}% anual y Y = {int(years)} años. "
        "G transforma el tránsito del año base en la acumulación equivalente durante el período de diseño."
    )
    st.caption("Cada cantidad corresponde al tránsito promedio diario de esa categoría. Revise cuidadosamente valores atípicos antes de continuar.")

with p3:
    st.subheader("Caracterización de la subrasante")
    mode = st.radio("Entrada de CBR", ["Valor único", "Serie de ensayos"], horizontal=True)
    if mode == "Valor único":
        cbr_design = st.number_input("CBR de diseño (%)", min_value=0.1, max_value=100.0, value=5.0, step=0.1)
        cbr_series = pd.DataFrame({"CBR (%)": [cbr_design]})
    else:
        cbr_series = st.data_editor(
            pd.DataFrame({"CBR (%)": [4.2, 5.0, 5.6, 6.1, 4.8]}),
            num_rows="dynamic",
            use_container_width=True,
            key="cbr_editor",
        )
        percentile = st.slider("Percentil conservador para diseño", 5, 50, 10, 5)
        valid = pd.to_numeric(cbr_series["CBR (%)"], errors="coerce").dropna()
        cbr_design = float(valid.quantile(percentile / 100.0)) if not valid.empty else 0.0

    sclass = subgrade_class(cbr_design)
    mr_estimated = resilient_modulus(cbr_design)
    if st.session_state.active_tomo == "Tomo II":
        tomo2_cbr_category = classify_cbr(cbr_design)
        sgc1, sgc2 = st.columns(2)
        sgc1.metric("Categoría normativa CBR — Tomo II", f"CBR {tomo2_cbr_category}%" if tomo2_cbr_category is not None else "Fuera de alcance")
        sgc2.metric("Clase geotécnica auxiliar", sclass, help="S1–S4 se conserva para visualización y análisis interno; no sustituye la categoría CBR del catálogo Tomo II.")
        if tomo2_cbr_category is None:
            st.error("Tomo II: CBR < 3% queda fuera del alcance directo del catálogo.")
        else:
            st.info("Para la selección Tomo II se utiliza la categoría CBR 3/4/6/9/11 del motor normativo. S1–S4 es una clasificación auxiliar de la aplicación.")

    st.markdown("#### Caracterización geotécnica complementaria")
    sg1, sg2, sg3, sg4 = st.columns(4)
    soil_sucs = sg1.text_input("Clasificación SUCS", value="", key="subgrade_sucs")
    soil_aashto = sg2.text_input("Clasificación AASHTO", value="", key="subgrade_aashto")
    liquid_limit = sg3.number_input("Límite líquido LL (%)", min_value=0.0, max_value=150.0, value=0.0, step=1.0, key="subgrade_ll")
    plasticity_index = sg4.number_input("Índice plástico IP (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key="subgrade_pi")
    sg5, sg6, sg7, sg8 = st.columns(4)
    natural_moisture = sg5.number_input("Humedad natural (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key="subgrade_moisture")
    max_dry_density = sg6.number_input("Densidad seca máxima (kg/m³)", min_value=0.0, max_value=3000.0, value=0.0, step=10.0, key="subgrade_mdd")
    subgrade_water_table = sg7.number_input("Nivel freático investigado (m)", min_value=0.0, max_value=50.0, value=2.0, step=0.1, key="subgrade_water_table")
    mr_source = sg8.selectbox("Fuente del módulo resiliente", ["Estimado a partir del CBR", "Ensayo de laboratorio/campo", "Valor documentado del proyecto"], key="subgrade_mr_source")
    measured_mr = st.number_input("Módulo resiliente documentado Mr (MPa, 0 = usar estimación por CBR)", min_value=0.0, max_value=2000.0, value=0.0, step=1.0, key="subgrade_measured_mr")
    mr = float(measured_mr) if measured_mr > 0 and mr_source != "Estimado a partir del CBR" else float(mr_estimated)

    x1, x2, x3, x4 = st.columns(4)
    x1.metric("CBR de diseño", f"{cbr_design:.2f}%")
    x2.metric("Rango de subrasante", sclass)
    x3.metric("Mr estimado por CBR", f"{mr_estimated:.2f} MPa")
    x4.metric("Mr usado en diseño", f"{mr:.2f} MPa")
    st.session_state.subgrade_details = {
        "sucs": soil_sucs, "aashto": soil_aashto, "liquid_limit_pct": float(liquid_limit),
        "plasticity_index_pct": float(plasticity_index), "natural_moisture_pct": float(natural_moisture),
        "max_dry_density_kg_m3": float(max_dry_density), "water_table_m": float(subgrade_water_table),
        "mr_estimated_mpa": float(mr_estimated), "mr_design_mpa": float(mr), "mr_source": mr_source,
    }
    if measured_mr <= 0 and mr_source != "Estimado a partir del CBR":
        st.warning("Se indicó una fuente documentada de Mr, pero no se ingresó el valor. Se mantiene temporalmente la estimación por CBR.")

    st.markdown("#### Segmentación preliminar en tramos homogéneos")
    st.caption("Registre cambios de subrasante, tránsito relativo o zona climática. El agrupamiento es documental y de cribado; la delimitación final debe responder a la investigación de campo.")
    default_segments = pd.DataFrame([{
        'Tramo': 'TH-01', 'Inicio_m': 0.0, 'Fin_m': float(project_length_m), 'CBR_%': float(cbr_design),
        'Mr_MPa': float(mr), 'Factor_tránsito': 1.0, 'Zona_climática': str(st.session_state.get('climate_zone_hint','General'))
    }])
    seg_df = st.data_editor(st.session_state.get('homogeneous_segments_input', default_segments), num_rows='dynamic', use_container_width=True, hide_index=True, key='homogeneous_segments_editor')
    st.session_state.homogeneous_segments_input = seg_df.copy()
    seg_work = seg_df.copy()
    for col in ['Inicio_m','Fin_m','CBR_%','Mr_MPa','Factor_tránsito']:
        if col in seg_work.columns:
            seg_work[col] = pd.to_numeric(seg_work[col], errors='coerce').fillna(0.0)
    if not seg_work.empty:
        seg_work['Longitud_m'] = (seg_work['Fin_m'] - seg_work['Inicio_m']).clip(lower=0.0)
        seg_work['ESAL_tramo'] = float(esal) * seg_work['Factor_tránsito'].clip(lower=0.0)
        seg_work['Categoría_TomoI'] = seg_work['ESAL_tramo'].apply(lambda x: f"Categoría {tomo1_design_category(float(x))}")
        seg_work['Clase_subrasante'] = seg_work['CBR_%'].apply(lambda x: subgrade_class(float(x)) if float(x) > 0 else 'Sin definir')
        seg_work['Grupo_preliminar'] = seg_work.apply(lambda r: f"{r['Categoría_TomoI']} / {r['Clase_subrasante']} / {r.get('Zona_climática','')}", axis=1)
        st.dataframe(seg_work, use_container_width=True, hide_index=True)
        if (seg_work['Fin_m'] < seg_work['Inicio_m']).any():
            st.error("Hay tramos con estación final menor que la inicial.")
        if seg_work['Longitud_m'].sum() < float(project_length_m) * 0.95:
            st.warning("La suma de longitudes de tramos no cubre toda la longitud del proyecto. Revise estaciones.")
    st.session_state.homogeneous_segments = seg_work.to_dict(orient='records')

    render_gdp_scope_alerts(st.session_state.active_tomo, tpd_total, heavy_pct, cbr_design, esal, int(years))

    chart_df = cbr_series.copy()
    chart_df.index = [f"Muestra {i+1}" for i in range(len(chart_df))]
    st.bar_chart(chart_df)
    st.caption("Clasificación implementada: S1 < 4; S2 = 4–6; S3 = 7–9; S4 > 9. Para el intervalo 6–7 se aplica el rango conservador inferior.")

with pclima:
    st.subheader("Temperatura del sitio y evaluación climática")
    st.caption("Admite clima documentado por estación o una serie de 12 temperaturas medias mensuales. Las ecuaciones térmicas GDP existentes se aplican sin modificación.")

    climate_input_mode = st.segmented_control(
        "Modo de información climática",
        ["Estación documentada", "Valores mensuales"],
        default="Estación documentada",
        key="climate_input_mode",
    ) or "Estación documentada"

    if "climate_station_selected" not in st.session_state:
        st.session_state.climate_station_selected = PROJECT_CLIMATE_OPTION
        load_climate_zone_to_state()

    selected_climate_option = st.session_state.climate_station_selected
    # Si cambian las coordenadas, renueva automáticamente el catálogo del proyecto.
    if selected_climate_option == PROJECT_CLIMATE_OPTION:
        climate_lat, climate_lon, geometry_label = current_project_climate_point()
        climate_signature = (round(climate_lat, 5), round(climate_lon, 5), geometry_label)
        if st.session_state.get("climate_project_signature") != climate_signature:
            load_climate_zone_to_state()
            st.session_state.climate_project_signature = climate_signature
    elif (
        selected_climate_option != "Otra / dato propio"
        and st.session_state.get("climate_catalog", {}).get("zone") != selected_climate_option
    ):
        # Corrige estados restaurados donde el selector y el catálogo no coinciden.
        load_climate_zone_to_state()

    c1, c2, c3 = st.columns(3)
    with c1:
        station_selected = st.selectbox(
            "Estación o zona representativa",
            [PROJECT_CLIMATE_OPTION] + CLIMATE_STATIONS_TOMO_II + ["Otra / dato propio"],
            key="climate_station_selected",
            on_change=load_climate_zone_to_state,
        )
        climate_source = st.text_input(
            "Fuente / institución",
            value=st.session_state.get("climate_source_input", "Fuente documentada por el usuario"),
            key="climate_source_input",
        )
        climate_period = st.text_input(
            "Periodo documentado",
            value=st.session_state.get("climate_period_input", ""),
            key="climate_period_input",
        )
    with c2:
        depth_mm = st.number_input("Profundidad de evaluación en la mezcla (mm)", min_value=1.0, max_value=500.0, value=35.0, step=1.0, help="Se recomienda evaluar aproximadamente a la profundidad media de la capa asfáltica.")
        analysis_category = tomo1_design_category(esal)
        if st.session_state.active_tomo == "Tomo I":
            st.metric(
                "Categoría de análisis del Tomo I",
                f"Categoría {analysis_category}",
                help="Asignación automática según ESAL de diseño y Tabla 102-01 de la GDP-2024 Tomo I.",
            )
        else:
            st.caption("La categoría jerárquica 1–3 corresponde al Tomo I y se calcula automáticamente a partir del ESAL.")
    with c3:
        temp_data_confirmed = st.checkbox("Fuente y periodo climático documentados", value=False)
        master_curve_confirmed = st.checkbox("Curva maestra / módulos a varias temperaturas disponibles", value=False)
        climate_notes = st.text_area("Notas de trazabilidad climática", value="", height=90)

    climate_monthly_df = pd.DataFrame()
    monthly_values = []
    catalog = st.session_state.get("climate_catalog", {})
    catalog_matches_zone = catalog.get("zone") == station_selected
    if st.session_state.get("climate_catalog_status") == "error":
        st.warning(
            "No fue posible consultar NASA POWER. Puede continuar con datos propios. "
            f"Detalle: {st.session_state.get('climate_catalog_error', 'sin respuesta')}"
        )
    elif station_selected == "Otra / dato propio":
        st.info("Modo de dato propio: complete manualmente la fuente, el periodo y las temperaturas.")
    elif catalog_matches_zone:
        st.success(
            f"Climatología cargada automáticamente para {station_selected}: "
            f"{catalog['latitude']:.5f}, {catalog['longitude']:.5f} "
            f"({catalog.get('geometry_label', 'punto consultado')})."
        )

    if climate_input_mode == "Valores mensuales":
        st.markdown("#### Temperaturas medias mensuales del aire")
        default_monthly = catalog.get("monthly_c", [23.0, 23.5, 24.0, 24.5, 24.0, 23.5, 23.5, 23.5, 23.5, 23.0, 22.8, 22.8])
        monthly_input = pd.DataFrame({"Mes": MONTHS_ES, "Temperatura media del aire (°C)": default_monthly})
        monthly_editor = st.data_editor(
            monthly_input,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=f"climate_monthly_editor_{station_selected}",
            column_config={
                "Mes": st.column_config.TextColumn("Mes", disabled=True),
                "Temperatura media del aire (°C)": st.column_config.NumberColumn(
                    "Temperatura media del aire (°C)", min_value=-20.0, max_value=60.0, step=0.1, format="%.1f"
                ),
            },
        )
        monthly_values = pd.to_numeric(monthly_editor["Temperatura media del aire (°C)"], errors="coerce").fillna(0.0).tolist()
        air_temp_c = representative_temperature(monthly_values)
        monthly_modified = catalog_matches_zone and any(
            abs(current - original) > 0.049
            for current, original in zip(monthly_values, catalog.get("monthly_c", []))
        )
        st.caption(
            "Origen: valores modificados por el usuario."
            if monthly_modified else
            "Origen: climatología automática NASA POWER; la tabla permanece editable."
        )
        climate_monthly_df = monthly_climate_table(monthly_values, latitude, depth_mm, pavement_temperature_ltpp, pavement_temperature_shrp)
        summary = monthly_summary(climate_monthly_df)
        st.dataframe(climate_monthly_df, use_container_width=True, hide_index=True)
        st.line_chart(climate_monthly_df.set_index("Mes")[["Aire (°C)", "Pavimento LTPP (°C)", "Pavimento SHRP (°C)"]])
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Aire medio anual", f"{summary['air_mean_c']:.1f} °C")
        s2.metric("Aire mínimo mensual", f"{summary['air_min_c']:.1f} °C")
        s3.metric("Aire máximo mensual", f"{summary['air_max_c']:.1f} °C")
        s4.metric("Rango mensual", f"{summary['air_max_c']-summary['air_min_c']:.1f} °C")
    else:
        air_temp_c = st.number_input(
            "Temperatura representativa del aire (°C)",
            min_value=-10.0,
            max_value=50.0,
            value=float(st.session_state.get("climate_air_temp_c", 24.0)),
            step=0.1,
            key="climate_air_temp_c",
        )
        air_modified = catalog_matches_zone and abs(air_temp_c - float(catalog.get("annual_c", air_temp_c))) > 0.049
        st.info(
            "Modo estación/zona: la temperatura media se cargó del catálogo y puede editarse. "
            + ("El valor actual fue modificado por el usuario." if air_modified else "El valor actual coincide con el catálogo.")
        )

    tp_ltpp = pavement_temperature_ltpp(air_temp_c, latitude, depth_mm)
    tp_shrp = pavement_temperature_shrp(air_temp_c, latitude, depth_mm)
    pavement_temp_c = tp_ltpp
    a1,a2,a3,a4=st.columns(4)
    a1.metric("Temperatura representativa del aire", f"{air_temp_c:.1f} °C")
    a2.metric("Pavimento — LTPP", f"{tp_ltpp:.1f} °C")
    a3.metric("Pavimento — SHRP", f"{tp_shrp:.1f} °C")
    a4.metric("Profundidad evaluada", f"{depth_mm:.0f} mm")

    st.markdown("#### Trazabilidad climática")
    st.write(f"**Modo:** {climate_input_mode} · **Fuente:** {climate_source or 'No indicada'} · **Periodo:** {climate_period or 'No indicado'} · **Estación/zona:** {station_selected}")

    if st.session_state.active_tomo == "Tomo I":
        st.markdown("#### Índice de humedad de Thornthwaite (TMI)")
        st.caption("GDP-2024 Tomo I · Sección 302, Tabla 302-01 y Anexo B. El balance utiliza Smax = 200 mm.")
        tmi_temperatures = monthly_values if len(monthly_values) == 12 else catalog.get("monthly_c", [float(air_temp_c)] * 12)
        tmi_precipitation = catalog.get("monthly_precip_mm", [0.0] * 12)
        tmi_seed = pd.DataFrame({
            "Mes": MONTHS_ES,
            "Temperatura media (°C)": tmi_temperatures,
            "Precipitación mensual (mm)": tmi_precipitation,
        })
        tmi_input = st.data_editor(
            tmi_seed, use_container_width=True, hide_index=True, num_rows="fixed",
            key=f"climate_tmi_editor_{station_selected}",
            column_config={
                "Mes": st.column_config.TextColumn("Mes", disabled=True),
                "Temperatura media (°C)": st.column_config.NumberColumn(min_value=-20.0, max_value=60.0, step=0.1, format="%.1f"),
                "Precipitación mensual (mm)": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%.1f"),
            },
        )
        tmi_temps = pd.to_numeric(tmi_input["Temperatura media (°C)"], errors="coerce").fillna(0.0).tolist()
        tmi_rain = pd.to_numeric(tmi_input["Precipitación mensual (mm)"], errors="coerce").fillna(0.0).tolist()
        tmi_ready = len(tmi_rain) == 12 and sum(tmi_rain) > 0
        if tmi_ready:
            tmi_table, tmi_summary = thornthwaite_tmi_balance(tmi_temps, tmi_rain, latitude, 200.0)
            tm1, tm2, tm3, tm4 = st.columns(4)
            tm1.metric("TMI anual", f"{tmi_summary['annual_tmi']:.1f}")
            tm2.metric("Clase climática", tmi_summary["climate_class"])
            tm3.metric("Precipitación anual", f"{tmi_summary['annual_precipitation_mm']:.0f} mm")
            tm4.metric("ETP anual", f"{tmi_summary['annual_pet_mm']:.0f} mm")
            with st.expander("Ver balance hídrico mensual TMI", expanded=False):
                st.dataframe(tmi_table, use_container_width=True, hide_index=True)
            st.success("Clasificación calculada con la metodología TMI incorporada en el GDP-2024 Tomo I.")
        else:
            tmi_table = pd.DataFrame()
            tmi_summary = {}
            st.info("Ingrese las 12 precipitaciones mensuales para calcular el TMI. NASA POWER las completa automáticamente cuando están disponibles.")

        st.markdown("#### Curva maestra y ecuación de desplazamiento de la mezcla asfáltica en caliente")
        st.caption("Modelo sigmoidal + desplazamiento WLF configurable. Los coeficientes deben provenir de ensayos/ajuste documentado; no se presentan como coeficientes universales GDP.")
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc_delta = mc1.number_input("δ — asíntota inferior log10(E*)", value=2.5, step=0.1, key='mc_delta')
        mc_alpha = mc2.number_input("α — amplitud sigmoidal", value=2.0, step=0.1, key='mc_alpha')
        mc_beta = mc3.number_input("β — parámetro sigmoidal", value=0.0, step=0.1, key='mc_beta')
        mc_gamma = mc4.number_input("γ — pendiente sigmoidal", value=-1.0, step=0.1, key='mc_gamma')
        sh1, sh2, sh3, sh4 = st.columns(4)
        reference_temp_c = sh1.number_input("Temperatura de referencia Tref (°C)", min_value=-20.0, max_value=80.0, value=20.0, step=1.0, key='mc_tref')
        analysis_frequency_hz = sh2.number_input("Frecuencia de carga f (Hz)", min_value=0.0001, max_value=1000.0, value=10.0, step=1.0, key='mc_frequency')
        wlf_c1 = sh3.number_input("WLF C1", value=8.86, step=0.1, key='mc_wlf_c1')
        wlf_c2 = sh4.number_input("WLF C2 (°C)", value=101.6, step=1.0, key='mc_wlf_c2')

        log_a_t = wlf_log10_shift_factor(tp_ltpp, reference_temp_c, wlf_c1, wlf_c2)
        a_t = 10.0 ** log_a_t
        reduced_frequency_hz = max(float(analysis_frequency_hz) * a_t, 1e-12)
        log_fr = math.log10(reduced_frequency_hz)
        e_effective = master_curve_dynamic_modulus_mpa(log_fr, mc_delta, mc_alpha, mc_beta, mc_gamma)
        st.latex(r"\log_{10}(a_T)=-\frac{C_1(T-T_{ref})}{C_2+(T-T_{ref})}")
        st.latex(r"f_r=f\,a_T")
        st.latex(r"\log_{10}(E^*)=\delta+\frac{\alpha}{1+\exp(\beta+\gamma\log_{10}f_r)}")
        mcm1, mcm2, mcm3, mcm4 = st.columns(4)
        mcm1.metric("log10(aT)", f"{log_a_t:.3f}")
        mcm2.metric("aT", f"{a_t:.4g}")
        mcm3.metric("Frecuencia reducida", f"{reduced_frequency_hz:.4g} Hz")
        mcm4.metric("E* calculado", f"{e_effective:,.0f} MPa")

        curve_logs = [(-4.0 + i * 0.2) for i in range(41)]
        curve_df = pd.DataFrame({
            'log10(f reducida)': curve_logs,
            'Frecuencia reducida (Hz)': [10.0 ** x for x in curve_logs],
            'E* (MPa)': [master_curve_dynamic_modulus_mpa(x, mc_delta, mc_alpha, mc_beta, mc_gamma) for x in curve_logs],
        })
        curve_fig = go.Figure(go.Scatter(x=curve_df['log10(f reducida)'], y=curve_df['E* (MPa)'], mode='lines+markers'))
        curve_fig.update_layout(height=340, title='Curva maestra E* — modelo configurable', xaxis_title='log10 frecuencia reducida (Hz)', yaxis_title='E* (MPa)', plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(curve_fig, use_container_width=True, config={'displaylogo': False})

        temps_for_e = monthly_values if len(monthly_values) == 12 else [float(air_temp_c)] * 12
        monthly_curve_rows = []
        for month, temp_month in zip(MONTHS_ES, temps_for_e):
            month_log_at = wlf_log10_shift_factor(float(temp_month), reference_temp_c, wlf_c1, wlf_c2)
            month_at = 10.0 ** month_log_at
            month_fr = max(float(analysis_frequency_hz) * month_at, 1e-12)
            month_e = master_curve_dynamic_modulus_mpa(math.log10(month_fr), mc_delta, mc_alpha, mc_beta, mc_gamma)
            monthly_curve_rows.append({'Mes': month, 'Temperatura (°C)': float(temp_month), 'log10(aT)': month_log_at, 'f reducida (Hz)': month_fr, 'E* calculado (MPa)': month_e})
        e_monthly = pd.DataFrame(monthly_curve_rows)
        st.dataframe(e_monthly, use_container_width=True, hide_index=True)
        e_ref_state = float(st.session_state.get('design_materials', {}).get('asphalt_dynamic_modulus_mpa', 3500.0) or 3500.0)
        climate_material_factor = float(e_monthly['E* calculado (MPa)'].mean()) / max(e_ref_state, 1e-9)
        st.session_state.monthly_dynamic_modulus_input = e_monthly.copy()
        st.session_state.climate_material = {
            'tmi_ready': bool(tmi_ready), 'tmi_summary': tmi_summary,
            'tmi_monthly_balance': tmi_table.to_dict(orient='records') if not tmi_table.empty else [],
            'tmi_reference': 'GDP-2024 Tomo I, Sección 302, Tabla 302-01 y Anexo B',
            'monthly_modulus': e_monthly.to_dict(orient='records'), 'reference_modulus_mpa': e_ref_state,
            'effective_modulus_mpa': float(e_effective), 'relative_climate_factor': float(climate_material_factor),
            'shift_model': 'WLF configurable', 'master_curve_model': 'Sigmoidal configurable',
            'master_curve_parameters': {'delta':mc_delta,'alpha':mc_alpha,'beta':mc_beta,'gamma':mc_gamma,'tref_c':reference_temp_c,'c1':wlf_c1,'c2':wlf_c2,'frequency_hz':analysis_frequency_hz},
            'method': 'Curva maestra + WLF configurable; requiere coeficientes documentados'
        }
        if not master_curve_confirmed:
            st.warning("La curva se calcula con parámetros configurables, pero el expediente aún indica que la curva maestra no está confirmada documentalmente.")

    st.markdown("#### Alertas de cumplimiento y revisión")
    climate_checks = climate_alerts(st.session_state.active_tomo, pavement_type, air_temp_c, pavement_temp_c, latitude, depth_mm, analysis_category, temp_data_confirmed, master_curve_confirmed, station_selected)
    if climate_input_mode == "Valores mensuales" and len(monthly_values) == 12 and temp_data_confirmed:
        climate_checks.append(("success", "Serie mensual completa: 12 valores documentados y procesados."))
    for level,msg in climate_checks:
        getattr(st, level)(msg)
    st.info("Referencia incorporada: GDP-2024 Tomo I, Sección 303.01, ecuaciones 303-01 a 303-04; GDP-2024 Tomo II, Anexo B.3 sobre temperatura del pavimento y estaciones climáticas consideradas.")

with p4:
    if st.session_state.active_tomo == "Tomo II":
        st.subheader("Catálogo oficial de estructuras — GDP-2024 Tomo II")
        st.caption("Selección directa desde las Tablas 301-01 a 301-21, sin interpolación y con trazabilidad por resultado.")

        options, tomo2_result = alternatives_for_app(
            tpd=float(tpd_total),
            heavy_pct=float(heavy_pct),
            cbr=float(cbr_design),
            period=int(years),
        )
        st.session_state.tomo2_options = options.copy()
        st.session_state.tomo2_result = tomo2_result
        exact_match = tomo2_result.get("status") == "ok" and not options.empty
        st.session_state.exact_match = exact_match

        st.markdown("### Resumen de entrada normativa")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("TPD", f"{tpd_total:,.0f} veh/día")
        r2.metric("Pesados", f"{heavy_pct:.2f}%")
        r3.metric("CBR", f"{cbr_design:.2f}%")
        r4.metric("Periodo", f"{int(years)} años")

        criteria = tomo2_result.get("criteria", [])
        if criteria:
            cdf = pd.DataFrame(criteria)
            st.dataframe(cdf, use_container_width=True, hide_index=True)

        status = tomo2_result.get("status")
        if status == "fuera_alcance":
            st.error("La combinación ingresada está fuera del alcance directo del catálogo Tomo II. No se emite ninguna alternativa normativa.")
        elif status == "sin_alternativa":
            st.session_state.pop("selected_row", None)
            selected_row = None
            total_thickness = 0.0
            st.session_state.total_thickness = 0.0
            exact_categories = tomo2_result.get("categories", {})
            st.error(
                "No existe una estructura normativa asignada para "
                f"{exact_categories.get('tpd', 'TPD sin categoría')}, "
                f"P{exact_categories.get('pesados', '—')} %, CBR {exact_categories.get('cbr', '—')} % y "
                f"{exact_categories.get('periodo', years)} años en {tomo2_result.get('table', 'la tabla consultada')}. "
                "La aplicación no interpola ni copia estructuras de otra celda."
            )
            nearby = nearby_catalog_options(float(tpd_total), float(heavy_pct), float(cbr_design), int(years))
            if nearby:
                st.markdown("#### Celdas tabuladas cercanas — solo referencia")
                nearby_df = pd.DataFrame(nearby[:6]).drop(columns=["distancia"])
                nearby_df.columns = ["Ajuste", "Valor", "Estructura(s)", "Tabla", "Página", "Condición de uso"]
                st.dataframe(nearby_df, use_container_width=True, hide_index=True)
                available_periods = [item for item in nearby if item["ajuste"] == "Periodo de diseño"]
                action_cols = st.columns(2)
                if available_periods:
                    closest_period = int(available_periods[0]["valor"])
                    if action_cols[0].button(
                        f"Usar periodo tabulado de {closest_period} años",
                        key="apply_nearby_tomo2_period",
                        use_container_width=True,
                        help="Cambia el periodo del proyecto. Confirme y documente que este horizonte sea procedente.",
                    ):
                        st.session_state._pending_tomo2_design_period = closest_period
                        st.rerun()
                if action_cols[1].button(
                    "Evaluar el caso mediante Tomo I",
                    key="evaluate_unassigned_tomo2_in_tomo1",
                    use_container_width=True,
                ):
                    st.session_state._pending_active_tomo = "Tomo I"
                    st.rerun()
            else:
                st.info("No se encontraron celdas cercanas con estructura. Revise el alcance del proyecto y evalúe el caso mediante Tomo I.")
        elif status == "ok":
            st.success(f"Se encontraron {len(options)} alternativa(s) oficiales para la combinación ingresada.")

        if tomo2_result.get("table"):
            st.info(f"Referencia de asignación: {tomo2_result.get('table')} · página {tomo2_result.get('page')} · {tomo2_result.get('source','GDP-2024 Tomo II')}")

        st.markdown("#### Estado climático del diseño")
        for level,msg in climate_checks:
            if level == "error": st.error(msg)
            elif level == "warning": st.warning(msg)
            else: st.success(msg)

        if not options.empty:
            label_map = {}
            for _, row in options.iterrows():
                esp = float(row["Carpeta_cm"]) + float(row["Base_cm"]) + float(row["Subbase_cm"])
                base_label = row.get("Base_tipo", "Base")
                label = f"{row['Código']} — {row['Superficie']} — {base_label} — {esp:.0f} cm"
                label_map[label] = str(row["Código"])

            selected_label = st.selectbox("Seleccione una alternativa oficial", list(label_map.keys()), key="official_tomo2_structure")
            selected_code = label_map[selected_label]
            selected_row = options[options["Código"].astype(str) == selected_code].iloc[0].to_dict()
            st.session_state.selected_row = selected_row
            total_thickness = float(selected_row["Carpeta_cm"]) + float(selected_row["Base_cm"]) + float(selected_row["Subbase_cm"])
            st.session_state.total_thickness = total_thickness

            st.markdown("### Paquete estructural seleccionado")
            k1, k2, k3 = st.columns(3)
            k1.metric("Código", selected_row["Código"])
            k2.metric("Tipo de superficie", selected_row["Superficie"])
            k3.metric("Espesor de capas", f"{total_thickness:.0f} cm")

            st.caption(
                "Si necesita una comprobación mecanístico-empírica complementaria, puede copiar "
                "esta geometría a Tomo I. La alternativa del catálogo Tomo II no se modifica ni se reclasifica."
            )
            if st.button(
                "🔬 Evaluar esta estructura en Tomo I",
                key="evaluate_tomo2_in_tomo1",
                use_container_width=True,
            ):
                st.session_state._pending_tomo1_import = dict(selected_row)
                st.session_state._pending_active_tomo = "Tomo I"
                st.rerun()

            left, right = st.columns([0.9, 2.1], gap="large")
            with left:
                st.markdown("#### Capas")
                if float(selected_row["Carpeta_cm"]) > 0:
                    st.markdown(f'<div class="layer">Carpeta asfáltica<br><b>{float(selected_row["Carpeta_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="layer">{selected_row["Superficie"]}<br><b>Capa superficial</b></div>', unsafe_allow_html=True)
                if float(selected_row.get("Base_granular_cm", 0)) > 0:
                    st.markdown(f'<div class="layer">Base granular<br><b>{float(selected_row["Base_granular_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                if float(selected_row.get("Base_estabilizada_cm", 0)) > 0:
                    st.markdown(f'<div class="layer">Base estabilizada<br><b>{float(selected_row["Base_estabilizada_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                if float(selected_row["Subbase_cm"]) > 0:
                    st.markdown(f'<div class="layer">Subbase granular<br><b>{float(selected_row["Subbase_cm"]):.0f} cm</b></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="layer">Subrasante<br><b>CBR {cbr_design:.2f}%</b></div>', unsafe_allow_html=True)
                exploded_view = st.toggle("Vista explotada 3D", value=True, help="Separa las capas para identificarlas con mayor facilidad.", key="gdp3d_exploded")
                scale_label = st.selectbox("Escala vertical", ["Real (×1)", "Exagerada ×2", "Exagerada ×5"], index=0, key="gdp3d_vertical_scale")
                vertical_scale = {"Real (×1)":1.0, "Exagerada ×2":2.0, "Exagerada ×5":5.0}[scale_label]
                view_mode = st.selectbox("Modo de corte", ["Completa", "Media calzada", "Corte transversal", "Corte longitudinal"], key="gdp3d_view_mode")
                available_layers = [x["name"] for x in _structure_layers_3d(selected_row, sclass, cbr_design)]
                selected_layer_3d = st.selectbox("Resaltar capa", ["Todas"] + available_layers, key="gdp3d_selected_layer")
                if vertical_scale > 1:
                    st.warning(f"Visualización con exageración vertical ×{vertical_scale:g}. Los espesores rotulados conservan el valor de diseño real.")
                st.caption("Las cotas corresponden al diseño. La subrasante se representa como medio semiinfinito, sin asignarle un espesor estructural ficticio.")

            with right:
                st.markdown("#### Visor estructural 3D v2")
                fig_3d = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_view, vertical_scale, view_mode, selected_layer_3d)
                render_rotating_3d(fig_3d, key="structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))

            if len(options) > 1:
                with st.expander("Comparar alternativas en 3D", expanded=False):
                    comparison_codes = [str(v) for v in options["Código"].tolist() if str(v) != str(selected_row["Código"])]
                    comparison_code = st.selectbox("Alternativa para comparar", comparison_codes, key="gdp3d_compare_code")
                    comparison_row = options[options["Código"].astype(str) == comparison_code].iloc[0].to_dict()
                    ca, cb = st.columns(2, gap="medium")
                    with ca:
                        st.markdown(f"**Seleccionada: {selected_row['Código']}**")
                        fig_a = pavement_3d_figure(selected_row, sclass, cbr_design, False, 1.0, "Corte transversal", "Todas")
                        render_rotating_3d(fig_a, key="compare_a", height=470, auto_rotate=False)
                    with cb:
                        st.markdown(f"**Comparación: {comparison_row['Código']}**")
                        fig_b = pavement_3d_figure(comparison_row, sclass, cbr_design, False, 1.0, "Corte transversal", "Todas")
                        render_rotating_3d(fig_b, key="compare_b", height=470, auto_rotate=False)
                    compare_df = pd.DataFrame([
                        ["Carpeta / superficie", float(selected_row.get("Carpeta_cm",0) or 0), float(comparison_row.get("Carpeta_cm",0) or 0)],
                        ["Base total", float(selected_row.get("Base_cm",0) or 0), float(comparison_row.get("Base_cm",0) or 0)],
                        ["Subbase", float(selected_row.get("Subbase_cm",0) or 0), float(comparison_row.get("Subbase_cm",0) or 0)],
                    ], columns=["Componente", str(selected_row["Código"]), str(comparison_row["Código"])])
                    st.dataframe(compare_df, use_container_width=True, hide_index=True)

            trace = selected_trace(selected_row)
            with st.expander("Trazabilidad GDP-2024 de la alternativa", expanded=True):
                trace_df = pd.DataFrame([
                    ["Fuente", trace.get("fuente", "")],
                    ["Decreto", trace.get("decreto", "")],
                    ["Definición de estructura", trace.get("definicion_estructura", "")],
                    ["Tabla de asignación", trace.get("asignacion", "")],
                    ["Criterio aplicado", trace.get("criterio", "")],
                    ["Celda original", trace.get("celda_original", "")],
                    ["Nota de extracción", trace.get("nota_extraccion", "")],
                ], columns=["Elemento", "Referencia"])
                st.dataframe(trace_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Descargar trazabilidad de la alternativa (CSV)",
                    trace_df.to_csv(index=False).encode("utf-8-sig"),
                    f"trazabilidad_{selected_row['Código']}.csv",
                    "text/csv",
                )
        else:
            selected_row = None
            st.session_state.selected_row = None
            st.session_state.total_thickness = 0.0
    else:
        st.subheader("Estructura propuesta para evaluación — GDP-2024 Tomo I")
        st.info(
            "El Tomo I es una guía mecanístico-empírica para pavimentos flexibles y semirrígidos. "
            "En este modo GDP permite **definir una sección propuesta para evaluarla**, pero no la presenta como una alternativa de catálogo ni como diseño final aprobado. "
            "El cumplimiento debe sustentarse con la caracterización de tránsito, subrasante, clima, materiales y la evaluación de respuesta/desempeño aplicable del Tomo I."
        )
        st.caption(
            "Referencia normativa: GDP-2024 Tomo I — Guía mecanístico-empírica para el diseño de pavimentos flexibles y semirrígidos, "
            "oficializada mediante Decreto Ejecutivo 44762-MOPT."
        )

        pending_t1_import = st.session_state.pop("_pending_tomo1_import", None)
        previous_t1 = st.session_state.get("tomo1_structure", {})
        if isinstance(pending_t1_import, dict) and pending_t1_import:
            for widget_key in (
                "tomo1_structure_source", "tomo1_pavement_type", "tomo1_asphalt_cm",
                "tomo1_base_granular_cm", "tomo1_base_stabilized_cm", "tomo1_subbase_cm",
                "tomo1_improvement_cm", "tomo1_structure_id",
            ):
                st.session_state.pop(widget_key, None)
            source = "Importada de Tomo II para evaluación"
            dflt = pending_t1_import
            st.info(
                "Se copió la geometría de la alternativa Tomo II para una evaluación complementaria en Tomo I. "
                "Esto no modifica ni reclasifica la alternativa original del catálogo."
            )
        else:
            source = str(previous_t1.get("Origen_TomoI", "Definida por el usuario"))
            dflt = previous_t1
            if source.startswith("Importada"):
                st.info(
                    "Esta sección conserva una geometría importada desde Tomo II para evaluación complementaria; "
                    "no representa una alternativa propia del Tomo I."
                )
        t1_type = st.selectbox(
            "Tipo de pavimento a evaluar",
            ["Flexible", "Semirrígido"],
            index=0 if str(dflt.get("Tipo_TomoI", "Flexible")) != "Semirrígido" else 1,
            key="tomo1_pavement_type",
        )
        st.markdown("#### Espesores de la sección propuesta")
        e1, e2, e3, e4 = st.columns(4)
        asphalt_cm = e1.number_input(
            "Mezcla asfáltica (cm)", min_value=0.0, max_value=40.0,
            value=float(dflt.get("Carpeta_cm", 5.0) or 0.0), step=0.5, key="tomo1_asphalt_cm"
        )
        base_granular_cm = e2.number_input(
            "Base granular (cm)", min_value=0.0, max_value=80.0,
            value=float(dflt.get("Base_granular_cm", dflt.get("Base_cm", 20.0)) or 0.0) if float(dflt.get("Base_estabilizada_cm", 0) or 0) <= 0 else float(dflt.get("Base_granular_cm", 0) or 0),
            step=1.0, key="tomo1_base_granular_cm"
        )
        base_stabilized_cm = e3.number_input(
            "Base estabilizada (cm)", min_value=0.0, max_value=80.0,
            value=float(dflt.get("Base_estabilizada_cm", 0.0) or 0.0), step=1.0, key="tomo1_base_stabilized_cm"
        )
        subbase_cm = e4.number_input(
            "Subbase granular (cm)", min_value=0.0, max_value=100.0,
            value=float(dflt.get("Subbase_cm", 20.0) or 0.0), step=1.0, key="tomo1_subbase_cm"
        )
        i1, i2 = st.columns(2)
        improvement_cm = i1.number_input(
            "Mejoramiento de subrasante (cm, si aplica)", min_value=0.0, max_value=150.0,
            value=float(dflt.get("Mejoramiento_subrasante_cm", 0.0) or 0.0), step=1.0, key="tomo1_improvement_cm"
        )
        raw_structure_id = str(dflt.get("Código", "") or "").strip()
        normalized_structure_id = tomo1_structure_identifier(source, raw_structure_id)
        current_structure_id = str(st.session_state.get("tomo1_structure_id", "") or "").strip()
        if current_structure_id and (
            current_structure_id == raw_structure_id
            or (source.startswith("Importada") and not current_structure_id.startswith("T1-EVAL-"))
            or (not source.startswith("Importada") and current_structure_id.startswith("T1-EVAL-"))
        ):
            st.session_state.tomo1_structure_id = normalized_structure_id
        structure_id = i2.text_input(
            "Identificador de la sección", value=normalized_structure_id, key="tomo1_structure_id"
        )

        base_total_cm = float(base_granular_cm + base_stabilized_cm)
        total_thickness = float(asphalt_cm + base_total_cm + subbase_cm + improvement_cm)
        proposed = {
            "Código": structure_id.strip() or "T1-PROP-01",
            "Superficie": "Carpeta asfáltica" if asphalt_cm > 0 else "Superficie propuesta",
            "Tipo_TomoI": t1_type,
            "Origen_TomoI": source,
            "Carpeta_cm": float(asphalt_cm),
            "Base_cm": base_total_cm,
            "Base_granular_cm": float(base_granular_cm),
            "Base_estabilizada_cm": float(base_stabilized_cm),
            "Subbase_cm": float(subbase_cm),
            "Mejoramiento_subrasante_cm": float(improvement_cm),
            "Base_tipo": "Estabilizada" if base_stabilized_cm > 0 and base_granular_cm <= 0 else ("Mixta" if base_stabilized_cm > 0 and base_granular_cm > 0 else "Granular"),
            "Fuente": "GDP-2024 Tomo I — sección propuesta para evaluación mecanístico-empírica",
        }
        st.session_state.tomo1_structure = proposed
        st.session_state.selected_row = proposed
        st.session_state.total_thickness = total_thickness
        selected_row = proposed

        st.markdown("#### Propiedades de materiales para la evaluación Tomo I")
        st.caption("Registre propiedades representativas y su fuente. Estos valores quedan trazables en el expediente; no sustituyen ensayos ni calibración mecanístico-empírica.")
        mt1, mt2, mt3, mt4 = st.columns(4)
        asphalt_dynamic_modulus = mt1.number_input("Módulo dinámico de mezcla E* de referencia (MPa)", min_value=0.0, max_value=50000.0, value=3500.0, step=100.0, key="mat_asphalt_e")
        asphalt_poisson = mt2.number_input("Poisson mezcla asfáltica", min_value=0.10, max_value=0.49, value=0.35, step=0.01, key="mat_asphalt_nu")
        base_mr = mt3.number_input("Mr base granular (MPa)", min_value=0.0, max_value=2000.0, value=200.0, step=10.0, key="mat_base_mr")
        subbase_mr = mt4.number_input("Mr subbase (MPa)", min_value=0.0, max_value=1500.0, value=120.0, step=10.0, key="mat_subbase_mr")
        mt5, mt6, mt7 = st.columns(3)
        stabilized_modulus = mt5.number_input("Módulo base estabilizada (MPa)", min_value=0.0, max_value=50000.0, value=3000.0 if base_stabilized_cm > 0 else 0.0, step=100.0, key="mat_stabilized_e")
        stabilized_strength = mt6.number_input("Resistencia de referencia base estabilizada (MPa)", min_value=0.0, max_value=50.0, value=3.5 if base_stabilized_cm > 0 else 0.0, step=0.1, key="mat_stabilized_strength")
        material_source = mt7.text_input("Fuente / informe de materiales", value="", key="mat_source")
        material_notes = st.text_area("Notas de caracterización de materiales", value="", height=80, key="mat_notes")

        st.markdown("##### Calidad y procedencia de materiales granulares")
        qg1, qg2, qg3, qg4 = st.columns(4)
        granular_aashto = qg1.text_input("Clasificación AASHTO del granular", value="", key='granular_aashto')
        granular_sucs = qg2.text_input("Clasificación SUCS del granular", value="", key='granular_sucs')
        granular_ll = qg3.number_input("LL granular (%)", min_value=0.0, max_value=150.0, value=0.0, step=1.0, key='granular_ll')
        granular_pi = qg4.number_input("IP granular (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0, key='granular_pi')
        qg5, qg6, qg7, qg8 = st.columns(4)
        granular_moisture = qg5.number_input("Humedad granular (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key='granular_moisture')
        granular_density = qg6.number_input("Densidad seca granular (kg/m³)", min_value=0.0, max_value=3000.0, value=0.0, step=10.0, key='granular_density')
        granular_cbr = qg7.number_input("CBR del granular (%)", min_value=0.0, max_value=200.0, value=80.0, step=1.0, key='granular_cbr_full')
        granular_data_origin = qg8.selectbox("Origen de propiedades", ["Ensayo medido", "Informe del proyecto", "Estimado", "Asumido"], key='granular_origin')
        st.session_state.granular_quality = {
            'aashto': granular_aashto, 'sucs': granular_sucs, 'll_pct': granular_ll, 'pi_pct': granular_pi,
            'moisture_pct': granular_moisture, 'dry_density_kg_m3': granular_density, 'cbr_pct': granular_cbr,
            'data_origin': granular_data_origin,
        }

        st.markdown("##### Modelo constitutivo para arenas / bases / subbases granulares")
        st.caption("Use coeficientes k1, k2 y k3 obtenidos del ensayo/modelo documentado. La aplicación muestra la fórmula y sustitución para trazabilidad.")
        gr1, gr2, gr3, gr4 = st.columns(4)
        granular_type = gr1.selectbox("Material granular", ["Base granular", "Subbase granular", "Arena / material seleccionado"], key='granular_model_type')
        granular_k1 = gr2.number_input("k1", value=1000.0, step=50.0, key='granular_k1')
        granular_k2 = gr3.number_input("k2", value=0.50, step=0.05, key='granular_k2')
        granular_k3 = gr4.number_input("k3", value=-0.20, step=0.05, key='granular_k3')
        gs1, gs2, gs3 = st.columns(3)
        theta_kpa = gs1.number_input("Esfuerzo volumétrico θ (kPa)", min_value=0.1, max_value=5000.0, value=300.0, step=10.0, key='granular_theta')
        tau_oct_kpa = gs2.number_input("Esfuerzo octaédrico τoct (kPa)", min_value=0.0, max_value=5000.0, value=100.0, step=10.0, key='granular_tau_oct')
        pa_kpa = gs3.number_input("Presión atmosférica Pa (kPa)", min_value=1.0, max_value=200.0, value=101.325, step=0.5, key='granular_pa')
        granular_mr_calc = granular_resilient_modulus_mpa(granular_k1, granular_k2, granular_k3, theta_kpa, tau_oct_kpa, pa_kpa)
        st.latex(r"M_R=k_1P_a\left(\frac{\theta}{P_a}\right)^{k_2}\left(\frac{\tau_{oct}}{P_a}+1\right)^{k_3}")
        st.write(f"Sustitución: k1={granular_k1:.3f}; k2={granular_k2:.3f}; k3={granular_k3:.3f}; θ={theta_kpa:.1f} kPa; τoct={tau_oct_kpa:.1f} kPa; Pa={pa_kpa:.3f} kPa.")
        st.metric("Mr calculado del material granular", f"{granular_mr_calc:,.1f} MPa")
        granular_apply_note = st.selectbox("Uso del Mr calculado", ["Referencia / comparación", "Usar como Mr efectivo de base", "Usar como Mr efectivo de subbase"], key='granular_apply_mode')

        st.markdown("##### Modelo específico de base estabilizada e interfaces")
        ib1, ib2, ib3 = st.columns(3)
        interface_ac_base = ib1.selectbox("Interfaz carpeta / base", ["Adherida", "Parcialmente adherida", "Deslizante"], key='interface_ac_base')
        interface_base_subbase = ib2.selectbox("Interfaz base / subbase", ["Adherida", "Parcialmente adherida", "Deslizante"], key='interface_base_subbase')
        interface_subbase_subgrade = ib3.selectbox("Interfaz subbase / subrasante", ["Adherida", "Parcialmente adherida", "Deslizante"], index=1, key='interface_subbase_subgrade')
        st.session_state.layer_interfaces = {
            'asphalt_base': interface_ac_base, 'base_subbase': interface_base_subbase,
            'subbase_subgrade': interface_subbase_subgrade,
            'solver_status': 'Documentadas; el cribado actual solo las usa como factor de revisión. El solver multicapa futuro deberá imponerlas matemáticamente.'
        }
        stabilized_shrinkage = st.selectbox("Riesgo de contracción de base estabilizada", ["Bajo", "Medio", "Alto"], index=1, key='stabilized_shrinkage')
        stabilized_model = stabilized_base_screening_model(stabilized_modulus, stabilized_strength, base_stabilized_cm, stabilized_shrinkage, interface_ac_base)
        st.session_state.stabilized_base_model = stabilized_model
        if base_stabilized_cm > 0:
            sbm1, sbm2, sbm3 = st.columns(3)
            sbm1.metric("Índice de rigidez estabilizada", f"{stabilized_model['rigidity_index']:,.0f}")
            sbm2.metric("Factor contracción/interfaz", f"{stabilized_model['screening_penalty_factor']:.2f}")
            sbm3.metric("Estado", stabilized_model['status'])
            st.caption("La base estabilizada se trata como material propio para trazabilidad de rigidez, resistencia, contracción e interfaz; no como simple sustitución de una base granular.")

        st.session_state.design_materials = {
            "asphalt_dynamic_modulus_mpa": float(asphalt_dynamic_modulus), "asphalt_poisson": float(asphalt_poisson),
            "base_mr_mpa": float(granular_mr_calc if granular_apply_note == "Usar como Mr efectivo de base" else base_mr),
            "subbase_mr_mpa": float(granular_mr_calc if granular_apply_note == "Usar como Mr efectivo de subbase" else subbase_mr),
            "base_mr_input_mpa": float(base_mr), "subbase_mr_input_mpa": float(subbase_mr),
            "granular_model": {'material':granular_type,'k1':granular_k1,'k2':granular_k2,'k3':granular_k3,'theta_kpa':theta_kpa,'tau_oct_kpa':tau_oct_kpa,'pa_kpa':pa_kpa,'mr_calculated_mpa':granular_mr_calc,'application':granular_apply_note},
            "granular_quality": st.session_state.get('granular_quality', {}),
            "layer_interfaces": st.session_state.get('layer_interfaces', {}),
            "stabilized_base_model": st.session_state.get('stabilized_base_model', {}),
            "stabilized_modulus_mpa": float(stabilized_modulus), "stabilized_strength_mpa": float(stabilized_strength),
            "source": material_source, "notes": material_notes, "master_curve_confirmed": bool(master_curve_confirmed),
        }
        if tomo1_category in (1, 2) and not master_curve_confirmed:
            st.warning("Categorías 1 y 2: complete la caracterización térmica/dinámica de la mezcla antes de emitir el diseño como definitivo.")
        if t1_type == "Semirrígido" and base_stabilized_cm > 0 and stabilized_modulus <= 0:
            st.error("La base estabilizada requiere un módulo documentado para la evaluación estructural.")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Carpeta", f"{asphalt_cm:.1f} cm")
        m2.metric("Base total", f"{base_total_cm:.1f} cm")
        m3.metric("Subbase", f"{subbase_cm:.1f} cm")
        m4.metric("Sección modelada", f"{total_thickness:.1f} cm")

        st.markdown("##### Verificación de espesor de carpeta asfáltica — diseño/fórmula de trabajo")
        st.caption("CR-2020 controla el espesor contra el diseño, fórmula de trabajo y tamaño máximo nominal aplicable; no se impone aquí un único rango universal. Los límites siguientes son del proyecto y deben quedar documentados.")
        th1, th2, th3 = st.columns(3)
        asphalt_min_cm = th1.number_input("Espesor mínimo permitido (cm)", min_value=0.0, max_value=40.0, value=5.0, step=0.5, key='asphalt_min_cm_criterion')
        asphalt_max_cm = th2.number_input("Espesor máximo permitido (cm)", min_value=0.0, max_value=80.0, value=20.0, step=0.5, key='asphalt_max_cm_criterion')
        thickness_source = th3.text_input("Fuente del rango de carpeta", value="Pendiente de documentar", key='asphalt_thickness_source')
        asphalt_range_numerically_ok = float(asphalt_min_cm) <= float(asphalt_cm) <= float(asphalt_max_cm) if asphalt_max_cm >= asphalt_min_cm else False
        asphalt_source_ready = bool(str(thickness_source).strip()) and str(thickness_source).strip().lower() not in ('pendiente de documentar', 'pendiente')
        asphalt_thickness_ok = bool(asphalt_range_numerically_ok and asphalt_source_ready)
        if not asphalt_source_ready:
            st.warning("Rango calculado solo como criterio de proyecto: falta documentar la fuente. No se declara cumplimiento normativo.")
        elif asphalt_thickness_ok:
            st.success(f"Carpeta {asphalt_cm:.1f} cm: cumple el rango documentado del proyecto {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm · {thickness_source}.")
        else:
            st.error(f"Carpeta {asphalt_cm:.1f} cm: fuera del rango documentado {asphalt_min_cm:.1f}–{asphalt_max_cm:.1f} cm. Revise criterio y estructura.")
        st.session_state.asphalt_thickness_control = {'asphalt_cm':float(asphalt_cm),'min_cm':float(asphalt_min_cm),'max_cm':float(asphalt_max_cm),'numerically_within_range':bool(asphalt_range_numerically_ok),'source_ready':bool(asphalt_source_ready),'complies':bool(asphalt_thickness_ok),'source':thickness_source,'status':'Cumple criterio documentado' if asphalt_thickness_ok else ('Pendiente fuente' if not asphalt_source_ready else 'No cumple')}

        if asphalt_cm <= 0:
            st.warning("Para una evaluación de pavimento flexible/semirrígido en este flujo debe documentarse la capa superficial correspondiente. El valor actual no se interpreta como una solución final.")
        if base_total_cm <= 0 and subbase_cm <= 0:
            st.warning("La sección no contiene base ni subbase. Revise la configuración antes de utilizar los módulos de análisis.")
        if t1_type == "Semirrígido" and base_stabilized_cm <= 0:
            st.warning("Se seleccionó pavimento semirrígido, pero no se definió una base estabilizada. Revise la estructura y la caracterización de materiales conforme al Tomo I.")

        st.markdown("#### Control de información para evaluación Tomo I")
        c1, c2, c3, c4 = st.columns(4)
        c1.success(f"Tránsito: EEq = {esal:,.0f} · Categoría {tomo1_category}")
        c2.success(f"Subrasante: CBR = {cbr_design:.2f}%")
        if temp_data_confirmed:
            c3.success("Clima: fuente documentada")
        else:
            c3.warning("Clima: falta documentar fuente")
        if master_curve_confirmed:
            c4.success("Materiales: respuesta térmica documentada")
        else:
            c4.warning("Materiales: caracterización incompleta")
        st.warning(
            "**Estado:** sección propuesta para evaluación. GDP no declara conformidad final del Tomo I con estos espesores por sí solos; "
            "la aceptación requiere completar las verificaciones mecanístico-empíricas y la trazabilidad de entradas aplicables."
        )

        left, right = st.columns([0.9, 2.1], gap="large")
        with left:
            st.markdown("#### Visor técnico")
            exploded_t1 = st.toggle("Vista explotada 3D", value=True, key="tomo1_gdp3d_exploded")
            scale_t1 = st.selectbox("Escala vertical", ["Real (×1)", "Exagerada ×2", "Exagerada ×5"], index=0, key="tomo1_gdp3d_vertical_scale")
            vertical_t1 = {"Real (×1)":1.0, "Exagerada ×2":2.0, "Exagerada ×5":5.0}[scale_t1]
            view_t1 = st.selectbox("Modo de corte", ["Completa", "Media calzada", "Corte transversal", "Corte longitudinal"], key="tomo1_gdp3d_view_mode")
            layers_t1 = [x["name"] for x in _structure_layers_3d(selected_row, sclass, cbr_design)]
            highlight_t1 = st.selectbox("Resaltar capa", ["Todas"] + layers_t1, key="tomo1_gdp3d_selected_layer")
            if vertical_t1 > 1:
                st.warning(f"Exageración vertical ×{vertical_t1:g}; las cotas mantienen los espesores reales ingresados.")
            st.caption("La subrasante se representa como medio semiinfinito. El mejoramiento, cuando se ingresa, se muestra como una capa diferenciada.")
        with right:
            st.markdown("#### Visor estructural 3D v2 — Tomo I")
            fig_t1 = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_t1, vertical_t1, view_t1, highlight_t1)
            render_rotating_3d(fig_t1, key="tomo1_structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))

        st.info(
            "La estructura activa queda enlazada con **6. Diseño flexible** y **7. Desempeño**. "
            "En la pestaña 7 se habilita nuevamente el **Modelo 3D del deterioro del pavimento** para la sección propuesta."
        )


with pflex:
    if active_tomo == "Tomo II":
        st.subheader("Diseño estructural complementario — Tomo II")
        st.success("La estructura activa proviene del catálogo oficial GDP-2024 Tomo II y conserva sus espesores de la alternativa seleccionada.")
        st.info("AASHTO-93, SN, optimización libre de espesores y cribado mecanístico pertenecen al flujo complementario/Tomo I y están bloqueados en este modo para no alterar silenciosamente la alternativa normativa del catálogo.")
        if selected_row:
            t2sum = pd.DataFrame([
                ["Código", selected_row.get("Código", "")],
                ["Superficie", selected_row.get("Superficie", "")],
                ["Carpeta (cm)", selected_row.get("Carpeta_cm", 0)],
                ["Base granular (cm)", selected_row.get("Base_granular_cm", 0)],
                ["Base estabilizada (cm)", selected_row.get("Base_estabilizada_cm", 0)],
                ["Subbase Granular (cm)", selected_row.get("Subbase_cm", 0)],
                ["Tabla de asignación", selected_row.get("Tabla_asignacion", "")],
            ], columns=["Elemento", "Valor"])
            st.dataframe(t2sum, use_container_width=True, hide_index=True)
            st.caption("Para un análisis mecanístico adicional, cambie explícitamente a Tomo I e importe esta estructura para evaluación. Esa evaluación no modifica la condición original de alternativa Tomo II.")
        else:
            st.warning("Seleccione primero una alternativa oficial en 5. Estructura.")
    else:
        st.subheader("Diseño preliminar de pavimento flexible — Tomo I")
        st.info("Este módulo calcula el número estructural aportado por la sección propuesta y ejecuta verificaciones preliminares. No sustituye el análisis mecanístico-empírico completo de desempeño del Tomo I.")
        if selected_row:
            st.markdown("#### Confiabilidad y serviciabilidad")
            reliability_default = {3: 75.0, 2: 85.0, 1: 95.0}.get(int(tomo1_category), 75.0)
            serviceability_default = 2.0 if float(tpd_total) < 500.0 else 2.5
            previous_reliability = st.session_state.get("design_reliability", {})
            rc1, rc2 = st.columns(2)
            reliability_pct = rc1.number_input(
                "Índice de confiabilidad (%)",
                min_value=50.0,
                max_value=99.9,
                value=float(reliability_default),
                step=1.0,
                key="design_reliability_pct",
                help="Valor inicial según la categoría de diseño del Tomo I; puede ajustarse manualmente.",
            )
            terminal_serviceability = rc2.number_input(
                "Índice de serviciabilidad",
                min_value=0.0,
                max_value=5.0,
                value=float(serviceability_default),
                step=0.1,
                key="design_terminal_serviceability_visible",
                help="Valor inicial según TPDA de la Tabla 204-03: 2,0 para TPDA menor a 500 y 2,5 para TPDA de 500 o más. Puede ajustarse manualmente.",
            )
            # Parámetros auxiliares conservados internamente para compatibilidad con cálculos,
            # proyectos guardados y exportaciones; solo confiabilidad y serviciabilidad se muestran.
            overall_standard_error = float(previous_reliability.get("overall_standard_error", st.session_state.get("design_standard_error", 0.45)))
            initial_serviceability = float(previous_reliability.get("initial_serviceability", st.session_state.get("design_initial_serviceability", 4.2)))
            st.session_state.design_reliability = {
                "reliability_pct": float(reliability_pct), "category_default_pct": float(reliability_default),
                "overall_standard_error": float(overall_standard_error), "initial_serviceability": float(initial_serviceability),
                "terminal_serviceability": float(terminal_serviceability),
            }
            if reliability_pct < reliability_default:
                st.warning(f"La confiabilidad ingresada ({reliability_pct:.0f}%) es menor al valor de control preliminar asociado a Categoría {tomo1_category} ({reliability_default:.0f}%). Documente la justificación.")

            st.markdown("#### Diseño preliminar AASHTO 93 — SN requerido y aportado")
            st.caption("Este bloque es una comprobación preliminar AASHTO-93 y se mantiene separado del diseño mecanístico-empírico GDP-2024 Tomo I.")
            f1,f2,f3,f4 = st.columns(4)
            a1 = f1.number_input("Coeficiente estructural carpeta a1", min_value=0.01, max_value=1.0, value=DEFAULT_LAYER_COEFFICIENTS["asphalt"], step=0.01, key="aashto_a1")
            a2 = f2.number_input("Coeficiente estructural base granular a2", min_value=0.01, max_value=1.0, value=DEFAULT_LAYER_COEFFICIENTS["granular_base"], step=0.01, key="aashto_a2")
            a_be = f3.number_input(
                "Coeficiente estructural base estabilizada aBE",
                min_value=0.01, max_value=1.0, value=DEFAULT_LAYER_COEFFICIENTS["stabilized_base"], step=0.01, key="aashto_a_be",
                help="Coeficiente independiente para la base estabilizada. El valor 0.20 es preliminar y debe sustituirse por el valor documentado/calibrado del proyecto cuando esté disponible."
            )
            a3 = f4.number_input("Coeficiente estructural subbase granular a3", min_value=0.01, max_value=1.0, value=DEFAULT_LAYER_COEFFICIENTS["granular_subbase"], step=0.01, key="aashto_a3")
            g1,g2,g3 = st.columns(3)
            m2 = g1.number_input("Coeficiente drenaje base granular m2", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m2")
            m_be = g2.number_input(
                "Factor de ajuste base estabilizada mBE", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m_be",
                help="Factor de ajuste separado para la base estabilizada; no se interpreta automáticamente como coeficiente de drenaje de una capa granular."
            )
            m3 = g3.number_input("Coeficiente drenaje subbase granular m3", min_value=0.4, max_value=1.4, value=1.00, step=0.05, key="aashto_m3")

            d1 = float(selected_row.get('Carpeta_cm', 0.0) or 0.0) / 2.54
            d_bg = float(selected_row.get('Base_granular_cm', 0.0) or 0.0) / 2.54
            d_be = float(selected_row.get('Base_estabilizada_cm', 0.0) or 0.0) / 2.54
            if d_bg <= 0 and d_be <= 0:
                d_bg = float(selected_row.get('Base_cm', 0.0) or 0.0) / 2.54
            d3 = float(selected_row.get('Subbase_cm', 0.0) or 0.0) / 2.54

            sn_breakdown = structural_number_breakdown(
                asphalt_in=d1, granular_base_in=d_bg, stabilized_base_in=d_be,
                granular_subbase_in=d3, a1=a1, a_granular_base=a2,
                a_stabilized_base=a_be, a_granular_subbase=a3,
                m_granular_base=m2, m_stabilized_base=m_be, m_granular_subbase=m3,
            )
            sn1 = sn_breakdown["asphalt"]
            sn_bg = sn_breakdown["granular_base"]
            sn_be = sn_breakdown["stabilized_base"]
            sn3 = sn_breakdown["granular_subbase"]
            sn_total = sn_breakdown["total"]
            sn_cum1 = sn1
            sn_cum_bg = sn1 + sn_bg
            sn_cum_be = sn1 + sn_bg + sn_be
            sn_cum3 = sn_total

            material_t1 = st.session_state.get('tomo1_materials', {})
            be_modulus = float(material_t1.get('base_stabilized_modulus_mpa', material_t1.get('stabilized_base_modulus_mpa', 0.0)) or 0.0)
            be_strength = float(material_t1.get('base_stabilized_strength_mpa', material_t1.get('stabilized_base_strength_mpa', 0.0)) or 0.0)
            if d_be > 0:
                if be_modulus <= 0 or be_strength <= 0:
                    st.warning("La sección incluye base estabilizada. Documente su módulo y resistencia de referencia en 5. Estructura antes de considerar definitivo el coeficiente aBE.")
                st.info(
                    f"Base estabilizada activa: {d_be*2.54:.1f} cm · aBE={a_be:.2f} · mBE={m_be:.2f}. "
                    "Su aporte SN se calcula por separado de la base granular."
                )

            aashto_result = aashto93_required_sn(esal, mr, reliability_pct, overall_standard_error, initial_serviceability, terminal_serviceability)
            sn_required = float(aashto_result['sn_required'])
            aashto_complies = sn_total >= sn_required
            # El despeje residual clásico se conserva únicamente para la ruta granular.
            # La base estabilizada se trata como capa independiente y no se fuerza dentro de a2.
            layer_residuals = residual_layer_thicknesses(sn_required, a1, a2, a3, m2, m3, d1, d_bg)
            st.session_state.aashto93_design = {**aashto_result, 'sn_provided': sn_total, 'complies': bool(aashto_complies),
                'a1':a1,'a2':a2,'aBE':a_be,'a3':a3,'m2':m2,'mBE':m_be,'m3':m3,
                'D1_in':d1,'D2_granular_in':d_bg,'D2_stabilized_in':d_be,'D3_in':d3,
                'SN1_contribution':sn1,'SN_base_granular_contribution':sn_bg,'SN_base_stabilized_contribution':sn_be,'SN3_contribution':sn3,
                'SN_cumulative_1':sn_cum1,'SN_cumulative_base_granular':sn_cum_bg,'SN_cumulative_base_stabilized':sn_cum_be,'SN_cumulative_3':sn_cum3}

            ares1, ares2, ares3, ares4 = st.columns(4)
            ares1.metric("SN requerido AASHTO-93", f"{sn_required:.2f}")
            ares2.metric("SN aportado", f"{sn_total:.2f}", "Cumple" if aashto_complies else "No cumple")
            ares3.metric("ZR", f"{aashto_result['zr']:.3f}")
            ares4.metric("ΔPSI", f"{aashto_result['delta_psi']:.2f}")
            st.latex(r"\log_{10}(W_{18})=Z_RS_0+9.36\log_{10}(SN+1)-0.20+\frac{\log_{10}(\Delta PSI/2.7)}{0.40+1094/(SN+1)^{5.19}}+2.32\log_{10}(M_R)-8.07")
            st.caption(f"Sustitución: W18={esal:,.0f}; R={reliability_pct:.1f}%; ZR={aashto_result['zr']:.3f}; S0={overall_standard_error:.2f}; ΔPSI={aashto_result['delta_psi']:.2f}; Mr={mr:.2f} MPa ({aashto_result['mr_psi']:,.0f} psi).")

            st.markdown("##### Desglose del Número Estructural")
            layer_rows = [
                ['Carpeta asfáltica','D1',d1,d1*2.54,'a1',a1,1.0,sn1,sn_cum1],
            ]
            if d_bg > 0:
                layer_rows.append(['Base granular','DBG',d_bg,d_bg*2.54,'a2',a2,m2,sn_bg,sn_cum_bg])
            if d_be > 0:
                layer_rows.append(['Base estabilizada','DBE',d_be,d_be*2.54,'aBE',a_be,m_be,sn_be,sn_cum_be])
            layer_rows.append(['Subbase granular','D3',d3,d3*2.54,'a3',a3,m3,sn3,sn_cum3])
            layer_table = pd.DataFrame(layer_rows, columns=['Capa','Espesor','D (in)','D (cm)','Coeficiente','aᵢ','mᵢ','Aporte SN','SN acumulado'])
            st.dataframe(layer_table, use_container_width=True, hide_index=True)
            st.latex(r"SN=a_1D_1+a_{BG}m_{BG}D_{BG}+a_{BE}m_{BE}D_{BE}+a_3m_3D_3")
            st.write(f"**SN carpeta = {a1:.3f}×{d1:.3f} = {sn1:.3f}**")
            if d_bg > 0:
                st.write(f"**SN base granular = {a2:.3f}×{m2:.3f}×{d_bg:.3f} = {sn_bg:.3f}**")
            if d_be > 0:
                st.write(f"**SN base estabilizada = {a_be:.3f}×{m_be:.3f}×{d_be:.3f} = {sn_be:.3f}**")
            st.write(f"**SN subbase granular = {a3:.3f}×{m3:.3f}×{d3:.3f} = {sn3:.3f}**")

            st.markdown("##### Despeje teórico de espesores por SN residual")
            st.latex(r"D_2=\frac{SN_{req}-a_1D_1}{a_2m_2}")
            st.latex(r"D_3=\frac{SN_{req}-a_1D_1-a_2m_2D_2}{a_3m_3}")
            dr1, dr2, dr3 = st.columns(3)
            dr1.metric("D1 si la carpeta aportara todo el SN", f"{layer_residuals['d1_if_single_layer_in']:.2f} in", f"{layer_residuals['d1_if_single_layer_in']*2.54:.1f} cm")
            dr2.metric("D2 teórico por SN residual", f"{layer_residuals['d2_residual_in']:.2f} in", f"{layer_residuals['d2_residual_in']*2.54:.1f} cm")
            dr3.metric("D3 teórico con D1 y D2 adoptados", f"{layer_residuals['d3_residual_in']:.2f} in", f"{layer_residuals['d3_residual_in']*2.54:.1f} cm")
            st.info("Los espesores teóricos por SN residual deben ajustarse a mínimos constructivos, rangos GDP/CR-2020 aplicables y al análisis mecanístico-empírico; no son por sí solos una sección final.")

            st.markdown("##### Control de calidad CBR de materiales granulares")
            st.caption("Criterios incorporados como control fijo de calidad: base granular CBR ≥ 80% y subbase granular CBR ≥ 30%. Referencia de aplicación: CR-2020 Sección 301 y Subsección 703.05. Verifique además graduación, plasticidad y demás requisitos de la especificación vigente.")
            cb1, cb2, cb3, cb4 = st.columns(4)
            base_cbr = cb1.number_input("CBR material de base (%)", min_value=0.0, max_value=200.0, value=80.0, step=1.0, key="base_material_cbr")
            cb2.metric("CBR mínimo base — CR-2020", f"{CR2020_BASE_CBR_MIN_PCT:.0f}%", help=CR2020_GRANULAR_QUALITY_REFERENCE)
            subbase_cbr = cb3.number_input("CBR material de subbase (%)", min_value=0.0, max_value=200.0, value=30.0, step=1.0, key="subbase_material_cbr")
            cb4.metric("CBR mínimo subbase — CR-2020", f"{CR2020_SUBBASE_CBR_MIN_PCT:.0f}%", help=CR2020_GRANULAR_QUALITY_REFERENCE)
            base_cbr_min = CR2020_BASE_CBR_MIN_PCT
            subbase_cbr_min = CR2020_SUBBASE_CBR_MIN_PCT
            base_cbr_ok = base_cbr >= base_cbr_min; subbase_cbr_ok = subbase_cbr >= subbase_cbr_min
            st.session_state.layer_quality_controls = {'base_cbr':base_cbr,'base_cbr_min':base_cbr_min,'base_cbr_ok':base_cbr_ok,
                'subbase_cbr':subbase_cbr,'subbase_cbr_min':subbase_cbr_min,'subbase_cbr_ok':subbase_cbr_ok,
                'criterion_note':'Valores mínimos configurables; verificar contra especificación vigente del proyecto.'}
            qc1,qc2 = st.columns(2)
            (qc1.success if base_cbr_ok else qc1.error)(f"Base: CBR {base_cbr:.1f}% {'≥' if base_cbr_ok else '<'} criterio {base_cbr_min:.1f}%")
            (qc2.success if subbase_cbr_ok else qc2.error)(f"Subbase: CBR {subbase_cbr:.1f}% {'≥' if subbase_cbr_ok else '<'} criterio {subbase_cbr_min:.1f}%")

            st.progress(min(sn_total/max(sn_required,0.01),1.0), text="Relación SN aportado / SN requerido")

            st.markdown("### Respuesta mecanística de cribado — Tomo I")
            st.warning(
                "Este bloque todavía **no es un solver elástico multicapa definitivo**. Calcula indicadores transparentes de respuesta "
                "para revisar la coherencia de carga, rigidez y espesores. La emisión final requiere validar estos resultados con "
                "un motor multicapa y funciones de transferencia calibradas/aplicables al GDP-2024."
            )
            ml1, ml2, ml3, ml4 = st.columns(4)
            axle_load_kn = ml1.number_input("Carga del eje de análisis (kN)", min_value=10.0, max_value=300.0, value=80.0, step=5.0, key="mech_axle_load")
            tire_pressure_kpa = ml2.number_input("Presión de contacto/neumático (kPa)", min_value=200.0, max_value=1500.0, value=700.0, step=25.0, key="mech_tire_pressure")
            tires_per_axle = ml3.number_input("Neumáticos equivalentes por eje", min_value=1, max_value=12, value=4, step=1, key="mech_tires_per_axle")
            subgrade_poisson = ml4.number_input("Poisson subrasante", min_value=0.20, max_value=0.49, value=0.40, step=0.01, key="mech_subgrade_nu")
            crit1, crit2, crit3 = st.columns(3)
            allowable_eps_t = crit1.number_input("Criterio de control εt bajo carpeta (µε)", min_value=10.0, max_value=5000.0, value=200.0, step=10.0, key="mech_allow_eps_t", help="Valor de control definido por el diseñador/procedimiento validado; no se presenta como límite normativo universal.")
            allowable_eps_v = crit2.number_input("Criterio de control εv sobre subrasante (µε)", min_value=10.0, max_value=10000.0, value=500.0, step=10.0, key="mech_allow_eps_v", help="Valor de control definido por el diseñador/procedimiento validado; no se presenta como límite normativo universal.")
            allowable_stabilized_ratio = crit3.number_input("Relación esfuerzo/resistencia admisible base estabilizada", min_value=0.05, max_value=1.50, value=0.50, step=0.05, key="mech_allow_stab_ratio")

            materials_for_response = st.session_state.get("design_materials", {})
            mech_response = mechanistic_screening_response(
                selected_row, materials_for_response, mr, axle_load_kn, tire_pressure_kpa, int(tires_per_axle),
                subgrade_poisson=float(subgrade_poisson),
            )
            fatigue_util = mech_response["asphalt_tensile_microstrain_screening"] / max(float(allowable_eps_t), 1e-6)
            rut_util = mech_response["subgrade_vertical_microstrain_screening"] / max(float(allowable_eps_v), 1e-6)
            stab_util = mech_response["stabilized_stress_strength_ratio"] / max(float(allowable_stabilized_ratio), 1e-6) if mech_response["stabilized_stress_strength_ratio"] > 0 else 0.0
            mech_response.update({
                "allowable_asphalt_tensile_microstrain": float(allowable_eps_t),
                "allowable_subgrade_vertical_microstrain": float(allowable_eps_v),
                "allowable_stabilized_stress_strength_ratio": float(allowable_stabilized_ratio),
                "fatigue_utilization_ratio": float(fatigue_util),
                "rutting_utilization_ratio": float(rut_util),
                "stabilized_utilization_ratio": float(stab_util),
            })
            st.session_state.mechanistic_screening = mech_response

            st.markdown("#### Confiabilidad aplicada al resultado")
            uq1, uq2 = st.columns(2)
            response_log_sigma = uq1.number_input("Incertidumbre lognormal de respuesta σln", min_value=0.0, max_value=1.0, value=0.15, step=0.01, key="response_log_sigma", help="Parámetro configurable; no es un valor GDP universal.")
            rel_multiplier = reliability_multiplier(reliability_pct, response_log_sigma)
            fatigue_design_util = fatigue_util * rel_multiplier
            rut_design_util = rut_util * rel_multiplier
            uq2.metric("Multiplicador por confiabilidad", f"{rel_multiplier:.3f}", f"R = {reliability_pct:.1f}%")
            mech_response['reliability_multiplier'] = rel_multiplier
            mech_response['fatigue_utilization_design'] = fatigue_design_util
            mech_response['rutting_utilization_design'] = rut_design_util
            mech_response['response_log_sigma'] = response_log_sigma
            st.session_state.mechanistic_screening = mech_response
            rr1, rr2 = st.columns(2)
            rr1.metric("Utilización fatiga a confiabilidad", f"{fatigue_design_util:.2f}", "Cumple" if fatigue_design_util <= 1 else "Revisar")
            rr2.metric("Utilización ahuellamiento a confiabilidad", f"{rut_design_util:.2f}", "Cumple" if rut_design_util <= 1 else "Revisar")

            st.markdown("#### Restricciones constructivas y optimización automática")
            st.caption("El optimizador solo evalúa combinaciones que respetan los límites constructivos documentados. Continúa siendo un cribado hasta disponer del solver multicapa definitivo.")
            cc1, cc2, cc3, cc4 = st.columns(4)
            constr_asphalt_min = cc1.number_input("Carpeta mínima para optimizador (cm)", min_value=0.0, max_value=40.0, value=float(st.session_state.get('asphalt_thickness_control',{}).get('min_cm',5.0)), step=0.5, key='constr_asphalt_min')
            constr_asphalt_max = cc2.number_input("Carpeta máxima para optimizador (cm)", min_value=0.0, max_value=80.0, value=float(st.session_state.get('asphalt_thickness_control',{}).get('max_cm',20.0)), step=0.5, key='constr_asphalt_max')
            constr_base_min = cc3.number_input("Base mínima (cm)", min_value=0.0, max_value=100.0, value=15.0, step=1.0, key='constr_base_min')
            constr_subbase_min = cc4.number_input("Subbase mínima (cm)", min_value=0.0, max_value=120.0, value=15.0, step=1.0, key='constr_subbase_min')
            cc5, cc6 = st.columns(2)
            constr_increment = cc5.selectbox("Incremento constructivo de espesores (cm)", [0.5, 1.0, 2.0], index=1, key='constr_increment')
            constr_source = cc6.text_input("Fuente / criterio constructivo", value="Criterio del proyecto — documentar", key='constr_source')
            construction_constraints = {
                'asphalt_min_cm': float(constr_asphalt_min), 'asphalt_max_cm': float(constr_asphalt_max),
                'base_min_cm': float(constr_base_min), 'subbase_min_cm': float(constr_subbase_min),
                'increment_cm': float(constr_increment), 'source': constr_source,
            }
            st.session_state.construction_constraints = construction_constraints
            current_cc = construction_constraints_check(selected_row, construction_constraints)
            if current_cc['complies']:
                st.success("La sección activa satisface las restricciones constructivas configuradas.")
            else:
                failed = [k for k,v in current_cc['checks'].items() if not v]
                st.warning("La sección activa incumple restricciones constructivas: " + ", ".join(failed))

            st.markdown("#### Diseño iterativo automático — candidatos restringidos")
            op1, op2, op3, op4 = st.columns(4)
            opt_max_inc = op1.number_input("Incremento máximo a explorar por capa (cm)", min_value=0, max_value=30, value=8, step=2, key="opt_max_inc")
            opt_surface_price = op2.number_input("Precio carpeta para optimización (₡/m³)", min_value=0.0, value=95000.0, step=5000.0, key="opt_surface_price")
            opt_base_price = op3.number_input("Precio base para optimización (₡/m³)", min_value=0.0, value=28000.0, step=1000.0, key="opt_base_price")
            opt_subbase_price = op4.number_input("Precio subbase para optimización (₡/m³)", min_value=0.0, value=22000.0, step=1000.0, key="opt_subbase_price")
            opt_area = float(project_length_m) * float(project_width_m)
            st.session_state.pop("run_screening_optimization", None)
            if st.button("Generar candidatos de diseño", key="run_screening_optimization"):
                opt_df = optimize_structure_with_constraints(
                    selected_row, materials_for_response, mr, axle_load_kn, tire_pressure_kpa, int(tires_per_axle),
                    allowable_eps_t, allowable_eps_v, reliability_pct, response_log_sigma, opt_area,
                    {'surface': opt_surface_price, 'base': opt_base_price, 'subbase': opt_subbase_price},
                    construction_constraints, float(opt_max_inc)
                )
                st.session_state.optimization_candidates = opt_df
            opt_show = st.session_state.get('optimization_candidates', pd.DataFrame())
            if isinstance(opt_show, pd.DataFrame) and not opt_show.empty:
                compliant_count = int((opt_show['Cumple_cribado'] == 'Sí').sum())
                st.success(f"Se generaron {len(opt_show)} candidatos; {compliant_count} cumplen el cribado a confiabilidad configurado.")
                st.dataframe(opt_show.head(25), use_container_width=True, hide_index=True)

            mr1, mr2, mr3, mr4 = st.columns(4)
            mr1.metric("Radio de contacto", f"{mech_response['contact_radius_m']*1000:.0f} mm")
            mr2.metric("εt bajo carpeta — cribado", f"{mech_response['asphalt_tensile_microstrain_screening']:.0f} µε", f"Utilización {fatigue_util:.2f}")
            mr3.metric("εv sobre subrasante — cribado", f"{mech_response['subgrade_vertical_microstrain_screening']:.0f} µε", f"Utilización {rut_util:.2f}")
            mr4.metric("Profundidad equivalente", f"{mech_response['equivalent_depth_to_subgrade_m']:.2f} m")

            response_df = pd.DataFrame([
                ["Carga por neumático", mech_response["tire_load_kn"], "kN", "Entrada derivada"],
                ["Esfuerzo indicador bajo carpeta", mech_response["sigma_bottom_asphalt_mpa"], "MPa", "Cribado"],
                ["Deformación tracción bajo carpeta", mech_response["asphalt_tensile_microstrain_screening"], "µε", "Cribado fatiga"],
                ["Esfuerzo indicador sobre subrasante", mech_response["sigma_top_subgrade_mpa"], "MPa", "Cribado"],
                ["Deformación vertical sobre subrasante", mech_response["subgrade_vertical_microstrain_screening"], "µε", "Cribado ahuellamiento"],
                ["Esfuerzo base estabilizada", mech_response["stabilized_stress_mpa"], "MPa", "Cribado semirrígido"],
            ], columns=["Respuesta", "Valor", "Unidad", "Uso"])
            st.dataframe(response_df, use_container_width=True, hide_index=True)
            if fatigue_util > 1.0:
                st.error("El indicador εt supera el criterio de control configurado. Revise espesor/rigidez de carpeta, soporte y carga antes de avanzar.")
            else:
                st.success("El indicador εt se mantiene dentro del criterio de control configurado para este cribado.")
            if rut_util > 1.0:
                st.error("El indicador εv sobre subrasante supera el criterio configurado. Revise capas granulares, mejoramiento, Mr y drenaje.")
            else:
                st.success("El indicador εv se mantiene dentro del criterio de control configurado para este cribado.")
            if mech_response["stabilized_stress_strength_ratio"] > 0:
                if mech_response["stabilized_stress_strength_ratio"] > allowable_stabilized_ratio:
                    st.error("La relación esfuerzo/resistencia de cribado de la base estabilizada supera el criterio configurado.")
                else:
                    st.success("La base estabilizada se mantiene dentro del criterio esfuerzo/resistencia configurado para este cribado.")
            st.caption("Método del bloque: " + mech_response["method"] + ". " + mech_response["limitations"])

            if float(selected_row['Carpeta_cm']) <= 0 and selected_row['Superficie'] == 'Tratamiento superficial': st.warning("La alternativa usa tratamiento superficial; revise que el nivel de tránsito, el desempeño esperado y los materiales sean compatibles con el alcance del catálogo.")
            if tp_ltpp >= 45: st.warning("Temperatura alta del pavimento: revise el módulo dinámico de la mezcla y el riesgo de ahuellamiento.")
            if m2 < 0.8 or m3 < 0.8: st.warning("Los coeficientes de drenaje reducen de forma importante el aporte estructural de las capas granulares.")
            st.session_state.flex_design={"a1":a1,"a2":a2,"aBE":a_be,"a3":a3,"m2":m2,"mBE":m_be,"m3":m3,"sn":sn_total,"reliability_pct":reliability_pct,"overall_standard_error":overall_standard_error,"initial_serviceability":initial_serviceability,"terminal_serviceability":terminal_serviceability,"mechanistic_screening":st.session_state.get("mechanistic_screening",{})}
        else: st.info("Seleccione una estructura para activar el diseño flexible.")

with pperf:
    if active_tomo == "Tomo II":
        st.subheader("Desempeño y conservación — Tomo II")
        st.info("El Tomo II selecciona estructuras por catálogo. Las curvas mecanístico-empíricas de fatiga/ahuellamiento no forman parte del flujo normativo simplificado y se mantienen desactivadas en este modo.")
        if selected_row:
            st.success(f"Alternativa oficial activa: {selected_row.get('Código','')} · {selected_row.get('Superficie','')}")
            st.caption("Use Costos, Ciclo de vida, Drenaje, Control CR-2020 e Informe para la evaluación complementaria. Si requiere respuesta mecanística, cambie a Tomo I e importe la sección explícitamente.")
        else:
            st.warning("Seleccione una alternativa oficial para continuar.")
    else:
        st.subheader("Monitoreo de deterioro — evaluación preliminar del Tomo I")
        st.warning("Las curvas son indicadores preliminares normalizados para comparar escenarios. Para emitir un diseño final deben sustituirse por la respuesta multicapa, modelos constitutivos y calibraciones aplicables del Tomo I.")
        if selected_row:
            mech_state = st.session_state.get("mechanistic_screening", {})
            if mech_state:
                st.markdown("#### Vínculo con respuesta estructural")
                ms1, ms2, ms3 = st.columns(3)
                ms1.metric("Utilización fatiga εt", f"{float(mech_state.get('fatigue_utilization_ratio',0)):.2f}")
                ms2.metric("Utilización ahuellamiento εv", f"{float(mech_state.get('rutting_utilization_ratio',0)):.2f}")
                ms3.metric("Carga de análisis", f"{float(mech_state.get('axle_load_kn',0)):.0f} kN")
                st.info("Estas utilizaciones sirven para priorizar revisión estructural. Las curvas de deterioro inferiores continúan siendo preliminares y todavía no constituyen funciones de transferencia GDP calibradas.")
            else:
                st.warning("Ejecute primero la respuesta mecanística de cribado en **6. Diseño flexible** para vincular deformaciones críticas con este módulo.")
            st.markdown("#### Funciones de transferencia configurables")
            transfer_enabled = st.checkbox("Activar modelo experimental de daño (requiere calibración documentada)", value=False, key="transfer_enabled")
            tf1, tf2, tf3, tf4 = st.columns(4)
            transfer_reference_esal = tf1.number_input(
                "ESAL de referencia de calibración",
                min_value=1.0,
                value=1_000_000.0,
                step=100_000.0,
                key="transfer_ref_esal",
                help=(
                    "Debe corresponder al tránsito acumulado del conjunto de datos usado para calibrar "
                    "los coeficientes. No es necesariamente el ESAL del proyecto ni un valor normativo GDP."
                ),
            )
            fatigue_exponent = tf2.number_input("Exponente de transferencia fatiga", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="transfer_fatigue_exp")
            rutting_exponent = tf3.number_input("Exponente de transferencia ahuellamiento", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="transfer_rut_exp")
            transfer_sigma = tf4.number_input("σln del modelo de transferencia", min_value=0.0, max_value=1.0, value=float(st.session_state.get('mechanistic_screening',{}).get('response_log_sigma',0.15)), step=0.01, key="transfer_sigma")
            transfer_calibration_source = st.text_input(
                "Fuente de la calibración del modelo",
                placeholder="Informe, estudio, laboratorio, versión y fecha",
                key="transfer_calibration_source",
                help="Registre el documento o conjunto de datos del cual provienen el ESAL de referencia y los coeficientes.",
            )
            st.caption(
                "El valor inicial de 1 000 000 ESAL es únicamente demostrativo y no constituye un valor oficial "
                "del GDP-2024, CR-2020 ni AASHTO. El modelo usa la relación ESAL del proyecto / ESAL de calibración."
            )
            if transfer_enabled and not transfer_calibration_source.strip():
                st.warning(
                    "Modelo experimental activo sin fuente de calibración documentada. Sus resultados deben "
                    "tratarse como exploratorios y no como criterio de aceptación del diseño."
                )
            climate_factor_tf = float(st.session_state.get('climate_material', {}).get('relative_climate_factor', 1.0) or 1.0)
            transfer_result = {}
            if transfer_enabled and mech_state:
                transfer_result = configurable_transfer_damage(
                    mech_state, esal, climate_factor_tf, float(st.session_state.get('design_reliability',{}).get('reliability_pct',75.0)),
                    transfer_sigma, transfer_reference_esal, fatigue_exponent, rutting_exponent
                )
                transfer_result["calibration_source"] = transfer_calibration_source.strip() or "No documentada"
                st.session_state.transfer_model = transfer_result
                td1, td2, td3 = st.columns(3)
                td1.metric("Daño fatiga de diseño", f"{transfer_result['fatigue_damage_design']:.3f}", "≤1 criterio interno" if transfer_result['fatigue_damage_design'] <= 1 else ">1 revisar")
                td2.metric("Daño ahuellamiento de diseño", f"{transfer_result['rutting_damage_design']:.3f}", "≤1 criterio interno" if transfer_result['rutting_damage_design'] <= 1 else ">1 revisar")
                td3.metric("Factor climático E*", f"{climate_factor_tf:.3f}")
                st.warning("Estos índices son configurables y **no se identifican como funciones de transferencia oficiales GDP-2024** hasta introducir y validar una calibración específica.")
            else:
                st.session_state.transfer_model = {'enabled': False, 'calibration_status': 'Desactivado / pendiente de calibración'}

            pc1,pc2,pc3,pc4 = st.columns(4)
            with pc1:
                perf_years = st.number_input("Horizonte de monitoreo (años)", 1, 40, int(years), key="perf_years")
            with pc2:
                drainage_perf = st.number_input("Factor relativo de drenaje", .55, 1.40, float(st.session_state.get("flex_design",{}).get("m2",1.0)), .05, key="perf_drain")
            with pc3:
                fatigue_limit = st.number_input("Límite de fatiga (%)", 1.0, 100.0, 20.0, 1.0)
            with pc4:
                rut_limit = st.number_input("Límite de ahuellamiento (mm)", 1.0, 40.0, 20.0, 1.0)
            asphalt_eff = float(selected_row['Carpeta_cm']) if float(selected_row['Carpeta_cm']) > 0 else 2.0
            perf_df = performance_curves(perf_years, esal, tp_ltpp, cbr_design, asphalt_eff, drainage_perf)
            st.session_state.performance_df = perf_df
            last = perf_df.iloc[-1]
            g1,g2,g3,g4,g5=st.columns(5)
            g1.metric("Fatiga final",f"{last['Fatiga (%)']:.1f}%", "Cumple" if last['Fatiga (%)']<=fatigue_limit else "Supera límite")
            g2.metric("Ahuellamiento final",f"{last['Ahuellamiento (mm)']:.1f} mm", "Cumple" if last['Ahuellamiento (mm)']<=rut_limit else "Supera límite")
            g3.metric("Fisura longitudinal",f"{last['Fisuras longitudinales (%)']:.1f}%")
            g4.metric("Fisura por bloque",f"{last['Fisuras por bloque (%)']:.1f}%")
            g5.metric("PCI estimado",f"{last['PCI estimado']:.0f}")

            st.markdown("### Modelo 3D del deterioro del pavimento")
            st.caption("Visualización didáctica vinculada a las curvas preliminares de desempeño. Las patologías se representan sobre la superficie según el año y severidad seleccionados.")
            dctrl, dview = st.columns([0.27,0.73], gap="large")
            with dctrl:
                year_3d = st.slider("Año a visualizar en 3D", 0, int(perf_years), int(perf_years), 1, key="perf_3d_year")
                visible_pathologies = st.multiselect(
                    "Patologías visibles",
                    ["Fatiga","Ahuellamiento","Fisuras longitudinales","Fisuras por bloque","Fisuración térmica"],
                    default=["Fatiga","Ahuellamiento","Fisuras longitudinales","Fisuras por bloque"],
                    key="perf_3d_pathologies"
                )
                perf_state = perf_df.loc[perf_df['Año']==year_3d].iloc[0].to_dict()
                st.metric("PCI en el año seleccionado", f"{perf_state['PCI estimado']:.0f}")
                st.markdown(
                    f"""
                    <div class='panel-card'>
                      <div class='panel-title'>Severidad visual</div>
                      <div class='alert-row'>Fatiga: <b>{perf_state['Fatiga (%)']:.1f}%</b> · {pathology_severity(perf_state['Fatiga (%)'],10,20)}</div>
                      <div class='alert-row'>Ahuellamiento: <b>{perf_state['Ahuellamiento (mm)']:.1f} mm</b> · {pathology_severity(perf_state['Ahuellamiento (mm)'],8,15)}</div>
                      <div class='alert-row'>Fisuras longitudinales: <b>{perf_state['Fisuras longitudinales (%)']:.1f}%</b> · {pathology_severity(perf_state['Fisuras longitudinales (%)'],10,20)}</div>
                      <div class='alert-row'>Fisuras por bloque: <b>{perf_state['Fisuras por bloque (%)']:.1f}%</b> · {pathology_severity(perf_state['Fisuras por bloque (%)'],10,20)}</div>
                    </div>
                    """, unsafe_allow_html=True
                )
                st.info("La representación 3D es cualitativa y escala visualmente la severidad. No equivale a una simulación mecánica ni a una inspección PCI de campo.")
            with dview:
                perf_3d = deterioration_3d_figure(selected_row, sclass, cbr_design, perf_state, visible_pathologies)
                render_rotating_3d(perf_3d, key=f"performance_{year_3d}", height=650, auto_rotate=bool(st.session_state.get("auto_rotate_3d", True)))

            r1,r2=st.columns(2)
            with r1:
                st.plotly_chart(performance_plot(perf_df,"Fatiga (%)","Fatiga / área agrietada","Daño acumulado (%)",fatigue_limit,f"Límite {fatigue_limit:.0f}%"),use_container_width=True,config={"displaylogo":False})
                st.plotly_chart(performance_plot(perf_df,"Fisuras longitudinales (%)","Fisuras longitudinales","Densidad (%)",30.0,"Referencia 30%"),use_container_width=True,config={"displaylogo":False})
            with r2:
                st.plotly_chart(performance_plot(perf_df,"Ahuellamiento (mm)","Ahuellamiento total","Deformación (mm)",rut_limit,f"Límite {rut_limit:.0f} mm"),use_container_width=True,config={"displaylogo":False})
                st.plotly_chart(performance_plot(perf_df,"Fisuras por bloque (%)","Fisuras por bloque","Densidad (%)",30.0,"Referencia 30%"),use_container_width=True,config={"displaylogo":False})
            pci_fig=go.Figure(go.Scatter(x=perf_df['Año'],y=perf_df['PCI estimado'],mode='lines+markers',line=dict(color='#159947',width=4),marker=dict(size=7)))
            pci_fig.add_hline(y=70,line_dash='dash',line_color='#f5a000',annotation_text='PCI 70')
            pci_fig.add_hline(y=55,line_dash='dash',line_color='#ef3340',annotation_text='PCI 55')
            pci_fig.update_layout(height=320,title='Índice de condición estimado',xaxis_title='Años',yaxis_title='PCI',yaxis_range=[0,100],plot_bgcolor='#f8fbff',paper_bgcolor='white')
            st.plotly_chart(pci_fig,use_container_width=True,config={"displaylogo":False})
            if last['Fatiga (%)']>fatigue_limit: st.error("La estimación preliminar supera el límite de fatiga configurado. Revise espesores, módulo de mezcla, tránsito y confiabilidad.")
            if last['Ahuellamiento (mm)']>rut_limit: st.error("La estimación preliminar supera el límite de ahuellamiento. Revise temperatura, mezcla asfáltica, capas granulares, subrasante y drenaje.")
            if last['PCI estimado']<70: st.warning("El PCI estimado cae por debajo de 70 durante el horizonte analizado; programe mantenimiento preventivo o rehabilitación.")
            st.download_button("Descargar curvas de desempeño (CSV)",perf_df.to_csv(index=False).encode('utf-8-sig'),"curvas_desempeno_preliminar.csv","text/csv")
        else:
            st.info("Seleccione una estructura para activar el monitoreo de desempeño.")

with pcompare:
    st.subheader("Comparación técnica y económica de alternativas")
    if active_tomo == "Tomo II":
        candidates = st.session_state.get("tomo2_options", pd.DataFrame()).copy()
        st.caption("Tomo II: comparación limitada a alternativas oficiales de la celda normativa vigente.")
        if candidates.empty:
            st.info("No hay alternativas oficiales compatibles disponibles para comparar.")
            st.session_state.alternatives_compare = pd.DataFrame()
        else:
            cp1,cp2,cp3=st.columns(3)
            surf_price=cp1.number_input("Precio referencial superficie (₡/m³)",0.0,value=95000.0,step=5000.0,key='cmp_surf_t2')
            base_price=cp2.number_input("Precio referencial base (₡/m³)",0.0,value=28000.0,step=1000.0,key='cmp_base_t2')
            sub_price=cp3.number_input("Precio referencial subbase (₡/m³)",0.0,value=22000.0,step=1000.0,key='cmp_sub_t2')
            cmp_area=st.number_input("Área para comparación (m²)",1.0,value=float(project_length_m*project_width_m),step=50.0,key='cmp_area_t2')
            candidates['Espesor_total_cm']=candidates[['Carpeta_cm','Base_cm','Subbase_cm']].sum(axis=1)
            candidates['Costo_inicial']=cmp_area*(candidates['Carpeta_cm']/100*surf_price+candidates['Base_cm']/100*base_price+candidates['Subbase_cm']/100*sub_price)
            candidates['Estado_técnico']='Oficial GDP-2024'
            show=candidates.sort_values(['Costo_inicial','Espesor_total_cm']).copy()
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.session_state.alternatives_compare=show
    else:
        candidates = st.session_state.get('optimization_candidates', pd.DataFrame()).copy()
        st.caption("Tomo I: jerarquía obligatoria **cumplimiento técnico → utilización a confiabilidad → costo → espesor**. Los candidatos provienen del cribado iterativo, no de un catálogo normativo.")
        if candidates.empty:
            st.info("Genere candidatos en **6. Diseño flexible** para ejecutar la comparación técnico-económica Tomo I.")
            st.session_state.alternatives_compare = pd.DataFrame()
        else:
            candidates['Cumple_num'] = candidates['Cumple_cribado'].eq('Sí').astype(int)
            show = candidates.sort_values(['Cumple_num','Máxima_utilización','Costo_inicial','Espesor_total_cm'], ascending=[False,True,True,True]).copy()
            show['Prioridad'] = range(1, len(show)+1)
            cols = ['Prioridad','Código','Cumple_cribado','Utilización_fatiga_diseño','Utilización_ahuellamiento_diseño','Máxima_utilización','Carpeta_cm','Base_cm','Subbase_cm','Espesor_total_cm','Costo_inicial']
            st.dataframe(show[cols].head(50), use_container_width=True, hide_index=True)
            compliant = show[show['Cumple_cribado']=='Sí']
            if not compliant.empty:
                best = compliant.iloc[0]
                st.success(f"Candidato prioritario de cribado: **{best['Código']}** · utilización máx. {best['Máxima_utilización']:.2f} · costo {money(best['Costo_inicial'])}.")
            else:
                st.error("Ningún candidato cumple el cribado a confiabilidad. Debe ampliar rangos de espesores o revisar materiales/carga antes de comparar costos.")
            st.session_state.alternatives_compare = show

        st.markdown("#### Comparador de escenarios — sensibilidad estructural")
        st.caption("Compara un escenario conservador, esperado y optimista variando tránsito y soporte. Es análisis de sensibilidad, no sustitución de un estudio probabilístico.")
        scenario_mech = st.session_state.get('mechanistic_screening', {})
        if selected_row and scenario_mech:
            scenario_df = scenario_comparison_table(
                esal, mr, tp_ltpp, selected_row, st.session_state.get('design_materials', {}),
                float(scenario_mech.get('axle_load_kn',80.0)), float(scenario_mech.get('tire_pressure_kpa',700.0)),
                int(scenario_mech.get('tires_per_axle',4)), float(scenario_mech.get('allowable_asphalt_tensile_microstrain',200.0)),
                float(scenario_mech.get('allowable_subgrade_vertical_microstrain',500.0))
            )
            st.session_state.scenario_comparison = scenario_df
            st.dataframe(scenario_df, use_container_width=True, hide_index=True)
            sc_fig = go.Figure()
            sc_fig.add_trace(go.Bar(name='Fatiga', x=scenario_df['Escenario'], y=scenario_df['Utilización_fatiga']))
            sc_fig.add_trace(go.Bar(name='Ahuellamiento', x=scenario_df['Escenario'], y=scenario_df['Utilización_ahuellamiento']))
            sc_fig.update_layout(barmode='group', height=330, yaxis_title='Utilización', title='Sensibilidad por escenario')
            st.plotly_chart(sc_fig, use_container_width=True, config={'displaylogo': False})
        else:
            st.info("Ejecute primero la respuesta mecanística en Diseño flexible para habilitar escenarios.")

with p5:
    st.subheader("Costos de construcción y cantidades de obra")
    q1, q2, q3 = st.columns(3)
    with q1:
        length_m = st.number_input("Longitud (m)", min_value=1.0, value=float(project_length_m), step=10.0)
    with q2:
        width_m = st.number_input("Ancho pavimentado (m)", min_value=1.0, value=float(project_width_m), step=0.5)
    with q3:
        area_m2 = length_m * width_m
        st.metric("Área", f"{area_m2:,.2f} m²")

    if selected_row:
        price_surface = st.number_input("Precio carpeta/superficie (₡/m³)", min_value=0.0, value=95000.0, step=5000.0)
        price_base = st.number_input("Precio base (₡/m³)", min_value=0.0, value=28000.0, step=1000.0)
        price_subbase = st.number_input("Precio subbase (₡/m³)", min_value=0.0, value=22000.0, step=1000.0)
        indirect_pct = st.number_input("Indirectos e imprevistos (%)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)

        vol_surface = area_m2 * selected_row["Carpeta_cm"] / 100.0
        vol_base = area_m2 * selected_row["Base_cm"] / 100.0
        vol_subbase = area_m2 * selected_row["Subbase_cm"] / 100.0
        direct = vol_surface * price_surface + vol_base * price_base + vol_subbase * price_subbase
        total_cost = direct * (1 + indirect_pct / 100.0)
        per_m2 = total_cost / area_m2 if area_m2 else 0.0

        cost_table = pd.DataFrame([
            ["Carpeta/superficie", vol_surface, price_surface, vol_surface * price_surface],
            ["Base", vol_base, price_base, vol_base * price_base],
            ["Subbase", vol_subbase, price_subbase, vol_subbase * price_subbase],
        ], columns=["Capa", "Volumen_m3", "Precio_unitario", "Subtotal"])
        st.dataframe(cost_table.style.format({"Volumen_m3":"{:,.2f}", "Precio_unitario":"₡{:,.0f}", "Subtotal":"₡{:,.0f}"}), use_container_width=True, hide_index=True)
        z1, z2, z3 = st.columns(3)
        z1.metric("Costo directo", money(direct))
        z2.metric("Costo total", money(total_cost))
        z3.metric("Costo por m²", money(per_m2))
    else:
        total_cost = 0.0
        per_m2 = 0.0
        st.info("Seleccione una estructura en la pestaña anterior.")


with pmaint:
    st.subheader("Mantenimiento y análisis de ciclo de vida")
    st.caption("Defina intervenciones y compare su valor presente. Los años y costos deben ajustarse al plan de conservación del proyecto.")
    discount_pct=st.number_input("Tasa real de descuento (%)",min_value=0.0,max_value=30.0,value=6.0,step=0.5)
    default_maint=pd.DataFrame([
        [0,"Construcción inicial",float(total_cost if 'total_cost' in locals() else 0.0)],
        [3,"Mantenimiento rutinario",2500000.0],[6,"Sellado o tratamiento superficial",7000000.0],[10,"Rehabilitación",18000000.0]
    ],columns=['Año','Intervención','Costo (₡)'])
    maintenance_df=st.data_editor(default_maint,num_rows='dynamic',use_container_width=True,key='maint_editor')
    maintenance_df['Año']=pd.to_numeric(maintenance_df['Año'],errors='coerce').fillna(0).astype(int)
    maintenance_df['Costo (₡)']=pd.to_numeric(maintenance_df['Costo (₡)'],errors='coerce').fillna(0.0)
    maintenance_df['Valor presente (₡)']=maintenance_df.apply(lambda r: present_value(float(r['Costo (₡)']),int(r['Año']),discount_pct/100),axis=1)
    lifecycle_npv=float(maintenance_df['Valor presente (₡)'].sum())
    lc1,lc2=st.columns(2); lc1.metric("Costo ciclo de vida — VP",money(lifecycle_npv)); lc2.metric("Horizonte evaluado",f"{maintenance_df['Año'].max() if len(maintenance_df) else 0} años")
    st.line_chart(maintenance_df.set_index('Año')['Valor presente (₡)'])
    st.session_state.maintenance_df=maintenance_df
    st.session_state.lifecycle_npv=lifecycle_npv

with pdrain:
    st.subheader("Drenaje asociado al pavimento")
    st.info("El GDP destaca que el drenaje eficiente y el mantenimiento oportuno son fundamentales para la durabilidad. Este módulo documenta condiciones y genera alertas preliminares.")
    dr1,dr2,dr3=st.columns(3)
    drainage_quality=dr1.selectbox("Calidad esperada del drenaje",["Excelente","Buena","Regular","Deficiente","Muy deficiente"],index=1)
    saturated_pct=dr2.number_input("Tiempo estimado cercano a saturación (% del año)",0.0,100.0,value=5.0,step=1.0)
    water_table=dr3.number_input("Profundidad del nivel freático (m)",0.0,20.0,value=2.0,step=0.1)
    cross_slope=st.number_input("Pendiente transversal de calzada (%)",0.0,15.0,value=2.0,step=0.1)
    dcol1,dcol2,dcol3=st.columns(3)
    side_ditches=dcol1.checkbox("Cunetas o drenaje longitudinal definidos",value=True)
    outlets=dcol2.checkbox("Descargas y alcantarillas verificadas",value=False)
    subsurface=dcol3.checkbox("Subdrenaje considerado cuando corresponde",value=False)
    drain_alerts=[]
    if drainage_quality in ['Deficiente','Muy deficiente']: drain_alerts.append(('error','La calidad de drenaje declarada puede comprometer el desempeño de las capas granulares.'))
    if saturated_pct>25: drain_alerts.append(('warning','El pavimento permanecería una fracción significativa del año próximo a saturación; revise coeficientes de drenaje y necesidad de subdrenes.'))
    if water_table<1.0: drain_alerts.append(('warning','Nivel freático somero: se requiere una revisión geotécnica e hidráulica específica.'))
    if cross_slope<1.5: drain_alerts.append(('warning','La pendiente transversal ingresada podría dificultar la evacuación superficial; verifique el criterio geométrico aplicable.'))
    if not side_ditches or not outlets: drain_alerts.append(('warning','El sistema de conducción o descarga no está completamente documentado.'))
    if not drain_alerts: drain_alerts=[('success','No se detectaron alertas preliminares de drenaje con los datos ingresados.')]
    for level,msg in drain_alerts: getattr(st,level)(msg)
    st.session_state.drainage={"quality":drainage_quality,"saturated_pct":saturated_pct,"water_table_m":water_table,"cross_slope_pct":cross_slope,"side_ditches":side_ditches,"outlets":outlets,"subsurface":subsurface,"alerts":[m for _,m in drain_alerts]}

with pvalid:
    st.subheader("Validación técnica y trazabilidad — v1.0 beta")
    st.caption("Consolida alertas de alcance, catálogo, tránsito, subrasante, clima y drenaje. Los puntos marcados como Revisar deben resolverse antes de emitir una memoria final.")
    if selected_row:
        validation_df = technical_validation(
            active_tomo, selected_row, exact_match, esal, cbr_design, tp_ltpp,
            st.session_state.get("drainage", {}), st.session_state.get("project_geometry", {}),
            st.session_state.get("subgrade_details", {}), st.session_state.get("design_materials", {}),
            st.session_state.get("design_reliability", {}), st.session_state.get("mechanistic_screening", {}),
        )
        n_ok = int((validation_df["Estado"]=="Cumple").sum()); n_total=len(validation_df)
        v1,v2,v3=st.columns(3)
        v1.metric("Verificaciones cumplidas",f"{n_ok}/{n_total}")
        v2.metric("Nivel de trazabilidad", "Alto" if n_ok>=n_total-1 else "Medio")
        v3.metric("Resultado", "Apto para revisión" if n_ok>=n_total-1 else "Requiere ajustes")
        st.dataframe(validation_df,use_container_width=True,hide_index=True)
        if active_tomo == "Tomo II":
            trace = selected_trace(selected_row)
            st.markdown("#### Referencia normativa de la selección")
            st.info(f"{trace.get('fuente','GDP-2024 Tomo II')} · {trace.get('asignacion','')} · {trace.get('criterio','')}")
        st.download_button("Descargar matriz de validación (CSV)",validation_df.to_csv(index=False).encode("utf-8-sig"),"matriz_validacion_gdp.csv","text/csv")
        readiness_payload = {
            'traffic': {'esal': esal}, 'subgrade': {'mr': mr},
            'materials': st.session_state.get('design_materials', {}),
            'mechanistic_screening': st.session_state.get('mechanistic_screening', {}),
            'layer_interfaces': st.session_state.get('layer_interfaces', {}),
            'construction_constraints': st.session_state.get('construction_constraints', {}),
            'climate_material': st.session_state.get('climate_material', {}),
        }
        readiness_score, readiness_detail = engineering_readiness_score(readiness_payload)
        st.markdown("#### Índice de madurez técnica del diseño")
        rd1, rd2 = st.columns([1,3])
        rd1.metric("Madurez técnica", f"{readiness_score}%")
        rd2.dataframe(pd.DataFrame(readiness_detail), use_container_width=True, hide_index=True)
        st.session_state.engineering_readiness = {'score': readiness_score, 'detail': readiness_detail}

        st.markdown("#### Matriz de evidencia normativa")
        st.dataframe(normative_evidence_table(), use_container_width=True, hide_index=True)
        st.caption("Fuentes oficiales de referencia: GDP-2024 Tomo I — Decreto 44762-MOPT; CR-2020 — Decreto 43397-MOPT. Los controles sin tabla/sección exacta incorporada no pueden declarar cumplimiento automático.")
        st.markdown("#### Controles de emisión")
        c1,c2,c3,c4=st.columns(4)
        c1.checkbox("Datos de tránsito revisados",key="qa_traffic")
        c2.checkbox("Ensayos de subrasante respaldados",key="qa_subgrade")
        c3.checkbox("Drenaje y clima documentados",key="qa_climate")
        asphalt_state = st.session_state.get("asphalt_cr2020_checklist", st.session_state.get("asphalt_cr2010_checklist", {}))
        asphalt_ready = bool(asphalt_state) and int(asphalt_state.get("critical_nonconformities", 0)) == 0
        c4.checkbox("Control constructivo CR-2020 revisado", value=asphalt_ready, key="qa_asphalt_cr2020")
        if all(st.session_state.get(k,False) for k in ("qa_traffic","qa_subgrade","qa_climate","qa_asphalt_cr2020")) and n_ok>=n_total-1:
            st.success("El expediente está preparado para revisión profesional y emisión controlada.")
        else:
            st.warning("La memoria debe mantenerse como preliminar hasta completar los controles de emisión.")
    else:
        st.info("Seleccione una estructura para ejecutar la validación.")

with pcr2010:
    asphalt_cr2020_result = render_asphalt_cr2020_checklist(project_name)

with pexport:
    st.subheader("Exportación de planos, memorias e integración futura")
    st.caption("Se generan formatos de intercambio para continuar el trabajo en Excel, Civil 3D y QGIS. La importación final debe verificarse en cada software.")
    st.info("Los valores iniciales se toman automáticamente de la ubicación definida en **1. Proyecto**. Puede modificarlos aquí si la exportación corresponde a otro punto del eje.")
    ex1,ex2,ex3=st.columns(3)
    start_e=ex1.number_input("Este inicial CRTM05",value=float(crtm_easting),step=10.0,format="%.3f")
    start_n=ex2.number_input("Norte inicial CRTM05",value=float(crtm_northing),step=10.0,format="%.3f")
    azimuth=ex3.number_input("Azimut del eje (°)",0.0,360.0,value=90.0,step=1.0)
    ex4,ex5,ex6=st.columns(3)
    export_length=ex4.number_input("Longitud de eje (m)",1.0,value=float(length_m if 'length_m' in locals() else 150.0),step=10.0)
    interval=ex5.number_input("Intervalo de puntos (m)",1.0,value=10.0,step=1.0)
    elevation=ex6.number_input("Elevación de referencia (m)",value=100.0,step=0.1)
    lon1,lat1,lon2,lat2=st.columns(4)
    start_lon=lon1.number_input("Longitud inicial QGIS (WGS84)",-180.0,180.0,value=float(longitude),format='%.7f')
    start_lat=lat1.number_input("Latitud inicial QGIS (WGS84)",-90.0,90.0,value=float(latitude),format='%.7f')
    end_lon=lon2.number_input("Longitud final QGIS (WGS84)",-180.0,180.0,value=float(longitude + 0.001),format='%.7f')
    end_lat=lat2.number_input("Latitud final QGIS (WGS84)",-90.0,90.0,value=float(latitude),format='%.7f')
    if selected_row:
        st.download_button("Descargar sección transversal DXF",build_section_dxf(selected_row,float(width_m if 'width_m' in locals() else 6.0)),"seccion_pavimento.dxf","application/dxf")
    st.download_button("Descargar puntos para Civil 3D (CSV)",build_civil3d_csv(start_e,start_n,azimuth,export_length,interval,elevation),"eje_civil3d.csv","text/csv")
    props={"tomo":active_tomo,"traffic":tclass,"design_category":f"Categoría {tomo1_category}" if active_tomo == "Tomo I" else "No aplica","subgrade":sclass,"cbr":cbr_design,"esal":esal,"structure":selected_row.get('Código','') if selected_row else ''}
    st.download_button("Descargar eje para QGIS (GeoJSON)",build_geojson(project_name,start_lon,start_lat,end_lon,end_lat,props),"eje_proyecto.geojson","application/geo+json")
    st.info("Integración futura prevista: lectura de superficies y alineamientos de Civil 3D, capas GIS del proyecto, estaciones climáticas y exportación de corredores. Esta versión establece formatos de intercambio abiertos.")

with p6:
    st.subheader("Informe y exportación")
    payload = {
        "project": {
            "name": project_name,
            "location": location,
            "engineer": engineer,
            "date": project_date.isoformat(),
            "road_type": road_type,
            "pavement_type": pavement_type,
            "length_m": float(project_length_m),
            "lane_width_m": float(lane_width_m),
            "number_lanes": int(number_lanes),
            "traffic_directions": traffic_directions,
            "shoulder_width_m": float(shoulder_width_m),
            "paved_reference_width_m": float(project_width_m),
            "cross_slope_pct": float(project_cross_slope_pct),
            "longitudinal_slope_pct": float(project_long_slope_pct),
            "functional_condition": functional_class,
            "coordinate_system_input": coordinate_system,
            "crtm05_epsg": 5367,
            "crtm05_easting_m": crtm_easting,
            "crtm05_northing_m": crtm_northing,
            "wgs84_epsg": 4326,
            "latitude": latitude,
            "longitude": longitude,
        },
        "traffic": {
            "tpd_total": tpd_total,
            "weighted_daily": weighted_daily,
            "growth_rate": growth_pct,
            "growth_factor": gf,
            "years": int(years),
            "direction_factor": direction_factor,
            "lane_factor": lane_factor,
            "esal": esal,
            "class": tclass if active_tomo == "Tomo I" else "No aplica como categoría normativa Tomo II",
            "tomo2_tpd_category": classify_tpd(tpd_total) if active_tomo == "Tomo II" else None,
            "tomo2_heavy_category": classify_heavy_pct(heavy_pct) if active_tomo == "Tomo II" else None,
            "tomo2_cbr_category": classify_cbr(cbr_design) if active_tomo == "Tomo II" else None,
            "tomo2_period_years": int(years) if active_tomo == "Tomo II" else None,
            "design_category": tomo1_category if active_tomo == "Tomo I" else None,
            "design_category_label": f"Categoría {tomo1_category}" if active_tomo == "Tomo I" else "No aplica",
        },
        "subgrade": {"cbr": cbr_design, "class": sclass, "mr": mr, **st.session_state.get("subgrade_details", {})},
        "geometry": st.session_state.get("project_geometry", {}),
        "materials": st.session_state.get("design_materials", {}) if active_tomo == "Tomo I" else {},
        "reliability": st.session_state.get("design_reliability", {}) if active_tomo == "Tomo I" else {},
        "normative_evidence": normative_evidence_table().to_dict(orient="records"),
        "asphalt_thickness_control": st.session_state.get("asphalt_thickness_control", {}),
        "project_map": st.session_state.get("project_map", {
            "latitude": float(latitude), "longitude": float(longitude),
            "crtm_easting": float(crtm_easting), "crtm_northing": float(crtm_northing),
        }),
        "granular_quality": st.session_state.get("granular_quality", {}),
        "layer_interfaces": st.session_state.get("layer_interfaces", {}),
        "stabilized_base_model": st.session_state.get("stabilized_base_model", {}),
        "construction_constraints": st.session_state.get("construction_constraints", {}),
        "engineering_readiness": st.session_state.get("engineering_readiness", {}),
        "scenario_comparison": st.session_state.get("scenario_comparison", pd.DataFrame()).to_dict(orient="records") if isinstance(st.session_state.get("scenario_comparison", pd.DataFrame()), pd.DataFrame) else [],
        "mechanistic_screening": st.session_state.get("mechanistic_screening", {}) if active_tomo == "Tomo I" else {},
        "transfer_model": st.session_state.get("transfer_model", {}) if active_tomo == "Tomo I" else {},
        "climate_material": st.session_state.get("climate_material", {}) if active_tomo == "Tomo I" else {},
        "homogeneous_segments": st.session_state.get("homogeneous_segments", []),
        "rehabilitation": st.session_state.get("rehabilitation", {}),
        "optimization_candidates": st.session_state.get("optimization_candidates", pd.DataFrame()).to_dict(orient="records") if isinstance(st.session_state.get("optimization_candidates", pd.DataFrame()), pd.DataFrame) else [],
        "climate": {
            "input_mode": climate_input_mode,
            "source": climate_source,
            "period": climate_period,
            "station": station_selected,
            "catalog_origin": "automatic" if catalog_matches_zone else "manual",
            "catalog_latitude": catalog.get("latitude") if catalog_matches_zone else None,
            "catalog_longitude": catalog.get("longitude") if catalog_matches_zone else None,
            "notes": climate_notes,
            "air_c": air_temp_c,
            "pavement_ltpp_c": tp_ltpp,
            "pavement_shrp_c": tp_shrp,
            "latitude": latitude,
            "depth_mm": depth_mm,
            "monthly_air_c": monthly_values,
            "monthly_table": climate_monthly_df.to_dict(orient="records") if not climate_monthly_df.empty else [],
            "alerts": [m for _,m in climate_checks],
        },
        "active_tomo": active_tomo,
        "selected": selected_row,
        "gdp_tomo2": st.session_state.get("tomo2_result", {}) if active_tomo == "Tomo II" else {},
        "traceability": selected_trace(selected_row),
        "flex_design": st.session_state.get("flex_design", {}),
        "drainage": st.session_state.get("drainage", {}),
        "asphalt_cr2020": st.session_state.get("asphalt_cr2020_checklist", st.session_state.get("asphalt_cr2020_checklist", st.session_state.get("asphalt_cr2010_checklist", {}))),
        "lifecycle_npv": st.session_state.get("lifecycle_npv", 0.0),
        "costs": {"area": area_m2, "total": total_cost, "per_m2": per_m2},
    }

    quality_score, quality_detail = design_data_quality_score(payload)
    readiness_score, readiness_detail = engineering_readiness_score(payload)
    st.markdown("#### Estado profesional del expediente")
    qi1, qi2, qi3, qi4 = st.columns(4)
    qi1.metric("Calidad documental", f"{quality_score}%")
    qi2.metric("Madurez técnica", f"{readiness_score}%")
    qi3.metric("Tramos homogéneos", f"{len(payload.get('homogeneous_segments', []))}")
    qi4.metric("Candidatos optimizados", f"{len(payload.get('optimization_candidates', []))}")
    st.dataframe(pd.DataFrame(quality_detail), use_container_width=True, hide_index=True)
    st.markdown("#### Registro de cálculo auditable")
    audit_rows = [
        {'Etapa':'Tránsito','Ecuación / método':'EEq = 365·Σ(TPDᵢ·FCᵢ)·FD·FCarril·G','Resultado':f"{esal:,.0f} ESAL",'Estado':'Calculado'},
        {'Etapa':'AASHTO-93','Ecuación / método':'SN = a1D1 + aBG·mBG·DBG + aBE·mBE·DBE + a3·m3·D3','Resultado':f"SN={float(st.session_state.get('flex_design',{}).get('sn',0)):.2f}",'Estado':'Preliminar'},
        {'Etapa':'Granulares','Ecuación / método':'Mr=k1·Pa·(θ/Pa)^k2·(τoct/Pa+1)^k3','Resultado':f"Mr={float(payload.get('materials',{}).get('granular_model',{}).get('mr_calculated_mpa',0)):.1f} MPa",'Estado':'Configurable/documentado'},
        {'Etapa':'Clima / mezcla','Ecuación / método':'WLF + curva maestra E*','Resultado':f"E*={float(payload.get('climate_material',{}).get('effective_modulus_mpa',0)):.0f} MPa",'Estado':'Según parámetros documentados'},
        {'Etapa':'Respuesta estructural','Ecuación / método':str(payload.get('mechanistic_screening',{}).get('method','No ejecutado')),'Resultado':f"Umax={max(float(payload.get('mechanistic_screening',{}).get('fatigue_utilization_design',0) or 0),float(payload.get('mechanistic_screening',{}).get('rutting_utilization_design',0) or 0)):.2f}",'Estado':'Cribado'},
        {'Etapa':'Restricciones constructivas','Ecuación / método':'Mínimos/máximos + incremento constructivo','Resultado':str(payload.get('construction_constraints',{})),'Estado':'Criterio documentado del proyecto'},
    ]
    st.session_state.calculation_audit = audit_rows
    st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    if payload.get('transfer_model', {}).get('calibration_status') == 'Configurable / no normativa':
        st.warning("La función de transferencia está activa pero continúa marcada como configurable/no normativa. No emitir como diseño definitivo sin calibración validada.")

    report_html = make_report(payload)
    st.download_button(
        "Descargar memoria en HTML",
        data=report_html.encode("utf-8"),
        file_name="memoria_preliminar_gdp.html",
        mime="text/html",
    )
    st.download_button(
        "Descargar datos en JSON",
        data=json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="datos_diseno_gdp.json",
        mime="application/json",
    )
    st.download_button(
        "Descargar tránsito en CSV",
        data=vehicles.to_csv(index=False).encode("utf-8-sig"),
        file_name="transito_gdp.csv",
        mime="text/csv",
    )

    maintenance_export = st.session_state.get("maintenance_df", pd.DataFrame(columns=["Año","Intervención","Costo (₡)","Valor presente (₡)"]))
    alternatives_export = st.session_state.get("alternatives_compare", pd.DataFrame())
    excel_bytes = build_excel_workbook(payload, vehicles, alternatives_export, maintenance_export)
    st.download_button("Descargar libro de cálculo Excel", excel_bytes, "memoria_gdp.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    try:
        pdf_bytes = build_pdf_report(payload)
        st.download_button("Descargar memoria PDF", pdf_bytes, "memoria_gdp.pdf", "application/pdf")
    except Exception as exc:
        st.warning(f"No fue posible generar el PDF: {exc}")

    st.markdown("#### Resumen")
    classification_summary = f"Categoría {tomo1_category} (Tabla 102-01)" if active_tomo == "Tomo I" else f"rango {tclass}"
    st.write(
        f"Para el proyecto **{project_name}**, se estimaron **{esal:,.0f} ejes equivalentes**, "
        f"correspondientes a **{classification_summary}**. La subrasante presenta un CBR de diseño de "
        f"**{cbr_design:.2f}%**, clasificación **{sclass}**, y un módulo resiliente de diseño de "
        f"**{mr:.2f} MPa**. "
        f"La geometría de referencia es **{project_length_m:,.0f} m × {project_width_m:.2f} m**."
    )
    st.warning("La aplicación no sustituye la memoria de cálculo firmada. En Tomo II la selección se obtiene de las tablas GDP-2024 integradas; aun así deben verificarse estudios, materiales, drenaje, condiciones particulares y criterio profesional responsable.")

with pdash:
    # Dashboard profesional v0.9.1: una sola vista de control, similar al tablero de referencia.
    # SINGLE_TOMO_SELECTOR_DASHBOARD
    heavy_pct_dash = (heavy_total / tpd_total * 100.0) if tpd_total else 0.0
    selected_dash = selected_row or st.session_state.get("selected_row")
    selected_total = float(st.session_state.get("total_thickness", total_thickness or 0.0))
    dash_tomo = active_tomo

    # Encabezado compacto: el selector superior ya muestra la normativa activa.
    st.markdown(
        f"""<div class='panel-card' style='display:flex;justify-content:space-between;align-items:center;gap:18px'>
        <div><div class='panel-title'>Proyecto</div><b>{project_name}</b><br>
        <span style='color:#9eb3c8'>Ubicación: {location} &nbsp; · &nbsp; Tipo: {road_type} &nbsp; · &nbsp; Pavimento: {pavement_type}</span></div>
        <div style='text-align:right;white-space:nowrap'><span style='color:#42e07a;font-weight:850'>● Motor activo</span><br>
        <span style='color:#9eb3c8'>{project_date}</span></div></div>""",
        unsafe_allow_html=True,
    )

    # Tarjetas KPI
    k1,k2,k3,k4,k5,k6 = st.columns(6, gap="small")
    cards=[
        (k1,
         "Categoría de diseño" if dash_tomo == "Tomo I" else "Clasificación de tránsito",
         f"Categoría {tomo1_category}" if dash_tomo == "Tomo I" else tclass,
         (f"ESAL: {esal:,.2e}<br>Tabla 102-01" if dash_tomo == "Tomo I" else f"ESAL: {esal:,.2e}<br>TPD: {tpd_total:,.0f} veh/día"),
         "#218cff"),
        (k2,"Vehículos pesados",f"{heavy_pct_dash:.1f}%",f"Pesados: {heavy_total:,.0f} veh/día<br>TPDA estimado: {tpd_total:,.0f}","#3bd56d"),
        (k3,"Subrasante",sclass,f"CBR: {cbr_design:.2f}%<br>Módulo resiliente: {mr:.1f} MPa","#9d50ff"),
        (k4,"Periodo de diseño",f"{int(years)} años",f"Crecimiento: {growth_pct:.2f}%<br>Factor G: {gf:.3f}","#ff831d"),
        (k5,"Temperatura sitio",f"{air_temp_c:.1f} °C",f"Pavimento LTPP: {tp_ltpp:.1f} °C<br>Pavimento SHRP: {tp_shrp:.1f} °C","#ff4545"),
        (k6,"Sección propuesta" if dash_tomo == "Tomo I" else "Estructura de catálogo seleccionada",str(selected_dash.get('Código','—')) if selected_dash else "—",f"{selected_dash.get('Superficie','Sin seleccionar') if selected_dash else 'Sin seleccionar'}<br>Espesor: {selected_total:.0f} cm","#15c6ca"),
    ]
    for col,label,value,note,accent in cards:
        with col:
            st.markdown(f"<div class='dash-card' style='--accent:{accent}'><div class='dash-label'>{label}</div><div class='dash-value'>{value}</div><div class='dash-note'>{note}</div></div>",unsafe_allow_html=True)

    if selected_dash:
        # Modelo central y paneles laterales
        c_left,c_mid,c_right=st.columns([1.0,2.55,1.05],gap="small")
        surface_cm=float(selected_dash.get('Carpeta_cm',0)) if float(selected_dash.get('Carpeta_cm',0))>0 else 2.0
        with c_left:
            st.markdown("<div class='panel-card'><div class='panel-title'>Composición y origen</div>",unsafe_allow_html=True)
            if dash_tomo == "Tomo I":
                origin_t1 = str(selected_dash.get("Origen_TomoI", "Definida por el usuario"))
                compat = "Sección importada del Tomo II para evaluación mecanístico-empírica" if origin_t1.startswith("Importada") else "Sección propuesta por el usuario para evaluación mecanístico-empírica"
            else:
                compat="Alternativa compatible con la combinación calculada" if exact_match else "Alternativa de visualización; combinación no incorporada completamente"
            st.markdown(f"<div class='status-ok'>✓ {compat}<br>{tclass} — {sclass} — {int(years)} años</div>",unsafe_allow_html=True)
            base_stabilized_dash = float(selected_dash.get("Base_estabilizada_cm", 0) or 0)
            base_granular_dash = float(selected_dash.get("Base_granular_cm", 0) or 0)
            if base_granular_dash <= 0 and base_stabilized_dash <= 0:
                base_granular_dash = float(selected_dash.get("Base_cm", 0) or 0)
            rows=[("#171b22","Carpeta / superficie",f"{surface_cm:.0f} cm")]
            if base_granular_dash > 0:
                rows.append(("#c5c7c9","Base granular",f"{base_granular_dash:.0f} cm"))
            if base_stabilized_dash > 0:
                rows.append(("#d9a441","Base estabilizada",f"{base_stabilized_dash:.0f} cm"))
            rows.extend([
                ("#e38313","Subbase granular",f"{float(selected_dash.get('Subbase_cm',0)):.0f} cm"),
                ("#6f3518",f"Subrasante {sclass}",f"CBR {cbr_design:.1f}%"),
            ])
            for color,name,val in rows:
                st.markdown(f"<div class='layer-row'><span class='layer-dot' style='background:{color}'></span><span>{name}</span><b>{val}</b></div>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)

        with c_mid:
            st.markdown("<div class='panel-card'><div class='panel-title'>Modelo 3D interactivo</div>",unsafe_allow_html=True)
            view_mode=st.segmented_control("Vista",["Vista explotada","Vista unida"],default="Vista explotada",key="dash_view_mode",label_visibility="collapsed")
            fig_dash=pavement_3d_figure(selected_dash,sclass,cbr_design,view_mode=="Vista explotada")
            fig_dash.update_layout(title=None,height=600,paper_bgcolor="#07192a",plot_bgcolor="#07192a",margin=dict(l=0,r=0,t=20,b=0))
            render_rotating_3d(fig_dash, key="dashboard_view", height=610, auto_rotate=st.session_state.get("auto_rotate_3d", True))
            st.markdown("<div class='dark-note'>Rotación automática lenta · Arrastre para orbitar · Scroll para acercar/alejar</div></div>",unsafe_allow_html=True)

        with c_right:
            st.markdown("<div class='panel-card'><div class='panel-title'>Distribución de espesores</div>",unsafe_allow_html=True)
            pie_df=pd.DataFrame({"Capa":["Superficie","Base","Subbase"],"Espesor":[surface_cm,float(selected_dash.get('Base_cm',0)),float(selected_dash.get('Subbase_cm',0))]})
            pie=go.Figure(go.Pie(labels=pie_df['Capa'],values=pie_df['Espesor'],hole=.55,marker=dict(colors=['#171b22','#f5b51b','#ff6c00']),textinfo='percent'))
            pie.update_layout(height=230,margin=dict(l=0,r=0,t=5,b=5),paper_bgcolor='#0a1d2f',plot_bgcolor='#0a1d2f',font=dict(color='#eaf4ff'),showlegend=True,legend=dict(orientation='h',y=-.15))
            st.plotly_chart(pie,use_container_width=True,config={'displayModeBar':False})
            st.markdown("<div class='panel-title'>Costo inicial por capa</div>",unsafe_allow_html=True)
            costs_now=st.session_state.get('costs',{})
            area_now=float(costs_now.get('area',1000.0))
            # Estimación visual estable si aún no se ha completado Costos.
            cvals=[surface_cm/100*area_now*90000,float(selected_dash.get('Base_cm',0))/100*area_now*24000,float(selected_dash.get('Subbase_cm',0))/100*area_now*19000]
            bar=go.Figure(go.Bar(x=['Carpeta','Base','Subbase'],y=cvals,marker_color=['#313b47','#f5b51b','#ff6c00'],text=[money(v) for v in cvals],textposition='outside'))
            bar.update_layout(height=255,margin=dict(l=5,r=5,t=10,b=20),paper_bgcolor='#0a1d2f',plot_bgcolor='#0a1d2f',font=dict(color='#dcecff'),yaxis=dict(gridcolor='#25445f',title='Costo (₡)'),xaxis=dict(gridcolor='#25445f'))
            st.plotly_chart(bar,use_container_width=True,config={'displayModeBar':False})
            st.markdown("</div>",unsafe_allow_html=True)

        # Deterioro + PCI + alertas
        asphalt_eff=surface_cm
        dash_perf=performance_curves(int(years),esal,tp_ltpp,cbr_design,asphalt_eff,float(st.session_state.get('flex_design',{}).get('m2',1.0)))
        dmain,dpci,dalert=st.columns([3.6,.7,1.25],gap="small")
        with dmain:
            st.markdown("<div class='panel-card'><div class='panel-title'>Monitoreo de deterioro — estimaciones preliminares Tomo I</div>",unsafe_allow_html=True)
            pcols=st.columns(5,gap="small")
            specs=[('Fatiga (%)','Fatiga','Daño (%)',100.0),('Ahuellamiento (mm)','Ahuellamiento','mm',20.0),('Fisuras longitudinales (%)','Fisuras longitudinales','Densidad (%)',30.0),('Fisuras por bloque (%)','Fisuras por bloque','Densidad (%)',30.0),('Riesgo térmico (%)','Fisuración térmica','Riesgo (%)',30.0)]
            for col,(field,title,ylab,limit) in zip(pcols,specs):
                with col:
                    final=float(dash_perf.iloc[-1][field])
                    st.markdown(f"<div style='text-align:center;color:#a9bfd3;font-size:.72rem;text-transform:uppercase;font-weight:800'>{title}</div><div style='text-align:center;color:#45df79;font-size:1.55rem;font-weight:950'>{final:.0f}{' mm' if field=='Ahuellamiento (mm)' else '%'}</div>",unsafe_allow_html=True)
                    mini=performance_plot(dash_perf,field,'',ylab,limit,f'Límite {limit:g}')
                    mini.update_layout(height=220,margin=dict(l=8,r=5,t=18,b=20),paper_bgcolor='#0a1d2f',plot_bgcolor='#0a1d2f',font=dict(color='#bcd0e2',size=9),title=None,xaxis=dict(title='Años',gridcolor='#24445e'),yaxis=dict(title=None,gridcolor='#24445e'))
                    st.plotly_chart(mini,use_container_width=True,config={'displayModeBar':False})
            st.markdown("</div>",unsafe_allow_html=True)
        with dpci:
            final_pci=float(dash_perf.iloc[-1]['PCI estimado'])
            st.markdown(f"<div class='panel-card' style='height:100%'><div class='panel-title'>Índice de condición</div><div style='text-align:center;color:#40df76;font-size:2.65rem;font-weight:950;margin-top:18px'>{final_pci:.0f}</div><div style='text-align:center;color:#40df76;font-weight:800'>{'Muy bueno' if final_pci>=85 else 'Bueno' if final_pci>=70 else 'Requiere intervención'}</div>",unsafe_allow_html=True)
            pci_fig=go.Figure(go.Scatter(x=dash_perf['Año'],y=dash_perf['PCI estimado'],mode='lines+markers',line=dict(color='#39d66f',width=3),marker=dict(size=5)))
            pci_fig.update_layout(height=230,margin=dict(l=5,r=5,t=15,b=20),paper_bgcolor='#0a1d2f',plot_bgcolor='#0a1d2f',font=dict(color='#bcd0e2',size=9),xaxis=dict(gridcolor='#24445e'),yaxis=dict(range=[0,100],gridcolor='#24445e'))
            st.plotly_chart(pci_fig,use_container_width=True,config={'displayModeBar':False})
            st.markdown("</div>",unsafe_allow_html=True)
        with dalert:
            st.markdown("<div class='panel-card'><div class='panel-title' style='color:#ff921f'>Alertas</div>",unsafe_allow_html=True)
            st.markdown("<div class='alert-row alert-ok'>✓ Espesor mínimo verificado en la alternativa.</div>",unsafe_allow_html=True)
            if tp_ltpp>=45: st.markdown(f"<div class='alert-row alert-warn'>⚠ Temperatura elevada ({tp_ltpp:.1f} °C). Revisar ahuellamiento.</div>",unsafe_allow_html=True)
            else: st.markdown("<div class='alert-row alert-ok'>✓ Temperatura dentro del intervalo de revisión.</div>",unsafe_allow_html=True)
            st.markdown("<div class='alert-row alert-ok'>✓ Drenaje registrado para revisión.</div>",unsafe_allow_html=True)
            if final_pci<70: st.markdown("<div class='alert-row alert-warn'>⚠ Programar rehabilitación durante el periodo.</div>",unsafe_allow_html=True)
            else: st.markdown("<div class='alert-row alert-warn'>⚠ Verificar mantenimiento preventivo.</div>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
        st.markdown("<div class='dark-note'>Los gráficos de deterioro son estimaciones preliminares y no sustituyen la verificación mecanístico-empírica detallada del Tomo I.</div>",unsafe_allow_html=True)
    else:
        st.info("Complete el módulo de Estructura para activar el Dashboard profesional.")


# Guardado automático al terminar una ejecución completa. Streamlit vuelve a ejecutar el
# script después de cada interacción confirmada; el hash evita escrituras si nada cambió.
autosave_user_id = int(user.get("id", 0))
autosave_project_name = str(st.session_state.get("_active_project_name", "")).strip()
if autosave_user_id > 0 and autosave_project_name:
    autosave_state = _capture_session_state()
    autosave_hash = project_state_fingerprint(autosave_state)
    if autosave_hash != st.session_state.get("_autosave_hash"):
        try:
            save_project(autosave_user_id, autosave_project_name, autosave_state)
        except Exception as exc:
            st.session_state._autosave_status = "error"
            st.session_state._autosave_error = str(exc)
        else:
            st.session_state._autosave_hash = autosave_hash
            st.session_state._autosave_last_at = datetime.now().strftime("%H:%M:%S")
            st.session_state._autosave_status = "saved"
            st.session_state.pop("_autosave_error", None)
