from typing import Tuple

from .ephemera import AnalysisTarget, PatternFlavor


class AnalysisEngine:
    def __init__(self):
        self.peak = 0.0
        self.rms = 0.0
        self.f0 = 0.0
        self.is_voiced = False
        self.is_onset = False
        self.centroid = 0.0
        self.flatness = 0.0
        self.rolloff = 0.0

    def intake(
        self,
        *,
        peak: float,
        rms: float,
        f0: float,
        is_voiced: bool,
        is_onset: bool,
        centroid: float,
        flatness: float,
        rolloff: float,
    ):
        self.peak = peak
        self.rms = rms
        self.f0 = f0
        self.is_voiced = is_voiced
        self.is_onset = is_onset
        self.centroid = centroid
        self.flatness = flatness
        self.rolloff = rolloff

    def emit(self) -> Tuple[AnalysisTarget, float, float]:
        analysis_target = AnalysisTarget(
            pattern_flavor=PatternFlavor.BASIC,
            peak=self.peak,
            rms=self.rms,
            f0=self.f0,
            is_voiced=self.is_voiced,
            is_onset=self.is_onset,
            centroid=self.centroid,
            flatness=self.flatness,
            rolloff=self.rolloff,
            k=25,
        )
        min_sleep, max_sleep = 0.0, 1.0
        return analysis_target, min_sleep, max_sleep
