import pytest
from transformer_optimizer import CoreMaterial, SecondarySpec, TransformerSpec


@pytest.fixture
def material():
    return CoreMaterial("test steel", 7650.0, 0.003, 1.5, 2.0)


@pytest.fixture
def spec():
    return TransformerSpec(230.0, 50.0, 253.0, (SecondarySpec(35.0, 7.0, 2),),
                           1.4, 2.5e6, 2.8e6, core_thermal_resistance=1.5,
                           copper_thermal_resistance=1.5)
