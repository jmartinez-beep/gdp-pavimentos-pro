from project_state import is_active_control_key, is_ephemeral_state_key, tomo1_structure_identifier


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
    assert is_ephemeral_state_key("_pending_active_tomo")
    assert is_ephemeral_state_key("_pending_tomo1_import")
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
