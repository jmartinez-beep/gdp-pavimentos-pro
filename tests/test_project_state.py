from project_state import is_active_control_key, is_ephemeral_state_key


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
