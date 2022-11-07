import random
from typing import List

from supriya.patterns import ChoicePattern, EventPattern, Pattern, RandomPattern
from supriya.providers import BufferProxy

from .analysis import AnalysisTarget, PatternFlavor
from .synthdefs import granulate, playback, warp


class PatternFactory:
    def emit(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy], out: int = 0
    ) -> Pattern:
        if not buffers:
            raise ValueError
        return {
            PatternFlavor.BASIC: self.emit_basic_pattern,
            PatternFlavor.GRANULATE: self.emit_granulate_pattern,
            PatternFlavor.WARP: self.emit_warp_pattern,
        }[analysis_target.pattern_flavor](analysis_target, buffers, out)

    def emit_basic_pattern(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy], out: int = 0
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
            out=out,
            panning=RandomPattern(-1.0, 1.0),
            # transposition=RandomPattern(-3.0, 3.0),
        )

    def emit_granulate_pattern(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy], out: int = 0
    ) -> Pattern:
        return EventPattern(
            synthdef=granulate,
            buffer_id=ChoicePattern(
                sequence=buffers,
                forbid_repetitions=True,
                iterations=random.randint(1, 3),
            ),
            delta=RandomPattern(0.0, 2.0),
            duration=0.0,
            gain=RandomPattern(-24, 0),
            out=out,
            panning=RandomPattern(-1.0, 1.0),
            time_scaling=RandomPattern(1.0, 4.0),
        )

    def emit_warp_pattern(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy], out: int = 0
    ) -> Pattern:
        return EventPattern(
            synthdef=warp,
            buffer_id=ChoicePattern(
                sequence=buffers,
                forbid_repetitions=True,
                iterations=random.randint(1, 5),
            ),
            delta=RandomPattern(0.0, 5.0),
            duration=0.0,
            gain=RandomPattern(-24, 0),
            highpass_frequency=RandomPattern(20.0, 2000.0),
            out=out,
            overlaps=ChoicePattern(
                [1, 2, 4, 8, 16, 32, 64],
                iterations=None
                # [2, 2, 4, 4, 4, 4, 8, 8, 8, 16, 16], iterations=None
                # [4, 8, 8, 16], iterations=None
            ),
            panning=RandomPattern(-1.0, 1.0),
            start=RandomPattern(0.0, 0.25),
            stop=RandomPattern(0.75, 1.0),
            time_scaling=RandomPattern(1.0, 4.0),
            # transposition=ChoicePattern(sequence=[0, 0, -12], iterations=None),
            transposition=RandomPattern(-12.0, 0.0),
        )
