import dataclasses
import hashlib
import json
import logging
import math
import sys
from pathlib import Path
from typing import Dict, List

import librosa
import numpy

from . import config
from .utils import cd, timer

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Analysis:
    path: Path
    sample_count: int
    sample_rate: int
    frame_length: int  # frame here is a spectral frame
    frame_count: int  # frame here is a spectral frame
    hop_length: int
    window_length: int
    centroid: numpy.ndarray
    f0: numpy.ndarray
    flatness: numpy.ndarray
    is_voiced: numpy.ndarray
    rms: numpy.ndarray
    rolloff: numpy.ndarray


@dataclasses.dataclass
class Partition:
    path: str
    digest: str
    start_frame: int  # frame here is a sample frame
    frame_count: int  # frame here is a sample fram
    centroid: float
    f0: float
    flatness: float
    is_voiced: bool
    rms: float
    rolloff: float


def analyze(
    path: Path, frame_length: int = 4096, hop_length: int = 512, window_length=2048
) -> Analysis:
    logger.info(f"Analyzing {path} ...")
    with timer() as t:
        y, sr = librosa.load(path, sr=None, mono=True)
        logger.info(f"... Loaded {path} in {t():.4f} seconds")
    adjusted_frame_length = frame_length * (sr // 44100)
    adjusted_hop_length = hop_length * (sr // 44100)
    adjusted_window_length = window_length * (sr // 44100)
    with timer() as t:
        stft = librosa.stft(
            y=y,
            n_fft=adjusted_frame_length,
            hop_length=adjusted_hop_length,
            win_length=adjusted_window_length,
        )
        S, _ = librosa.magphase(stft)
        centroid = librosa.feature.spectral_centroid(S=S, sr=sr)
        flatness = librosa.feature.spectral_flatness(S=S)
        rms = librosa.power_to_db(
            librosa.feature.rms(S=S, frame_length=adjusted_frame_length)
        )
        rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr)
        logger.info(f"... Analyzed {path} STFT in {t():.4f} seconds")
    with timer() as t:
        f0, is_voiced, _ = librosa.pyin(
            y=y,
            fmin=config.PITCH_DETECTION_MIN_FREQUENCY,
            fmax=config.PITCH_DETECTION_MAX_FREQUENCY,
            sr=sr,
            frame_length=adjusted_frame_length,
            hop_length=adjusted_hop_length,
        )
        logger.info(f"... Analyzed {path} PYIN in {t():.4f} seconds")
    analysis = Analysis(
        centroid=numpy.squeeze(centroid),
        f0=numpy.squeeze(f0),
        flatness=numpy.squeeze(flatness),
        frame_count=f0.shape[0],
        frame_length=adjusted_frame_length,
        hop_length=adjusted_hop_length,
        is_voiced=numpy.squeeze(is_voiced),
        path=path,
        rms=numpy.squeeze(rms),
        rolloff=numpy.squeeze(rolloff),
        sample_count=y.shape[0],
        sample_rate=sr,
        window_length=adjusted_window_length,
    )
    return analysis


def partition(
    analysis: Analysis, partition_size_in_ms=1000, partition_hop_in_ms=500
) -> List[Partition]:
    logger.info(f"Partitioning {analysis.path} ...")
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
            centroid = analysis.centroid[start_index:stop_index]
            is_voiced = analysis.is_voiced[start_index:stop_index]
            f0 = analysis.f0[start_index:stop_index]
            flatness = analysis.flatness[start_index:stop_index]
            rms = analysis.rms[start_index:stop_index]
            rolloff = analysis.rolloff[start_index:stop_index]
            # hash the underlying data
            hasher = hashlib.sha1()
            for array in (centroid, is_voiced, f0, flatness, rms, rolloff):
                hasher.update(array.data)
            digest = hasher.hexdigest()
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
                rms=float(numpy.median(rms)),
                rolloff=float(numpy.median(rolloff)),
            )
            partitions.append(partition)
        logger.info(f"... Partitioned {analysis.path} in {t():.4f} seconds")
    return partitions


def run(input_path: Path, output_path: Path):
    if not input_path.exists() and input_path.is_dir():
        raise ValueError(input_path)
    logger.info(f"Running pipeline on {input_path} ...")
    with timer() as t:
        statistics: Dict[str, List[float]] = {}
        partitions = {}
        for audio_path in input_path.glob("**/*.wav"):
            with cd(input_path):
                analysis = analyze(audio_path.relative_to(input_path))
            for key in ("centroid", "f0", "flatness", "rms", "rolloff"):
                feature = getattr(analysis, key)
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
                if x.rms < config.SILENCE_THRESHOLD_DB:  # Ignore silence
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
        output_path.write_text(json.dumps(data, sort_keys=True, indent=2))
        logger.info(f"... Pipeline finished in {t():.4f} seconds")


def validate(analysis_path: Path):
    logger.info(f"Validating {analysis_path} ...")
    analysis = json.loads(analysis_path.read_text())
    root_path = analysis_path.parent
    missing = False
    for audio_path in sorted(
        set(root_path / x["path"] for x in analysis["partitions"])
    ):
        if audio_path.exists():
            logger.info(f"- {audio_path}: exists!")
        else:
            logger.warning(f"- {audio_path}: missing!")
            missing = True
    if missing:
        sys.exit("Could not locate all audio paths")
