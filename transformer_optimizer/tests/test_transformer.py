from transformer_optimizer import ToroidalCore, RoundWire, WindingWire, TransformerCandidate, ToroidalTransformerModel


def test_reference_transformer(spec, material):
    core = ToroidalCore(.16, .08, .06, .95, material.density, material)
    candidate = TransformerCandidate(core, 1.2,
        WindingWire(RoundWire(.0015, .00162)),
        WindingWire(RoundWire(.0025, .0027), 2))
    r = ToroidalTransformerModel().evaluate(spec, candidate)
    assert r.valid, r.violations
    assert r.primary_turns > 0 and all(n > 0 for n in r.secondary_turns)
    assert r.b_max_mains <= spec.max_flux_density
    assert r.total_loss > 0 and r.total_mass > 0
    assert all(a > b for a, b in zip(r.secondary_voltage_no_load,
                                     r.secondary_voltage_full_load, strict=True))
    assert r.magnetizing_current_estimated
    assert r.secondary_currents == (7.0, 7.0)


def test_bad_geometry_is_explicit(spec, material):
    core = ToroidalCore(.12, .05, .04, .95, material.density, material)
    candidate = TransformerCandidate(core, 1.1,
        WindingWire(RoundWire(.001, .00108)),
        WindingWire(RoundWire(.003, .00324), 2))
    r = ToroidalTransformerModel().evaluate(spec, candidate)
    assert not r.valid and r.violations
