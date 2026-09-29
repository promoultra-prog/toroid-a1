from transformer_optimizer import (
    CoreMaterial, SecondarySpec, TransformerSearchSpace, TransformerSpec, optimize_transformer
)


def main():
    # Illustrative loss fit only; replace with the chosen steel's datasheet curve.
    steel = CoreMaterial("example grain-oriented steel", 7650.0, 0.003, 1.5, 2.0)
    spec = TransformerSpec(
        mains_voltage=230.0, mains_frequency=50.0, mains_max_voltage=253.0,
        secondaries=(SecondarySpec(35.0, 7.0, quantity=2, maximum_no_load_voltage=39.0),),
        max_flux_density=1.4, max_current_density_primary=2.5e6,
        max_current_density_secondary=2.8e6,
        core_thermal_resistance=1.5, copper_thermal_resistance=1.5,
    )
    space = TransformerSearchSpace(
        outer_diameter=(0.12, 0.22), inner_diameter=(0.05, 0.10),
        height=(0.04, 0.09), design_flux_density=(1.1, 1.5),
        primary_wire_diameter=(0.7e-3, 1.6e-3),
        secondary_wire_diameter=(1.2e-3, 3.0e-3),
        primary_parallel_count=(1, 2), secondary_parallel_count=(1, 2),
        material=steel,
    )
    result = optimize_transformer(spec, space, population=40, generations=8, seed=1)
    print(f"Pareto candidates: {len(result.candidates)}")
    if result.candidates:
        print(result.dataframe.head(10).to_string(index=False))
    else:
        raise RuntimeError("No feasible candidate; expand the illustrative search space")


if __name__ == "__main__":
    main()
