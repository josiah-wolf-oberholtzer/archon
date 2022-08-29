import random
from typing import List

from supriya.patterns import ChoicePattern, EventPattern, Pattern, RandomPattern
from supriya.providers import BufferProxy

from .analysis import AnalysisTarget, PatternFlavor
from .synthdefs import playback


class PatternFactory:
    def emit(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy]
    ) -> Pattern:
        if not buffers:
            raise ValueError
        return {PatternFlavor.BASIC: self.emit_basic_pattern}[
            analysis_target.pattern_flavor
        ](analysis_target, buffers)

    def emit_basic_pattern(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy]
    ) -> Pattern:
        return EventPattern(
            synthdef=playback,
            buffer_id=ChoicePattern(
                sequence=buffers,
                forbid_repetitions=True,
                iterations=random.randint(5, 25),
            ),
            delta=RandomPattern(0.0, 0.25),
            duration=0.0,
            gain=RandomPattern(-24, 0),
            panning=RandomPattern(-1.0, 1.0),
            # transposition=RandomPattern(-3.0, 3.0),
        )
