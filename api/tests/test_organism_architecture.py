try:
    from api.services.organism_architecture import ORGANISM_LAYERS, organism_status
except ModuleNotFoundError:  # Docker image copies api/ contents to /app.
    from services.organism_architecture import ORGANISM_LAYERS, organism_status


def test_organism_layers_cover_fahmi_architecture_terms():
    ids = {layer["id"] for layer in ORGANISM_LAYERS}

    assert {
        "jiwa",
        "otak",
        "pikiran",
        "akal",
        "syaraf",
        "indera",
        "organ",
        "metabolisme",
        "imun",
    }.issubset(ids)


def test_organism_status_exposes_safe_next_steps():
    status = organism_status()

    assert status["doctrine"] == "digital_organism_architecture"
    assert status["promotion_rule"] == "proposal_gated"
    assert "partial" in status["status_legend"]
    assert status["layers"][0]["id"] == "jiwa"
    assert all(layer["next_step"] for layer in status["layers"])


def test_each_organism_layer_maps_live_status_and_backlog():
    allowed = {"live", "partial", "planned", "blocked"}

    for layer in ORGANISM_LAYERS:
        assert layer["implementation_status"] in allowed
        assert layer["live_components"]
        assert layer["backlog_refs"]
