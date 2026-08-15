from __future__ import annotations


EPHEMERAL_STATE_KEYS = {
    "auth_user", "auth_view", "login_user", "login_password", "reg_user", "reg_name", "reg_password",
    "project_save_name", "project_pick", "confirm_delete_project", "_loaded_project_notice",
    "main_project_save_name", "main_project_search", "main_project_pick", "main_confirm_delete_project",
    "main_save_project", "main_open_project", "main_delete_project",
}


def is_ephemeral_state_key(key: object) -> bool:
    """Return True for widget-owned state that must not be restored directly."""
    text = str(key)
    return (
        text in EPHEMERAL_STATE_KEYS
        or text.startswith("FormSubmitter")
        or text.endswith("_editor")
        or text.startswith("climate_monthly_editor_")
    )


def is_active_control_key(key: object) -> bool:
    """Keys already instantiated above the project loader and unsafe to delete mid-run."""
    text = str(key)
    return text in EPHEMERAL_STATE_KEYS or text.startswith("FormSubmitter")
