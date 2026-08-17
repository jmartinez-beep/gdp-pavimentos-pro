from project_state import (
    is_active_control_key, is_ephemeral_state_key,
    merge_segment_coordinate_snapshot,
    tomo1_structure_identifier,
)


def test_data_editor_widget_keys_are_ephemeral():
    assert is_ephemeral_state_key("project_geo_points_editor")
    assert is_ephemeral_state_key("vehicle_composition_editor")
    assert is_ephemeral_state_key("homogeneous_segments_editor")
    assert is_ephemeral_state_key("climate_monthly_editor_Cartago")


def test_persistent_project_data_is_not_filtered():
    assert not is_ephemeral_state_key("project_geo_points_input")
    assert not is_ephemeral_state_key("homogeneous_segments_input")
    assert not is_ephemeral_state_key("project_geometry")


def test_editor_is_removed_during_restore_but_open_button_is_preserved():
    assert not is_active_control_key("project_geo_points_editor")
    assert is_active_control_key("main_open_project")


def test_autosave_runtime_metadata_is_not_persisted():
    assert is_ephemeral_state_key("_active_project_name")
    assert is_ephemeral_state_key("_autosave_hash")
    assert is_ephemeral_state_key("_autosave_last_at")


def test_button_state_is_not_persisted_or_restored():
    assert is_ephemeral_state_key("run_screening_optimization")
    assert is_ephemeral_state_key("evaluate_tomo2_in_tomo1")
    assert is_ephemeral_state_key("apply_nearby_tomo2_period")
    assert is_ephemeral_state_key("evaluate_unassigned_tomo2_in_tomo1")
    assert is_ephemeral_state_key("_pending_active_tomo")
    assert is_ephemeral_state_key("_pending_tomo1_import")
    assert is_ephemeral_state_key("_pending_tomo2_design_period")
    assert not is_active_control_key("run_screening_optimization")
    assert is_ephemeral_state_key("download_cr2020_asphalt_checklist")
    assert is_ephemeral_state_key("download_cr2010_asphalt_checklist")
    assert not is_active_control_key("download_cr2020_asphalt_checklist")


def test_tomo1_identifiers_distinguish_proposed_and_imported_sections():
    assert tomo1_structure_identifier("Definida por el usuario", "") == "T1-PROP-01"
    assert tomo1_structure_identifier("Importada de Tomo II para evaluación", "EBE-2") == "T1-EVAL-EBE-2"
    assert tomo1_structure_identifier("Importada de Tomo II para evaluación", "T1-EVAL-EBE-2") == "T1-EVAL-EBE-2"
    assert tomo1_structure_identifier("Definida por el usuario", "T1-EVAL-EBE-2") == "T1-PROP-01"
    assert tomo1_structure_identifier("Definida por el usuario", "EBE-2") == "T1-PROP-01"
    assert tomo1_structure_identifier("Definida por el usuario", "EBG-4") == "T1-PROP-01"
    assert tomo1_structure_identifier("Definida por el usuario", "ETS-1") == "T1-PROP-01"
    assert tomo1_structure_identifier("Definida por el usuario", "T1-PROP-JORCO") == "T1-PROP-JORCO"


def test_segment_coordinates_survive_when_widget_keys_disappear():
    saved = {
        "start_e": 479868.240,
        "start_n": 1084814.720,
        "end_e": 479993.620,
        "end_n": 1084705.720,
    }
    assert merge_segment_coordinate_snapshot(saved, {}) == saved


def test_visible_segment_widgets_update_durable_snapshot():
    saved = {"start_e": 1.0, "end_e": 2.0}
    widgets = {
        "project_segment_start_e": 479868.240,
        "project_segment_start_n": 1084814.720,
        "project_segment_end_e": 479993.620,
        "project_segment_end_n": 1084705.720,
    }
    merged = merge_segment_coordinate_snapshot(saved, widgets)
    assert merged["start_e"] == 479868.240
    assert merged["end_n"] == 1084705.720


def test_each_coordinate_change_is_safe_before_widgets_are_hidden():
    saved = {
        "start_e": 479000.0,
        "start_n": 1084000.0,
        "end_e": 479100.0,
        "end_n": 1084100.0,
    }
    after_edit = merge_segment_coordinate_snapshot(
        saved, {"project_segment_end_e": 479993.620}
    )
    after_switch_to_point = merge_segment_coordinate_snapshot(after_edit, {})
    assert after_switch_to_point["start_e"] == 479000.0
    assert after_switch_to_point["end_e"] == 479993.620
