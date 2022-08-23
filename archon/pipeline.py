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
from typing import Dict, List, Optional

import librosa
import numpy
from joblib import Parallel, delayed
from supriya import Session, synthdef
from supriya.ugens import FFT, MFCC, BufFrames, BufWr, In, Line, LocalBuf

from . import config
from .utils import timer

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Analysis:
    """
    An analysis of a single file.
    """

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
    mfcc: numpy.ndarray
    rms: numpy.ndarray
    rolloff: numpy.ndarray


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


def analyze(
    path: Path,
    root_path: Path,
    path_index: int = 1,
    path_count: int = 1,
    setup_logging: bool = False,
    frame_length: int = 4096,
    hop_length: int = 512,
    window_length=2048,
) -> Optional[Analysis]:
    """
    Analyze a single file.
    """
    if setup_logging:
        logging.basicConfig()
        logging.getLogger("archon").setLevel(logging.INFO)
    relative_path = path.relative_to(root_path)
    logger.info(f"[{path_index: >3}/{path_count: >3}] Analyzing {relative_path} ...")
    sr = librosa.get_samplerate(path)
    adjusted_frame_length = frame_length * (sr // 44100)
    adjusted_hop_length = hop_length * (sr // 44100)
    adjusted_window_length = window_length * (sr // 44100)
    block_length = 1024
    try:
        block_count = len(
            [
                None
                for _ in librosa.stream(
                    path,
                    mono=True,
                    frame_length=adjusted_frame_length,
                    hop_length=adjusted_hop_length,
                    block_length=block_length,
                )
            ]
        )
        analyses: Dict[str, List[numpy.ndarray]] = {
            "centroid": [],
            "f0": [],
            "flatness": [],
            "is_voiced": [],
            "rms": [],
            "rolloff": [],
        }
        with timer() as t:
            for block_index, y in enumerate(
                librosa.stream(
                    path,
                    mono=True,
                    frame_length=adjusted_frame_length,
                    hop_length=adjusted_hop_length,
                    block_length=block_length,
                ),
                1,
            ):
                with timer() as tb:
                    stft = librosa.stft(
                        y=y,
                        n_fft=adjusted_frame_length,
                        hop_length=adjusted_hop_length,
                        win_length=adjusted_window_length,
                    )
                    S, _ = librosa.magphase(stft)
                    analyses["centroid"].append(
                        numpy.squeeze(librosa.feature.spectral_centroid(S=S, sr=sr))
                    )
                    analyses["flatness"].append(
                        numpy.squeeze(librosa.feature.spectral_flatness(S=S))
                    )
                    analyses["rms"].append(
                        numpy.squeeze(
                            librosa.power_to_db(
                                librosa.feature.rms(
                                    S=S, frame_length=adjusted_frame_length
                                )
                            )
                        )
                    )
                    analyses["rolloff"].append(
                        numpy.squeeze(librosa.feature.spectral_rolloff(S=S, sr=sr))
                    )
                    f0, is_voiced, _ = librosa.pyin(
                        y=y,
                        fmin=config.PITCH_DETECTION_MIN_FREQUENCY,
                        fmax=config.PITCH_DETECTION_MAX_FREQUENCY,
                        sr=sr,
                        frame_length=adjusted_frame_length,
                        hop_length=adjusted_hop_length,
                    )
                    analyses["f0"].append(numpy.squeeze(f0))
                    analyses["is_voiced"].append(numpy.squeeze(is_voiced))
                    logger.info(
                        f"[{path_index: >3}/{path_count: >3}] "
                        f"[{block_index: >3}/{block_count: >3}] "
                        f"Analyzed {relative_path} in {tb():.3f} seconds"
                    )
            with timer() as tsc:
                mfcc = analyze_mfcc(path, hop_length=adjusted_hop_length)
                logger.info(
                    f"[{path_index: >3}/{path_count: >3}] ... "
                    f"Analyzed {relative_path} MFCC in {tsc():.3f} seconds"
                )
            logger.info(
                f"[{path_index: >3}/{path_count: >3}] ... "
                f"Finished analyzing {relative_path} in {t():.3f} total seconds"
            )
        centroid = numpy.concatenate(analyses["centroid"])
        f0 = numpy.concatenate(analyses["f0"])
        flatness = numpy.concatenate(analyses["flatness"])
        is_voiced = numpy.concatenate(analyses["is_voiced"])
        rms = numpy.concatenate(analyses["rms"])
        rolloff = numpy.concatenate(analyses["rolloff"])
        analysis = Analysis(
            centroid=centroid,
            f0=f0,
            flatness=flatness,
            frame_count=f0.shape[0],
            frame_length=adjusted_frame_length,
            hop_length=adjusted_hop_length,
            is_voiced=is_voiced,
            mfcc=mfcc,
            path=relative_path,
            rms=rms,
            rolloff=rolloff,
            sample_count=y.shape[0],
            sample_rate=sr,
            window_length=adjusted_window_length,
        )
        return analysis
    except Exception:
        logger.warning(f"[{path_index: >3}/{path_count: >3}] {relative_path} failed!")
        traceback.print_exc()
        return None


def analyze_mfcc(path: Path, hop_length=512) -> numpy.ndarray:
    @synthdef()
    def mfcc_synthdef(in_, output_buffer_id=0, duration=0):
        source = In.ar(bus=in_)
        chain = FFT(LocalBuf(2048), source)
        mfcc = MFCC.kr(pv_chain=chain, coeff_count=13)
        phase = Line.ar(
            start=0,
            stop=BufFrames.kr(output_buffer_id),
            duration=duration,
            done_action=2,
        )
        BufWr.kr(buffer_id=output_buffer_id, phase=phase, source=mfcc)

    duration = librosa.get_duration(filename=path)
    sample_rate = librosa.get_samplerate(path)
    stream = librosa.stream(path, block_length=1, frame_length=1024, hop_length=256)
    if len(shape := next(stream).shape) == 1:
        channel_count = 1
    else:
        channel_count = shape[0]

    frame_count = int(duration * sample_rate / hop_length)

    with tempfile.TemporaryDirectory() as temp_directory:
        output_path = Path(temp_directory) / "mfcc.wav"
        session = Session(input_=path, input_bus_channel_count=channel_count)
        with session.at(0):
            output_buffer = session.add_buffer(
                channel_count=13, frame_count=frame_count
            )
            session.add_synth(
                synthdef=mfcc_synthdef,
                in_=session.audio_input_bus_group,
                output_buffer_id=output_buffer,
                duration=duration,
            )
        with session.at(duration):
            output_buffer.write(
                file_path=output_path, header_format="WAV", sample_format="FLOAT"
            )
        session.render(output_file_path="/dev/null", sample_rate=sample_rate)
        y, _ = librosa.load(
            output_path, sr=librosa.get_samplerate(output_path), mono=False
        )
    return y


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
            centroid = analysis.centroid[start_index:stop_index]
            is_voiced = analysis.is_voiced[start_index:stop_index]
            f0 = analysis.f0[start_index:stop_index]
            flatness = analysis.flatness[start_index:stop_index]
            mfcc = analysis.mfcc.T[start_index:stop_index]
            rms = analysis.rms[start_index:stop_index]
            rolloff = analysis.rolloff[start_index:stop_index]
            # hash the underlying data
            hasher = hashlib.sha1()
            for array in (centroid, is_voiced, f0, flatness, mfcc, rms, rolloff):
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
                mfcc=numpy.median(mfcc, axis=0).tolist(),
                rms=float(numpy.median(rms)),
                rolloff=float(numpy.median(rolloff)),
            )
            partitions.append(partition)
        logger.info(f"Partitioned {analysis.path} in {t():.4f} seconds")
    return partitions


def run(input_path: Path, output_path: Path):
    """
    Run the pipeline.
    """
    if not input_path.exists() and input_path.is_dir():
        raise ValueError(input_path)
    logger.info(f"Running pipeline on {input_path} ...")
    with timer() as t:
        all_paths = sorted(input_path.glob("**/*.wav"))
        path_count = len(all_paths)
        total_source_time = sum(
            librosa.get_duration(filename=path) for path in all_paths
        )

        job_count = (os.cpu_count() or 4) // 2
        analyses = [
            x
            for x in Parallel(n_jobs=job_count)(
                delayed(analyze)(
                    audio_path,
                    input_path,
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
        logger.info(
            f"Pipeline finished analyzing {total_source_time:.3f} seconds of audio "
            f"in {t():.3f} seconds"
        )


def validate(analysis_path: Path):
    """
    Validate an analysis file.
    """
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
