import dataclasses
from pathlib import Path


@dataclasses.dataclass
class ArchonConfig:
    analysis_path: Path
    history_size: int = 10
    mfcc_count: int = 13
    pitch_detection_max_frequency: float = 3000.0
    pitch_detection_min_frequency: float = 60.0
    silence_threshold_db: float = -60.0
    use_mfcc: bool = True
    use_pitch: bool = True
    use_spectral: bool = True

    @property
    def root_path(self) -> Path:
        return self.analysis_path.parent
