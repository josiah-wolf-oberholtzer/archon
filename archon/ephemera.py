import dataclasses
from enum import Enum
from typing import List


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
    mfccs: List[float]
    k: int
