def plot_pareto(result):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    scatter = ax.scatter([r.total_mass for r in result.evaluations],
                         [r.total_loss for r in result.evaluations],
                         c=[r.regulation_percent for r in result.evaluations])
    ax.set(xlabel="Total mass (kg)", ylabel="Total loss (W)")
    fig.colorbar(scatter, ax=ax, label="Regulation (%)")
    return fig
