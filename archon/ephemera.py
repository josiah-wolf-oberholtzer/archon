import dataclasses
from enum import Enum


class PatternFlavor(Enum):
    BASIC = "b"


@dataclasses.dataclass
class AnalysisTarget:
    pattern_flavor: PatternFlavor
