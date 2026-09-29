import pytest
from transformer_optimizer import RoundWire, WindingWire
from transformer_optimizer.physics.copper import resistance


def test_resistance_scaling():
    a = WindingWire(RoundWire(.001, .0011))
    b = WindingWire(RoundWire(.002, .0022))
    assert resistance(a, 20, 20) == pytest.approx(2 * resistance(a, 10, 20))
    assert resistance(a, 10, 20) == pytest.approx(4 * resistance(b, 10, 20))
    assert resistance(a, 10, 80) > resistance(a, 10, 20)
