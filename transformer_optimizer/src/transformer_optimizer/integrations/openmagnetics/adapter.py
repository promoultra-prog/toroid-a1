class PyOpenMagneticsAdapter:
    """Lazy optional binding. Called only on selected candidates after NSGA-II."""

    def calculate(self, mas: dict, temperature: float) -> dict:
        try:
            import PyOpenMagnetics as mkf
        except ImportError as exc:
            raise RuntimeError("PyOpenMagnetics is unavailable on this Python platform") from exc
        completed = mkf.mas_autocomplete(mas, {})
        inputs = mkf.process_inputs(completed["inputs"])
        magnetic = completed["magnetic"]
        core, coil = magnetic["core"], magnetic["coil"]
        operating_point = inputs["operatingPoints"][0]
        models = {"coreLosses": "STEINMETZ", "reluctance": "ZHANG"}
        core_result = mkf.calculate_core_losses(core, coil, inputs, models)
        winding_result = mkf.calculate_winding_losses(magnetic, operating_point, temperature)
        inductance_result = mkf.calculate_inductance_from_number_turns_and_gapping(
            core, coil, operating_point, models)
        if isinstance(inductance_result, dict):
            inductance = inductance_result["magnetizingInductance"]
            if isinstance(inductance, dict):
                inductance = inductance["magnetizingInductance"]
        else:
            inductance = inductance_result
        return {"core_loss_w": core_result["coreLosses"],
                "winding_loss_w": winding_result["windingLosses"],
                "inductance_h": float(inductance),
                "core_temperature_c": core_result.get("maximumCoreTemperature")}
