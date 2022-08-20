from typing import Optional

from supriya import OscMessage

from .ephemera import AnalysisTarget


class AnalysisEngine:
    def handle_analysis_message(self, osc_message: OscMessage):
        return self.intake(
            peak=osc_message.contents[2],
            rms=osc_message.contents[3],
            f0=osc_message.contents[4],
            is_voiced=bool(osc_message.contents[5]),
            is_onset=bool(osc_message.contents[6]),
            centroid=osc_message.contents[7],
            flatness=osc_message.contents[8],
            rolloff=osc_message.contents[9],
        )

    def intake(
        self,
        *peak: float,
        rms: float,
        f0: float,
        is_voiced: bool,
        is_onset: bool,
        centroid: float,
        flatness: float,
        rolloff: float,
    ):
        return None
