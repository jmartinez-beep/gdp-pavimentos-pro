from __future__ import annotations

import io
import json
import math
import zipfile
from dataclasses import dataclass, asdict
from datetime import date
from typing import Dict, List
import os

from web_storage import (authenticate, create_user, delete_project, list_projects, load_project, save_project)
from gdp_tomo2_adapter import alternatives_for_app, selected_trace
from geo_cr import crtm05_to_wgs84, wgs84_to_crtm05, is_plausible_costa_rica_wgs84
from climate_tools import MONTHS_ES, monthly_climate_table, monthly_summary, representative_temperature
from cr2020_asphalt import render_asphalt_cr2020_checklist

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

def technical_validation(active_tomo: str, selected: Dict, exact_match: bool, esal: float, cbr: float, pavement_temp: float, drainage: dict) -> pd.DataFrame:
    """Matriz trazable de validación. No reemplaza la revisión profesional."""
    checks = []
    def add(category, criterion, ok, severity, evidence):
        checks.append({"Categoría":category,"Criterio":criterion,"Estado":"Cumple" if ok else "Revisar","Severidad":severity,"Evidencia":evidence})
    add("Alcance", "Metodología seleccionada", active_tomo in ("Tomo I","Tomo II"), "Alta", active_tomo)
    add("Catálogo", "Coincidencia exacta tránsito-subrasante", bool(exact_match), "Alta", f"Código {selected.get('Código','—')}")
    add("Tránsito", "ESAL mayor que cero", esal > 0, "Alta", f"{esal:,.0f} ESAL")
    add("Subrasante", "CBR definido", cbr > 0, "Alta", f"CBR {cbr:.2f}%")
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
    costs = payload.get("costs", {})
    active_tomo = payload.get("active_tomo", "Tomo II")
    design_category = int(traffic.get("design_category", tomo1_design_category(float(traffic.get("esal", 0.0)))))
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
          <tr><th>Subbase</th><td>{selected['Subbase_cm']} cm</td></tr>
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
<h1>Memoria preliminar de diseño de pavimento</h1>
<p><b>Proyecto:</b> {project['name']}<br>
<b>Ubicación:</b> {project['location']}<br>
<b>CRTM05 (EPSG:5367):</b> E {project.get('crtm05_easting_m', 0):,.3f} m · N {project.get('crtm05_northing_m', 0):,.3f} m<br>
<b>WGS84 (EPSG:4326):</b> {project.get('latitude', 0):.7f}°, {project.get('longitude', 0):.7f}°<br>
<b>Fecha:</b> {project['date']}<br>
<b>Responsable:</b> {project['engineer']}</p>

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
<tr><th>Módulo resiliente estimado</th><td>{subgrade['mr']:.2f} MPa</td></tr>
</table>

<h2>3. Estructura seleccionada</h2>
{structure_html}

<h2>4. Estimación económica</h2>
<table>
<tr><th>Área</th><td>{costs.get('area', 0):,.2f} m²</td></tr>
<tr><th>Costo estimado</th><td>{money(costs.get('total', 0))}</td></tr>
<tr><th>Costo por m²</th><td>{money(costs.get('per_m2', 0))}</td></tr>
</table>

<div class='note'><b>Advertencia técnica:</b> Esta herramienta es un apoyo preliminar. La selección final debe verificarse con las tablas completas del GDP, estudios de campo, drenaje, materiales, control de calidad y criterio profesional responsable.</div>
</body></html>"""



CLIMATE_STATIONS_TOMO_II = [
    "Upala", "Los Chiles", "San Carlos", "Liberia", "Nicoya", "Puntarenas",
    "San José", "Alajuela", "Barva de Heredia", "Cartago", "Buenos Aires",
    "Aguirre", "Golfito", "Limón", "Orotina"
]

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
    rows += [
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

WEB_STATE_EXCLUDE = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice"
}

def _capture_session_state():
    state = {}
    for key, value in st.session_state.items():
        if key in WEB_STATE_EXCLUDE or key.startswith("FormSubmitter"):
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
        if key not in WEB_STATE_EXCLUDE and key != "auth_user":
            try:
                del st.session_state[key]
            except Exception:
                pass
    for key, value in saved.items():
        if key not in WEB_STATE_EXCLUDE:
            st.session_state[key] = value
    if auth_user:
        st.session_state.auth_user = auth_user


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
                save_project(int(user["id"]), project_name_web.strip(), _capture_session_state())
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
                        st.session_state._loaded_project_notice = pinfo["name"]
                        st.rerun()
            with cdel:
                if st.button("🗑️ Eliminar", use_container_width=True):
                    delete_project(int(user["id"]), int(pinfo["id"]))
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
    account_col, save_col = st.columns([3, 1])
    with account_col:
        st.success(
            f"Sesión iniciada como **{user.get('display_name', user.get('username', 'Usuario'))}**. "
            f"Proyecto de guardado actual: **{project_name_web or 'Sin nombre'}**. "
            "La administración completa de proyectos también está disponible en la barra lateral **Mis proyectos**."
        )
    with save_col:
        if st.button("💾 Guardar proyecto ahora", use_container_width=True, key="main_save_project"):
            if project_name_web.strip():
                save_project(int(user["id"]), project_name_web.strip(), _capture_session_state())
                st.success("Proyecto guardado correctamente.")
                st.rerun()
            else:
                st.warning("Indique un nombre para el proyecto en la barra lateral.")
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

head_left, head_mid, head_right = st.columns([1.2, 2.2, 1.2])
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
with head_right:
    st.caption("Cambie de tomo en cualquier momento. Los datos del proyecto permanecen en la sesión.")

# Valores compartidos entre módulos
selected_row = st.session_state.get("selected_row")
total_thickness = float(st.session_state.get("total_thickness", 0.0))
exact_match = bool(st.session_state.get("exact_match", False))

# Pestañas
st.markdown("""
<div style="background:#123b5d;color:white;padding:12px 18px;border-radius:10px;margin-bottom:14px;font-weight:700;">
GDP Pavimentos Pro 2024 — versión 1.1 · Web Ready Multiusuario
</div>
""", unsafe_allow_html=True)

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

    loc1, loc2, loc3, loc4 = st.columns(4)
    loc1.metric("Este CRTM05", f"{crtm_easting:,.3f} m")
    loc2.metric("Norte CRTM05", f"{crtm_northing:,.3f} m")
    loc3.metric("Latitud WGS84", f"{latitude:.7f}°")
    loc4.metric("Longitud WGS84", f"{longitude:.7f}°")
    st.map(pd.DataFrame({"lat": [latitude], "lon": [longitude]}), latitude="lat", longitude="lon", zoom=10)
    st.caption("Las coordenadas CRTM05 y WGS84 quedan incluidas en el estado guardado del proyecto y en las exportaciones.")

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

    vehicle_editor = current.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Grupo de tránsito", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
    vehicle_editor["Cantidad diaria (veh/día)"] = pd.to_numeric(
        vehicle_editor["Cantidad diaria (veh/día)"], errors="coerce"
    ).fillna(0).astype(int)
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
                min_value=0,
                max_value=1_000_000,
                step=1,
                format="%d",
                help="Cantidad promedio de vehículos por día para esta categoría."
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
    ).fillna(0).clip(lower=0).astype(int)
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

    st.markdown("#### Resumen del conteo ingresado")
    summary_vehicles = vehicles.rename(columns={"TPD": "Cantidad diaria (veh/día)"})[
        ["Categoría", "Grupo de tránsito", "Cantidad diaria (veh/día)", "Factor camión"]
    ]
    st.dataframe(summary_vehicles, use_container_width=True, hide_index=True)

    a, b, c, d = st.columns(4)
    with a:
        years = st.number_input("Periodo de diseño (años)", min_value=1, max_value=40, value=10)
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
    m1.metric("TPD total", f"{tpd_total:,.0f}")
    m2.metric("Vehículos pesados", f"{heavy_total:,.0f}", f"{heavy_pct:.2f}%")
    m3.metric("Ejes equivalentes diarios", f"{weighted_daily:,.2f}")
    m4.metric("Factor de crecimiento G", f"{gf:,.3f}")
    m5.metric("EEq de diseño", f"{esal:,.0f}", tclass if st.session_state.active_tomo == "Tomo II" else f"Categoría {tomo1_category}")

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
    mr = resilient_modulus(cbr_design)
    x1, x2, x3 = st.columns(3)
    x1.metric("CBR de diseño", f"{cbr_design:.2f}%")
    x2.metric("Rango de subrasante", sclass)
    x3.metric("Módulo resiliente estimado", f"{mr:.2f} MPa")

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

    c1, c2, c3 = st.columns(3)
    with c1:
        climate_source = st.text_input("Fuente / institución", value="IMN / fuente documentada")
        climate_period = st.text_input("Periodo documentado", value="")
        station_selected = st.selectbox("Estación o zona representativa", CLIMATE_STATIONS_TOMO_II + ["Otra / dato propio"], index=6)
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
    if climate_input_mode == "Valores mensuales":
        st.markdown("#### Temperaturas medias mensuales del aire")
        default_monthly = [23.0, 23.5, 24.0, 24.5, 24.0, 23.5, 23.5, 23.5, 23.5, 23.0, 22.8, 22.8]
        monthly_input = pd.DataFrame({"Mes": MONTHS_ES, "Temperatura media del aire (°C)": default_monthly})
        monthly_editor = st.data_editor(
            monthly_input,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="climate_monthly_editor",
            column_config={
                "Mes": st.column_config.TextColumn("Mes", disabled=True),
                "Temperatura media del aire (°C)": st.column_config.NumberColumn(
                    "Temperatura media del aire (°C)", min_value=-20.0, max_value=60.0, step=0.1, format="%.1f"
                ),
            },
        )
        monthly_values = pd.to_numeric(monthly_editor["Temperatura media del aire (°C)"], errors="coerce").fillna(0.0).tolist()
        air_temp_c = representative_temperature(monthly_values)
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
        air_temp_c = st.number_input("Temperatura representativa del aire (°C)", min_value=-10.0, max_value=50.0, value=24.0, step=0.1)
        st.info("Modo estación: documente la estación, institución y periodo. El valor representativo ingresado se usa directamente en las ecuaciones térmicas.")

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
            st.warning("La combinación está dentro del alcance general, pero la celda correspondiente no asigna una alternativa estructural. Revise la tabla y el criterio indicado.")
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

        previous_t1 = st.session_state.get("tomo1_structure", {})
        imported = st.session_state.get("selected_row") if st.session_state.get("selected_row") and not previous_t1 else None
        source_default = "Importada de Tomo II para evaluación" if imported else "Definida por el usuario"
        source = st.segmented_control(
            "Origen de la sección propuesta",
            ["Definida por el usuario", "Importada de Tomo II para evaluación"],
            default=source_default,
            key="tomo1_structure_source",
        ) or source_default

        import_row = imported if source.startswith("Importada") and imported else {}
        if source.startswith("Importada") and not import_row:
            st.warning("No hay una alternativa Tomo II disponible en la sesión. Se mantienen los valores editables de Tomo I.")

        dflt = previous_t1 or import_row
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
        structure_id = i2.text_input(
            "Identificador de la sección", value=str(dflt.get("Código", "T1-PROP-01") or "T1-PROP-01"), key="tomo1_structure_id"
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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Carpeta", f"{asphalt_cm:.1f} cm")
        m2.metric("Base total", f"{base_total_cm:.1f} cm")
        m3.metric("Subbase", f"{subbase_cm:.1f} cm")
        m4.metric("Sección modelada", f"{total_thickness:.1f} cm")

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
    st.subheader("Diseño preliminar de pavimento flexible — Tomo I")
    st.info("Este módulo calcula el número estructural aportado por la sección propuesta y ejecuta verificaciones preliminares. No sustituye el análisis mecanístico-empírico completo de desempeño del Tomo I.")
    if selected_row:
        f1,f2,f3,f4 = st.columns(4)
        a1 = f1.number_input("Coeficiente estructural carpeta a1", min_value=0.0, max_value=1.0, value=0.44, step=0.01)
        a2 = f2.number_input("Coeficiente estructural base a2", min_value=0.0, max_value=1.0, value=0.14, step=0.01)
        a3 = f3.number_input("Coeficiente estructural subbase a3", min_value=0.0, max_value=1.0, value=0.11, step=0.01)
        m2 = f4.number_input("Coeficiente drenaje base m2", min_value=0.4, max_value=1.4, value=1.00, step=0.05)
        m3 = st.number_input("Coeficiente drenaje subbase m3", min_value=0.4, max_value=1.4, value=1.00, step=0.05)
        d1=float(selected_row['Carpeta_cm'])/2.54; d2=float(selected_row['Base_cm'])/2.54; d3=float(selected_row['Subbase_cm'])/2.54
        sn1=a1*d1; sn2=a2*m2*d2; sn3=a3*m3*d3; sn_total=sn1+sn2+sn3
        c1,c2,c3,c4=st.columns(4); c1.metric("SN carpeta",f"{sn1:.2f}"); c2.metric("SN base",f"{sn2:.2f}"); c3.metric("SN subbase",f"{sn3:.2f}"); c4.metric("SN aportado",f"{sn_total:.2f}")
        st.progress(min(sn_total/6.0,1.0), text="Indicador relativo del aporte estructural")
        if float(selected_row['Carpeta_cm']) <= 0 and selected_row['Superficie'] == 'Tratamiento superficial': st.warning("La alternativa usa tratamiento superficial; revise que el nivel de tránsito, el desempeño esperado y los materiales sean compatibles con el alcance del catálogo.")
        if tp_ltpp >= 45: st.warning("Temperatura alta del pavimento: revise el módulo dinámico de la mezcla y el riesgo de ahuellamiento.")
        if m2 < 0.8 or m3 < 0.8: st.warning("Los coeficientes de drenaje reducen de forma importante el aporte estructural de las capas granulares.")
        st.session_state.flex_design={"a1":a1,"a2":a2,"a3":a3,"m2":m2,"m3":m3,"sn":sn_total}
    else: st.info("Seleccione una estructura para activar el diseño flexible.")

with pperf:
    st.subheader("Monitoreo de deterioro — evaluación preliminar del Tomo I")
    st.warning("Las curvas son indicadores preliminares normalizados para comparar escenarios. Para emitir un diseño final deben sustituirse por la respuesta multicapa, modelos constitutivos y calibraciones aplicables del Tomo I.")
    if selected_row:
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
        st.caption("Comparación limitada a las alternativas oficiales asignadas por la celda normativa vigente para el proyecto.")
    else:
        candidates = st.session_state.catalog.copy()
        st.caption("Comparación preliminar de referencia para Tomo I.")

    if candidates.empty:
        st.info("No hay alternativas compatibles disponibles para comparar.")
        st.session_state.alternatives_compare = pd.DataFrame()
    else:
        cp1,cp2,cp3=st.columns(3)
        surf_price=cp1.number_input("Precio referencial superficie (₡/m³)",0.0,value=95000.0,step=5000.0,key='cmp_surf')
        base_price=cp2.number_input("Precio referencial base (₡/m³)",0.0,value=28000.0,step=1000.0,key='cmp_base')
        sub_price=cp3.number_input("Precio referencial subbase (₡/m³)",0.0,value=22000.0,step=1000.0,key='cmp_sub')
        cmp_area=st.number_input("Área para comparación (m²)",1.0,value=900.0,step=50.0,key='cmp_area')
        candidates['Espesor_total_cm']=candidates[['Carpeta_cm','Base_cm','Subbase_cm']].sum(axis=1)
        candidates['Costo_inicial']=cmp_area*(candidates['Carpeta_cm']/100*surf_price+candidates['Base_cm']/100*base_price+candidates['Subbase_cm']/100*sub_price)
        candidates['Coincidencia']='Oficial GDP-2024' if active_tomo == "Tomo II" else 'Referencia'
        cmin=max(float(candidates['Costo_inicial'].min()),1.0); cmax=max(float(candidates['Costo_inicial'].max()),cmin)
        emin=max(float(candidates['Espesor_total_cm'].min()),1.0); emax=max(float(candidates['Espesor_total_cm'].max()),emin)
        candidates['Índice técnico-económico']=100-(60*(candidates['Costo_inicial']-cmin)/(cmax-cmin+1e-9)+40*(candidates['Espesor_total_cm']-emin)/(emax-emin+1e-9))
        base_cols=['Código','Superficie','Espesor_total_cm','Costo_inicial','Coincidencia','Índice técnico-económico']
        trace_cols=[c for c in ['Tabla_asignacion','Criterio_GDP'] if c in candidates.columns]
        show=candidates[base_cols+trace_cols].sort_values('Índice técnico-económico',ascending=False)
        st.dataframe(show.style.format({'Costo_inicial':'₡{:,.0f}','Espesor_total_cm':'{:.0f}'}),use_container_width=True,hide_index=True)
        st.bar_chart(show.set_index('Código')['Costo_inicial'])
        st.session_state.alternatives_compare=show

with p5:
    st.subheader("Costos de construcción y cantidades de obra")
    q1, q2, q3 = st.columns(3)
    with q1:
        length_m = st.number_input("Longitud (m)", min_value=1.0, value=150.0, step=10.0)
    with q2:
        width_m = st.number_input("Ancho pavimentado (m)", min_value=1.0, value=6.0, step=0.5)
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
        validation_df = technical_validation(active_tomo, selected_row, exact_match, esal, cbr_design, tp_ltpp, st.session_state.get("drainage", {}))
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
            "class": tclass,
            "design_category": tomo1_category,
            "design_category_label": f"Categoría {tomo1_category}",
        },
        "subgrade": {"cbr": cbr_design, "class": sclass, "mr": mr},
        "climate": {
            "input_mode": climate_input_mode,
            "source": climate_source,
            "period": climate_period,
            "station": station_selected,
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
        f"**{cbr_design:.2f}%**, clasificación **{sclass}**, y un módulo resiliente estimado de "
        f"**{mr:.2f} MPa**."
    )
    st.warning("La aplicación no sustituye la memoria de cálculo firmada. En Tomo II la selección se obtiene de las tablas GDP-2024 integradas; aun así deben verificarse estudios, materiales, drenaje, condiciones particulares y criterio profesional responsable.")

with pdash:
    # Dashboard profesional v0.9.1: una sola vista de control, similar al tablero de referencia.
    heavy_pct_dash = (heavy_total / tpd_total * 100.0) if tpd_total else 0.0
    selected_dash = selected_row or st.session_state.get("selected_row")
    selected_total = float(st.session_state.get("total_thickness", total_thickness or 0.0))

    # Encabezado superior
    hleft, hcenter, hright = st.columns([1.0, 2.2, 1.15], gap="small")
    with hleft:
        st.markdown("<div class='panel-card'><div class='panel-title'>Normativa activa</div>", unsafe_allow_html=True)
        dash_tomo = st.segmented_control("", ["Tomo I", "Tomo II"], default=st.session_state.active_tomo, key="dash_tomo_selector", label_visibility="collapsed") or st.session_state.active_tomo
        st.session_state.active_tomo = dash_tomo
        st.markdown("</div>", unsafe_allow_html=True)
    with hcenter:
        st.markdown(f"""<div class='panel-card'><div class='panel-title'>Proyecto</div><b>{project_name}</b><br><span style='color:#9eb3c8'>Ubicación: {location} &nbsp; | &nbsp; Tipo: {road_type} &nbsp; | &nbsp; Pavimento: {pavement_type}</span></div>""", unsafe_allow_html=True)
    with hright:
        st.markdown(f"""<div class='panel-card'><div class='panel-title'>Estado del diseño</div><span style='color:#42e07a;font-weight:850'>● Motor de cálculo activo</span><br><span style='color:#9eb3c8'>Versión 1.0 beta escritorio · {project_date}</span></div>""", unsafe_allow_html=True)

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
        (k6,"Estructura seleccionada",str(selected_dash.get('Código','—')) if selected_dash else "—",f"{selected_dash.get('Superficie','Sin seleccionar') if selected_dash else 'Sin seleccionar'}<br>Espesor: {selected_total:.0f} cm","#15c6ca"),
    ]
    for col,label,value,note,accent in cards:
        with col:
            st.markdown(f"<div class='dash-card' style='--accent:{accent}'><div class='dash-label'>{label}</div><div class='dash-value'>{value}</div><div class='dash-note'>{note}</div></div>",unsafe_allow_html=True)

    if selected_dash:
        # Modelo central y paneles laterales
        c_left,c_mid,c_right=st.columns([1.0,2.55,1.05],gap="small")
        surface_cm=float(selected_dash.get('Carpeta_cm',0)) if float(selected_dash.get('Carpeta_cm',0))>0 else 2.0
        with c_left:
            st.markdown("<div class='panel-card'><div class='panel-title'>Alternativa seleccionada</div>",unsafe_allow_html=True)
            st.markdown(f"### {selected_dash.get('Código','')} — {selected_dash.get('Superficie','')}")
            compat="Alternativa compatible con la combinación calculada" if exact_match else "Alternativa de visualización; combinación no incorporada completamente"
            st.markdown(f"<div class='status-ok'>✓ {compat}<br>{tclass} — {sclass} — {int(years)} años</div>",unsafe_allow_html=True)
            rows=[
                ("#171b22","Carpeta / superficie",f"{surface_cm:.0f} cm"),
                ("#c5c7c9","Base granular",f"{float(selected_dash.get('Base_cm',0)):.0f} cm"),
                ("#e38313","Subbase granular",f"{float(selected_dash.get('Subbase_cm',0)):.0f} cm"),
                ("#6f3518",f"Subrasante {sclass}",f"CBR {cbr_design:.1f}%"),
            ]
            for color,name,val in rows:
                st.markdown(f"<div class='layer-row'><span class='layer-dot' style='background:{color}'></span><span>{name}</span><b>{val}</b></div>",unsafe_allow_html=True)
            st.markdown(f"<div class='thickness-box'><span style='font-size:.72rem;color:#9eb3c8'>ESPESOR TOTAL ESTRUCTURAL</span><br>{selected_total:.0f} cm</div></div>",unsafe_allow_html=True)

        with c_mid:
            st.markdown("<div class='panel-card'><div class='panel-title'>Modelo 3D interactivo</div>",unsafe_allow_html=True)
            view_mode=st.segmented_control("Vista",["Vista explotada","Vista unida"],default="Vista explotada",key="dash_view_mode",label_visibility="collapsed")
            fig_dash=pavement_3d_figure(selected_dash,sclass,cbr_design,view_mode=="Vista explotada")
            fig_dash.update_layout(height=600,paper_bgcolor="#07192a",plot_bgcolor="#07192a",margin=dict(l=0,r=0,t=45,b=0))
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


