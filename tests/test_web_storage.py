from __future__ import annotations

import json
from datetime import date

import pandas as pd

import web_storage


def _use_temp_sqlite(tmp_path):
    web_storage.DATABASE_URL = ""
    web_storage.DB_PATH = tmp_path / "gdp_test.sqlite3"
    web_storage.init_db()


def test_sqlite_user_and_project_roundtrip(tmp_path):
    _use_temp_sqlite(tmp_path)

    ok, message = web_storage.create_user("ingeniero", "ClaveSegura123", "Ingeniero Prueba")
    assert ok, message

    user = web_storage.authenticate("INGENIERO", "ClaveSegura123")
    assert user is not None
    assert user["display_name"] == "Ingeniero Prueba"

    state = {
        "project_name": "Ruta piloto",
        "project_date": date(2026, 8, 10),
        "selected_row": {"Código": "EBG-2", "Carpeta_cm": 5.0},
        "vehicles": pd.DataFrame(
            [["Camión C2", 0.8, 35]],
            columns=["Categoría", "Factor camión", "TPD"],
        ),
        "tomo_scenarios": {
            "tomo1": {
                "growth_pct": 7.1,
                "subgrade": {"cbr": 7.2, "liquid_limit_pct": 35.0},
                "vehicles": pd.DataFrame([[100.0]], columns=["TPD"]),
            },
            "tomo2": {
                "growth_pct": 3.0,
                "subgrade": {"cbr": 5.0, "liquid_limit_pct": 20.0},
                "vehicles": pd.DataFrame([[200.0]], columns=["TPD"]),
            },
        },
    }

    web_storage.save_project(user["id"], "Ruta piloto", state)
    projects = web_storage.list_projects(user["id"])
    assert len(projects) == 1
    assert projects[0]["name"] == "Ruta piloto"

    restored = web_storage.load_project(user["id"], projects[0]["id"])
    assert restored is not None
    assert restored["project_name"] == "Ruta piloto"
    assert restored["project_date"] == date(2026, 8, 10)
    assert restored["selected_row"]["Código"] == "EBG-2"
    assert restored["vehicles"].iloc[0]["TPD"] == 35
    assert restored["tomo_scenarios"]["tomo1"]["subgrade"]["cbr"] == 7.2
    assert restored["tomo_scenarios"]["tomo2"]["subgrade"]["cbr"] == 5.0
    assert restored["tomo_scenarios"]["tomo1"]["vehicles"].iloc[0]["TPD"] == 100.0
    assert restored["tomo_scenarios"]["tomo2"]["vehicles"].iloc[0]["TPD"] == 200.0


def test_save_same_name_updates_project(tmp_path):
    _use_temp_sqlite(tmp_path)
    ok, _ = web_storage.create_user("usuario2", "ClaveSegura456", "Usuario 2")
    assert ok
    user = web_storage.authenticate("usuario2", "ClaveSegura456")
    assert user is not None

    web_storage.save_project(user["id"], "Proyecto A", {"cbr": 5.0})
    web_storage.save_project(user["id"], "Proyecto A", {"cbr": 7.0})

    projects = web_storage.list_projects(user["id"])
    assert len(projects) == 1
    restored = web_storage.load_project(user["id"], projects[0]["id"])
    assert restored["cbr"] == 7.0


def test_backend_name_reflects_database_url(monkeypatch):
    monkeypatch.setattr(web_storage, "DATABASE_URL", "postgresql://example.invalid/db")
    assert web_storage.backend_name() == "postgresql"
    monkeypatch.setattr(web_storage, "DATABASE_URL", "")
    assert web_storage.backend_name() == "sqlite"


def test_project_fingerprint_is_stable_and_detects_changes():
    state_a = {"cbr": 5.0, "vehicles": pd.DataFrame([[35, 0.8]], columns=["TPD", "FC"])}
    state_b = {"vehicles": pd.DataFrame([[35, 0.8]], columns=["TPD", "FC"]), "cbr": 5.0}
    state_c = {"cbr": 7.0, "vehicles": pd.DataFrame([[35, 0.8]], columns=["TPD", "FC"])}

    assert web_storage.project_state_fingerprint(state_a) == web_storage.project_state_fingerprint(state_b)
    assert web_storage.project_state_fingerprint(state_a) != web_storage.project_state_fingerprint(state_c)


def test_scenario_payload_with_dataframes_is_json_serializable():
    payload = {
        "scenarios": {
            "tomo1": {
                "vehicles": pd.DataFrame(
                    [["Camión C2", 152.5]], columns=["Categoría", "TPD"]
                ),
                "cbr_values": pd.DataFrame(
                    [[7.2, pd.Timestamp("2026-08-18")]], columns=["CBR", "Fecha"]
                ),
            },
            "tomo2": {"selected_row": {"Código": "EBE-2"}},
        }
    }

    encoded = json.dumps(web_storage.serialize_value(payload), ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["scenarios"]["tomo1"]["vehicles"]["__type__"] == "dataframe"
    assert decoded["scenarios"]["tomo1"]["cbr_values"]["records"][0]["Fecha"] == "2026-08-18T00:00:00"
