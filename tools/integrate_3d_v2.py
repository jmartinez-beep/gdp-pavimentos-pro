from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

new_figure_block = r'''def _structure_layers_3d(selected: Dict, sclass: str, cbr: float):
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
'''

pattern = re.compile(r"def pavement_3d_figure\(.*?\n\ndef deterioration_3d_figure", re.S)
match = pattern.search(text)
if not match:
    raise SystemExit("No se encontró el bloque 3D principal")
text = text[:match.start()] + new_figure_block + "\n\n\ndef deterioration_3d_figure" + text[match.end():]

# Ajustar la cota superior del modelo de patologías al nuevo bloque visual de subrasante.
old_top = '''    asphalt_cm = float(selected.get("Carpeta_cm", 0) or 0)\n    if asphalt_cm <= 0:\n        asphalt_cm = 2.0\n    base_cm = float(selected.get("Base_cm", 0) or 0)\n    subbase_cm = float(selected.get("Subbase_cm", 0) or 0)\n    top_z = 25.0 + subbase_cm + base_cm + asphalt_cm\n'''
new_top = '''    top_z = _top_surface_z_3d(selected, sclass, cbr, vertical_scale=1.0, exploded=False)\n'''
if old_top not in text:
    raise SystemExit("No se encontró cálculo superior del modelo de patologías")
text = text.replace(old_top, new_top, 1)

old_ui = '''                exploded_view = st.toggle("Vista explotada 3D", value=True, help="Separa las capas para identificarlas con mayor facilidad.")\n                st.caption("Use el mouse para girar, acercar y desplazar el modelo.")\n\n            with right:\n                st.markdown("#### Modelo 3D interactivo")\n                fig_3d = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_view)\n                render_rotating_3d(fig_3d, key="structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))\n'''
new_ui = '''                exploded_view = st.toggle("Vista explotada 3D", value=True, help="Separa las capas para identificarlas con mayor facilidad.", key="gdp3d_exploded")\n                scale_label = st.selectbox("Escala vertical", ["Real (×1)", "Exagerada ×2", "Exagerada ×5"], index=0, key="gdp3d_vertical_scale")\n                vertical_scale = {"Real (×1)":1.0, "Exagerada ×2":2.0, "Exagerada ×5":5.0}[scale_label]\n                view_mode = st.selectbox("Modo de corte", ["Completa", "Media calzada", "Corte transversal", "Corte longitudinal"], key="gdp3d_view_mode")\n                available_layers = [x["name"] for x in _structure_layers_3d(selected_row, sclass, cbr_design)]\n                selected_layer_3d = st.selectbox("Resaltar capa", ["Todas"] + available_layers, key="gdp3d_selected_layer")\n                if vertical_scale > 1:\n                    st.warning(f"Visualización con exageración vertical ×{vertical_scale:g}. Los espesores rotulados conservan el valor de diseño real.")\n                st.caption("Las cotas corresponden al diseño. La subrasante se representa como medio semiinfinito, sin asignarle un espesor estructural ficticio.")\n\n            with right:\n                st.markdown("#### Visor estructural 3D v2")\n                fig_3d = pavement_3d_figure(selected_row, sclass, cbr_design, exploded_view, vertical_scale, view_mode, selected_layer_3d)\n                render_rotating_3d(fig_3d, key="structure_view", height=700, auto_rotate=st.session_state.get("auto_rotate_3d", True))\n\n            if len(options) > 1:\n                with st.expander("Comparar alternativas en 3D", expanded=False):\n                    comparison_codes = [str(v) for v in options["Código"].tolist() if str(v) != str(selected_row["Código"])]\n                    comparison_code = st.selectbox("Alternativa para comparar", comparison_codes, key="gdp3d_compare_code")\n                    comparison_row = options[options["Código"].astype(str) == comparison_code].iloc[0].to_dict()\n                    ca, cb = st.columns(2, gap="medium")\n                    with ca:\n                        st.markdown(f"**Seleccionada: {selected_row['Código']}**")\n                        fig_a = pavement_3d_figure(selected_row, sclass, cbr_design, False, 1.0, "Corte transversal", "Todas")\n                        render_rotating_3d(fig_a, key="compare_a", height=470, auto_rotate=False)\n                    with cb:\n                        st.markdown(f"**Comparación: {comparison_row['Código']}**")\n                        fig_b = pavement_3d_figure(comparison_row, sclass, cbr_design, False, 1.0, "Corte transversal", "Todas")\n                        render_rotating_3d(fig_b, key="compare_b", height=470, auto_rotate=False)\n                    compare_df = pd.DataFrame([\n                        ["Carpeta / superficie", float(selected_row.get("Carpeta_cm",0) or 0), float(comparison_row.get("Carpeta_cm",0) or 0)],\n                        ["Base total", float(selected_row.get("Base_cm",0) or 0), float(comparison_row.get("Base_cm",0) or 0)],\n                        ["Subbase", float(selected_row.get("Subbase_cm",0) or 0), float(comparison_row.get("Subbase_cm",0) or 0)],\n                    ], columns=["Componente", str(selected_row["Código"]), str(comparison_row["Código"])])\n                    st.dataframe(compare_df, use_container_width=True, hide_index=True)\n'''
if old_ui not in text:
    raise SystemExit("No se encontró bloque UI 3D")
text = text.replace(old_ui, new_ui, 1)

# Actualizar subtítulo general sin alterar la versión funcional de la aplicación.
text = text.replace("Diseño flexible, 3D y gestión multiusuario · piloto gratuito para validación pública.", "Diseño flexible, visor estructural 3D v2 y gestión multiusuario · piloto gratuito para validación pública.", 1)

APP.write_text(text, encoding="utf-8")
print("Integración 3D v2 aplicada")
