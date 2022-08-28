import dataclasses
import hashlib
import json
import logging
import math
import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import librosa
import numpy
from joblib import Parallel, delayed
from supriya import Session

from .config import ArchonConfig
from .synthdefs import build_offline_analysis_synthdef
from .utils import timer

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Analysis:
    """
    An analysis of a single file.
    """

    path: Path
    array: numpy.ndarray
    frame_length: int  # frame here is a spectral frame
    hop_length: int
    sample_rate: int

    @property
    def features(self):
        return {
            "centroid": self.array[5],
            "f0": self.array[2],
            "flatness": self.array[6],
            "is_onset": self.array[4],
            "is_voiced": self.array[3],
            "mfcc": self.array[8:],
            "peak": self.array[0],
            "rms": self.array[1],
            "rolloff": self.array[7],
        }

    @property
    def frame_count(self):
        return self.array.shape[-1]


@dataclasses.dataclass
class Partition:
    """
    Analysis of a subsegment of a single file.

    Datapoints are medians.
    """

    path: str
    digest: str
    start_frame: int  # frame here is a sample frame
    frame_count: int  # frame here is a sample fram
    centroid: float
    f0: float
    flatness: float
    is_voiced: bool
    mfcc: List[float]
    rms: float
    rolloff: float


def describe_audio(path: Path) -> Tuple[int, float, int]:
    sample_rate = librosa.get_samplerate(path)
    duration = librosa.get_duration(filename=path)
    stream = librosa.stream(
        path, block_length=1, frame_length=1024, hop_length=256, mono=False
    )
    if len(shape := next(stream).shape) == 1:
        channel_count = 1
    else:
        channel_count = shape[0]
    return sample_rate, duration, channel_count


def analyze(
    config: ArchonConfig,
    path: Path,
    path_index: int = 1,
    path_count: int = 1,
    setup_logging: bool = False,
    frame_length: int = 2048,
    hop_ratio: float = 0.5,
) -> Optional[Analysis]:
    """
    Analyze a single file.
    """
    if setup_logging:
        logging.basicConfig()
        logging.getLogger("archon").setLevel(logging.INFO)
    relative_path = path.relative_to(config.root_path)
    logger.info(f"[{path_index: >3}/{path_count: >3}] Analyzing {relative_path} ...")
    sample_rate, duration, _ = describe_audio(path)
    logger.info
    try:
        with timer() as t:
            array, adjusted_frame_length = analyze_via_nrt(
                config=config,
                path=config.root_path / path,
                frame_length=frame_length,
                hop_ratio=hop_ratio,
            )
            # What if Analysis just has a reference to the original ndarray
            # and provides properties to index the correct bits
            analysis = Analysis(
                path=relative_path,
                array=array.copy(order="F"),
                frame_length=adjusted_frame_length,
                hop_length=int(adjusted_frame_length * hop_ratio),
                sample_rate=sample_rate,
            )
            logger.info(
                f"[{path_index: >3}/{path_count: >3}] ... "
                f"Analyzed {relative_path} in {t():.3f} seconds"
            )
        return analysis
    except Exception:
        logger.warning(f"[{path_index: >3}/{path_count: >3}] {relative_path} failed!")
        traceback.print_exc()
        return None


def analyze_via_nrt(
    config: ArchonConfig,
    path: Path,
    *,
    frame_length: int = 2048,
    hop_ratio: float = 0.5,
) -> Tuple[numpy.ndarray, int]:
    sample_rate, duration, channel_count = describe_audio(path)
    adjusted_frame_length = frame_length * (sample_rate // 44100)
    hop_length = adjusted_frame_length * hop_ratio
    frame_count = int(duration * sample_rate / hop_length)
    analysis_duration = frame_count * hop_length / sample_rate
    logger.debug(
        f"sr={sample_rate} d={duration} c={channel_count} "
        f"fl={adjusted_frame_length} hl={hop_length} fc={frame_count}"
    )
    synthdef = build_offline_analysis_synthdef(
        frame_length=adjusted_frame_length,
        hop_ratio=hop_ratio,
        pitch_detection_max_frequency=config.pitch_detection_max_frequency,
        pitch_detection_min_frequency=config.pitch_detection_min_frequency,
    )
    with tempfile.TemporaryDirectory() as temp_directory:
        logger.info(f"Rendering analysis in {temp_directory}")
        output_path = Path(temp_directory) / "analysis.wav"
        session = Session(
            input_=path.resolve(),
            input_bus_channel_count=channel_count,
            output_bus_channel_count=1,  # can't currently just write to /dev/null
        )
        with session.at(0):
            output_buffer = session.add_buffer(
                channel_count=42 + 8, frame_count=frame_count
            )
            session.add_synth(
                synthdef=synthdef,
                in_=session.audio_input_bus_group,
                output_buffer_id=output_buffer,
                duration=analysis_duration,
            )
        with session.at(analysis_duration):
            output_buffer.write(
                file_path=output_path, header_format="WAV", sample_format="FLOAT"
            )
        session.render(render_directory_path=temp_directory, sample_rate=sample_rate)
        analysis, _ = librosa.load(
            output_path, sr=librosa.get_samplerate(output_path), mono=False
        )
    return analysis, adjusted_frame_length


def partition(
    analysis: Analysis, partition_size_in_ms=1000, partition_hop_in_ms=500
) -> List[Partition]:
    """
    Partition an analysis.
    """
    with timer() as t:
        hop_length_in_ms = float(analysis.hop_length) / analysis.sample_rate * 1000
        indices_per_partition = math.ceil(partition_size_in_ms / hop_length_in_ms)
        indices_per_partition_hop = math.ceil(partition_hop_in_ms / hop_length_in_ms)
        partitions = []
        for start_index in range(0, analysis.frame_count, indices_per_partition_hop):
            stop_index = start_index + indices_per_partition
            if stop_index > analysis.frame_count:  # bail on final incomplete partition
                break
            # grab subsets
            features = analysis.features
            centroid = features["centroid"][start_index:stop_index]
            is_voiced = features["is_voiced"][start_index:stop_index]
            f0 = features["f0"][start_index:stop_index]
            flatness = features["flatness"][start_index:stop_index]
            mfcc = features["mfcc"].T[start_index:stop_index]
            rms = features["rms"][start_index:stop_index]
            rolloff = features["rolloff"][start_index:stop_index]
            # hash the underlying data
            hasher = hashlib.sha1()
            hasher.update(analysis.array[start_index:stop_index].copy().data)
            digest = hasher.hexdigest()
            # compute f0 for pitched partitions only
            computed_f0 = -1.0
            if computed_is_voiced := numpy.median(is_voiced):
                computed_f0 = float(
                    librosa.hz_to_midi(numpy.median(f0[~numpy.isnan(f0)]))
                )
            # yield the partition
            partition = Partition(
                path=str(analysis.path),
                digest=digest,
                start_frame=start_index * analysis.hop_length,
                frame_count=(stop_index - start_index) * analysis.hop_length,
                centroid=float(numpy.median(centroid)),
                f0=computed_f0,
                flatness=float(numpy.median(flatness)),
                is_voiced=bool(computed_is_voiced),
                mfcc=numpy.median(mfcc, axis=0).tolist(),
                rms=float(numpy.median(rms)),
                rolloff=float(numpy.median(rolloff)),
            )
            partitions.append(partition)
        logger.info(f"Partitioned {analysis.path} in {t():.4f} seconds")
    return partitions


def run(config: ArchonConfig):
    """
    Run the pipeline.
    """
    if not config.root_path.exists():
        raise ValueError(config.analysis_path)
    logger.info(f"Running pipeline on {config.root_path} ...")
    with timer() as t:
        all_paths = sorted(config.root_path.glob("**/*.wav"))
        path_count = len(all_paths)
        total_source_time = sum(
            librosa.get_duration(filename=path) for path in all_paths
        )

        job_count = (os.cpu_count() or 4) // 2
        analyses = [
            x
            for x in Parallel(n_jobs=job_count)(
                delayed(analyze)(
                    config,
                    audio_path,
                    path_index=path_index,
                    path_count=path_count,
                    setup_logging=True,
                )
                for path_index, audio_path in enumerate(all_paths, 1)
            )
            if x is not None
        ]

        statistics: Dict[str, List[float]] = {}
        partitions = {}
        for analysis in analyses:

            for key in ("centroid", "f0", "flatness", "rms", "rolloff"):
                feature = analysis.features[key]
                if key == "f0":
                    feature = librosa.hz_to_midi(feature[~numpy.isnan(feature)])
                minimum = float(numpy.min(feature))
                maximum = float(numpy.max(feature))
                sum_ = float(numpy.sum(feature))
                if key not in statistics:
                    statistics[key] = [minimum, maximum, sum_, feature.shape[0]]
                else:
                    if minimum < statistics[key][0]:
                        statistics[key][0] = minimum
                    if maximum > statistics[key][1]:
                        statistics[key][1] = maximum
                    statistics[key][2] += sum_
                    statistics[key][3] += feature.shape[0]

            for x in partition(analysis):
                if x.rms < config.silence_threshold_db:  # Ignore silence
                    continue
                partitions[x.digest] = x  # Use the hash to ignore duplicates

        data = {
            "partitions": sorted(
                (vars(x) for x in partitions.values()),
                key=lambda x: (x["path"], x["start_frame"]),
            ),
            "statistics": {
                key: {
                    "minimum": value[0],
                    "mean": float(value[2]) / value[3],
                    "maximum": value[1],
                }
                for key, value in statistics.items()
            },
        }
        config.analysis_path.write_text(json.dumps(data, sort_keys=True, indent=2))
        logger.info(
            f"Pipeline finished analyzing {total_source_time:.3f} seconds of audio "
            f"in {t():.3f} seconds"
        )


def validate(config: ArchonConfig):
    """
    Validate an analysis file.
    """
    logger.info(f"Validating {config.analysis_path} ...")
    analysis = json.loads(config.analysis_path.read_text())
    missing = False
    for audio_path in sorted(
        set(config.root_path / x["path"] for x in analysis["partitions"])
    ):
        if audio_path.exists():
            logger.info(f"- {audio_path}: exists!")
        else:
            logger.warning(f"- {audio_path}: missing!")
            missing = True
    if missing:
        sys.exit("Could not locate all audio paths")
