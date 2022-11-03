import dataclasses
from pathlib import Path
from typing import List, Optional


@dataclasses.dataclass
class ArchonConfig:
    analysis_path: Path
    history_size: int = 10
    input_bus: int = 8
    input_count: int = 8
    input_device: Optional[str] = None
    mfcc_count: int = 13
    output_bus: int = 0
    output_count: int = 8
    output_device: Optional[str] = None
    partition_hop_in_ms: float = 500.0
    partition_sizes_in_ms: List[float] = dataclasses.field(default_factory=list)
    pitch_detection_max_frequency: float = 3000.0
    pitch_detection_min_frequency: float = 60.0
    silence_threshold_db: float = -60.0
    use_mfcc: bool = True
    use_pitch: bool = True
    use_spectral: bool = True

    @property
    def root_path(self) -> Path:
        return self.analysis_path.parent
