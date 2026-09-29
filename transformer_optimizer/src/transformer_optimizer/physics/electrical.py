def full_load_voltage(no_load_voltage: float, current: float, secondary_resistance: float,
                      primary_current: float, primary_resistance: float, turns_ratio: float) -> float:
    # Referred primary copper drop; leakage reactance is unavailable in this MVP.
    return no_load_voltage - current * secondary_resistance - primary_current * primary_resistance * turns_ratio


def regulation_percent(no_load_voltage: float, loaded_voltage: float) -> float:
    return 100 * (no_load_voltage - loaded_voltage) / loaded_voltage if loaded_voltage > 0 else float("inf")
