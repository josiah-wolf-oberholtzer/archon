from typing import List, Optional, Tuple

import numpy

from .config import ArchonConfig
from .ephemera import AnalysisTarget, PatternFlavor


class AnalysisEngine:
    def __init__(self, config: ArchonConfig):
        self.config = config
        self.index = 0
        self.peak: numpy.ndarray = numpy.ndarray(config.history_size)
        self.rms: numpy.ndarray = numpy.ndarray(config.history_size)
        self.f0: numpy.ndarray = numpy.ndarray(config.history_size)
        self.is_voiced: numpy.ndarray = numpy.ndarray(
            config.history_size, dtype=numpy.bool_
        )
        self.is_onset: numpy.ndarray = numpy.ndarray(
            config.history_size, dtype=numpy.bool_
        )
        self.centroid: numpy.ndarray = numpy.ndarray(config.history_size)
        self.flatness: numpy.ndarray = numpy.ndarray(config.history_size)
        self.rolloff: numpy.ndarray = numpy.ndarray(config.history_size)
        self.mfcc: numpy.ndarray = numpy.ndarray(
            (config.history_size, config.mfcc_count)
        )

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
        mfcc: List[float],
    ):
        index = self.index % self.config.history_size
        self.peak[index] = peak
        self.rms[index] = rms
        self.f0[index] = f0
        self.is_voiced[index] = is_voiced
        self.is_onset[index] = is_onset
        self.centroid[index] = centroid
        self.flatness[index] = flatness
        self.rolloff[index] = rolloff
        self.mfcc[index] = mfcc
        self.index += 1

    def emit(self) -> Tuple[Optional[AnalysisTarget], float, float]:
        min_sleep, max_sleep = 0.0, 1.0
        if self.index < self.config.history_size:
            return None, min_sleep, max_sleep
        analysis_target = AnalysisTarget(
            pattern_flavor=PatternFlavor.BASIC,
            peak=float(self.peak.mean()),
            rms=float(self.rms.mean()),
            f0=float(self.f0.mean()),
            is_voiced=bool(self.is_voiced.mean()),
            is_onset=bool(self.is_onset.mean()),
            centroid=float(self.centroid.mean()),
            flatness=float(self.flatness.mean()),
            rolloff=float(self.rolloff.mean()),
            mfcc=self.mfcc.mean(axis=0).tolist(),
            k=25,
        )
        return analysis_target, min_sleep, max_sleep
