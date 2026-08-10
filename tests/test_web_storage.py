from __future__ import annotations

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
