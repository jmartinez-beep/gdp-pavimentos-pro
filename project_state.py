from __future__ import annotations


EPHEMERAL_STATE_KEYS = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice",
    "main_project_save_name", "main_project_search", "main_project_pick", "main_confirm_delete_project",
    "main_save_project", "main_open_project", "main_delete_project",
    "run_screening_optimization", "evaluate_tomo2_in_tomo1",
    "_pending_active_tomo", "_pending_tomo1_import",
    "_active_project_name", "_autosave_hash", "_autosave_status", "_autosave_error",
    "_autosave_last_at",
}

ACTIVE_CONTROL_KEYS = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice",
    "main_project_save_name", "main_project_search", "main_project_pick", "main_confirm_delete_project",
    "main_save_project", "main_open_project", "main_delete_project",
}

TOMO2_CATALOG_PREFIXES = ("EBE-", "EBG-", "ETS-")


def is_ephemeral_state_key(key: object) -> bool:
    """Return True for widget-owned state that must not be restored directly."""
    text = str(key)
    return (
        text in EPHEMERAL_STATE_KEYS
        or text.startswith("FormSubmitter")
        or text.startswith("download_")
        or text.endswith("_editor")
        or text.startswith("climate_monthly_editor_")
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
