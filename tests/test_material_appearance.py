from material_appearance import material_description, material_kind, material_style


def test_each_structural_material_has_a_distinct_kind():
    names = ["Base granular", "Base estabilizada", "Subbase granular", "Subrasante S3"]
    assert [material_kind(name) for name in names] == [
        "granular_base", "stabilized_base", "granular_subbase", "subgrade"
    ]


def test_styles_are_visually_independent_and_documented():
    styles = [material_style(name) for name in ("Base granular", "Base estabilizada", "Subbase granular")]
    assert len({style["seed"] for style in styles}) == 3
    assert len({style["edge"] for style in styles}) == 3
    assert "angular" in material_description("Base granular")
    assert "uniforme" in material_description("Base estabilizada")
