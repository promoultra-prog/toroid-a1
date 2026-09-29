from transformer_optimizer import TransformerSearchSpace, optimize_transformer


def test_optimizer_smoke(spec, material):
    space = TransformerSearchSpace(
        outer_diameter=(.15, .18), inner_diameter=(.08, .10), height=(.06, .08),
        design_flux_density=(1.1, 1.25), primary_wire_diameter=(.0013, .0016),
        secondary_wire_diameter=(.0023, .0029),
        secondary_parallel_count=(2, 2), material=material)
    result = optimize_transformer(spec, space, population=20, generations=3, seed=3)
    assert result.candidates
    assert all(r.valid for r in result.evaluations)
    assert len(result.objectives) == len(result.candidates)
    assert not result.dataframe.empty
    first = result.evaluations[0]
    assert result.dataframe.iloc[0]["VA"] == sum(
        voltage * current for voltage, current in zip(
            first.secondary_voltage_full_load, first.secondary_currents, strict=True))
