from transformer_optimizer.physics.magnetic import flux_density, primary_turns


def test_flux_monotonic():
    assert flux_density(230, 50, 400, .002) > flux_density(230, 50, 500, .002)
    assert flux_density(253, 50, 400, .002) > flux_density(230, 50, 400, .002)
    assert primary_turns(230, 50, 1.2, .003) < primary_turns(230, 50, 1.2, .002)
