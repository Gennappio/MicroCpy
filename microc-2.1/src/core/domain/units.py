from dataclasses import dataclass

@dataclass(frozen=True)
class Concentration:
    value: float  # mM

@dataclass(frozen=True)
class Diffusivity:
    value: float  # m^2/s
