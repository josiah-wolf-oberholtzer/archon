import dataclasses
from enum import Enum


class PatternFlavor(Enum):
    BASIC = "b"


@dataclasses.dataclass
class AnalysisTarget:
    pattern_flavor: PatternFlavor
    peak: float
    rms: float
    f0: float
    is_voiced: bool
    is_onset: bool
    centroid: float
    flatness: float
    rolloff: float
    k: int
