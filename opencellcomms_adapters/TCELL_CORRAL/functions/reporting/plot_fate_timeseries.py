"""Plot the committed Treg / Th1 / Th17 time series at the end of the run.

Post-processing world behaviour: charts the per-step committed-fate counts that
``record_fate_counts`` recorded, so the differentiation trajectory (and how a
perturbation shifts it) is visible without opening the raw series.
"""
from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext

_KEYS = ["Treg_committed", "Th1_committed", "Th17_committed"]


@register_function(
    display_name="Plot Fate Timeseries",
    description="Plot committed Treg/Th1/Th17 counts over the run to the plots directory.",
    category="FINALIZATION",
    parameters=[],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    compatible_kernels=["biophysics"],
)
def plot_fate_timeseries(env: BiologicalContext, **kwargs) -> bool:
    if not any(env.records.get(k) for k in _KEYS):
        print("[TCELL_CORRAL] no fate series recorded; nothing to plot")
        return True
    try:
        path = env.plot_records(_KEYS, "tcell_fate_timeseries.png")
        print(f"[TCELL_CORRAL] wrote fate timeseries -> {path}")
    except Exception as e:
        print(f"[TCELL_CORRAL] fate plot failed: {e}")
    return True
