from pathlib import Path

APP = Path('app.py')
text = APP.read_text(encoding='utf-8')
MARKER = '# FIX_PROJECT_MAP_PVALID_COLLISION'
if MARKER in text:
    print('Colisión pvalid ya corregida.')
    raise SystemExit(0)

old = '''            pvalid = bool(is_plausible_costa_rica_wgs84(plon, plat))\n        except Exception:\n            pe = pn = plat = plon = 0.0\n            pvalid = False\n        resolved_geo_points.append({\n            "name": pname, "type": ptype, "system_input": psystem, "description": pdesc,\n            "crtm_easting": float(pe), "crtm_northing": float(pn),\n            "latitude": float(plat), "longitude": float(plon), "valid": pvalid,\n        })\n'''

new = '''            # FIX_PROJECT_MAP_PVALID_COLLISION\n            point_is_valid = bool(is_plausible_costa_rica_wgs84(plon, plat))\n        except Exception:\n            pe = pn = plat = plon = 0.0\n            point_is_valid = False\n        resolved_geo_points.append({\n            "name": pname, "type": ptype, "system_input": psystem, "description": pdesc,\n            "crtm_easting": float(pe), "crtm_northing": float(pn),\n            "latitude": float(plat), "longitude": float(plon), "valid": point_is_valid,\n        })\n'''

count = text.count(old)
if count != 1:
    raise RuntimeError(f'Bloque esperado de pvalid encontrado {count} veces.')
text = text.replace(old, new, 1)

# pvalid debe existir únicamente como handle de la pestaña de Validación y en `with pvalid:`.
for forbidden in ('pvalid = bool(', 'pvalid = False', '"valid": pvalid'):
    if forbidden in text:
        raise RuntimeError(f'Persistió una reasignación peligrosa de pvalid: {forbidden}')

APP.write_text(text, encoding='utf-8')
print('Colisión corregida: el estado de puntos usa point_is_valid y pvalid queda reservado para la pestaña Validación.')
