import pytest
from transformer_optimizer import ToroidalCore, RoundWire, WindingWire
from transformer_optimizer.physics.geometry import winding_geometry, GeometryError


def test_winding_build_and_window(material):
    core = ToroidalCore(.16, .08, .06, .95, material.density, material)
    small = WindingWire(RoundWire(.001, .0011))
    large = WindingWire(RoundWire(.002, .0022))
    a = winding_geometry(core, 100, small, .0005, .85, .015)
    b = winding_geometry(core, 100, large, .0005, .85, .015)
    c = winding_geometry(core, 200, small, .0005, .85, .015)
    assert b.inner_build > a.inner_build
    assert c.total_wire_length > a.total_wire_length
    assert c.mean_turn_length > a.mean_turn_length
    with pytest.raises(GeometryError):
        winding_geometry(core, 10000, large, .0005, .85, .015)
