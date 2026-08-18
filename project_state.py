from __future__ import annotations


EPHEMERAL_STATE_KEYS = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice",
    "main_project_save_name", "main_project_search", "main_project_pick", "main_confirm_delete_project",
    "main_save_project", "main_new_project", "main_open_project", "main_delete_project",
    "run_screening_optimization", "evaluate_tomo2_in_tomo1",
    "apply_nearby_tomo2_period", "evaluate_unassigned_tomo2_in_tomo1",
    "_pending_active_tomo", "_pending_tomo1_import", "_pending_tomo2_design_period",
    "_active_project_name", "_autosave_hash", "_autosave_status", "_autosave_error",
    "_autosave_last_at",
}

ACTIVE_CONTROL_KEYS = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice",
    "main_project_save_name", "main_project_search", "main_project_pick", "main_confirm_delete_project",
    "main_save_project", "main_new_project", "main_open_project", "main_delete_project",
}

TOMO2_CATALOG_PREFIXES = ("EBE-", "EBG-", "ETS-")

SEGMENT_COORDINATE_KEYS = (
    "start_lat", "start_lon", "end_lat", "end_lon",
    "start_e", "start_n", "end_e", "end_n",
)


def merge_segment_coordinate_snapshot(
    saved: object, widget_values: dict[str, object]
) -> dict[str, float]:
    """Merge visible segment widgets into durable, mode-independent state."""
    result: dict[str, float] = {}
    if isinstance(saved, dict):
        for key in SEGMENT_COORDINATE_KEYS:
            try:
                result[key] = float(saved[key])
            except (KeyError, TypeError, ValueError):
                pass
    widget_to_field = {
        "project_segment_start_lat": "start_lat",
        "project_segment_start_lon": "start_lon",
        "project_segment_end_lat": "end_lat",
        "project_segment_end_lon": "end_lon",
        "project_segment_start_e": "start_e",
        "project_segment_start_n": "start_n",
        "project_segment_end_e": "end_e",
        "project_segment_end_n": "end_n",
    }
    for widget_key, field in widget_to_field.items():
        try:
            result[field] = float(widget_values[widget_key])
        except (KeyError, TypeError, ValueError):
            pass
    return result


def update_segment_coordinate_snapshot(
    saved: object, field: str, value: object
) -> dict[str, float]:
    """Update exactly one durable segment coordinate without touching the rest."""
    result = merge_segment_coordinate_snapshot(saved, {})
    if field not in SEGMENT_COORDINATE_KEYS:
        raise ValueError(f"Coordenada de tramo desconocida: {field}")
    result[field] = float(value)
    return result


def is_ephemeral_state_key(key: object) -> bool:
    """Return True for widget-owned state that must not be restored directly."""
    text = str(key)
    return (
        text in EPHEMERAL_STATE_KEYS
        or text.startswith("FormSubmitter")
        or text.startswith("download_")
        or text.endswith("_editor")
        or text.startswith("climate_monthly_editor_")
        or text.startswith("climate_tmi_editor_")
    )


def is_active_control_key(key: object) -> bool:
    """Keys already instantiated above the project loader and unsafe to delete mid-run."""
    text = str(key)
    return text in ACTIVE_CONTROL_KEYS or text.startswith("FormSubmitter")


def tomo1_structure_identifier(source: object, code: object) -> str:
    """Return an identifier that makes the Tomo I evaluation context explicit."""
    source_text = str(source or "").strip()
    code_text = str(code or "").strip()
    if source_text.startswith("Importada"):
        if code_text.startswith("T1-EVAL-"):
            return code_text
        return f"T1-EVAL-{code_text}" if code_text else "T1-EVAL-01"
    if (
        not code_text
        or code_text.startswith("T1-EVAL-")
        or code_text.startswith(TOMO2_CATALOG_PREFIXES)
    ):
        return "T1-PROP-01"
    return code_text
