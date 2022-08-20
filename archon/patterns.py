from typing import List

from supriya.patterns import Pattern
from supriya.providers import BufferProxy

from .ephemera import AnalysisTarget, PatternFlavor


class PatternFactory:
    def emit(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy]
    ) -> Pattern:
        return {PatternFlavor.BASIC: self.emit_basic_pattern}[
            analysis_target.pattern_flavor
        ](analysis_target, buffers)

    def emit_basic_pattern(
        self, analysis_target: AnalysisTarget, buffers: List[BufferProxy]
    ) -> Pattern:
        pass
