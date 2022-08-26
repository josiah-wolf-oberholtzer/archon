import dataclasses
import json
import logging
from pathlib import Path
from typing import List, Tuple

import numpy
from scipy.spatial import KDTree

from .config import ArchonConfig
from .ephemera import AnalysisTarget
from .utils import timer

logger = logging.getLogger(__name__)


@dataclasses.dataclass(eq=True, frozen=True)
class Entry:
    path: Path
    starting_frame: int
    frame_count: int
    digest: str


@dataclasses.dataclass
class Range:
    minimum: float
    mean: float
    maximum: float


@dataclasses.dataclass
class RangeSet:
    centroid: Range
    f0: Range
    flatness: Range
    rms: Range
    rolloff: Range

    def scale(self, value: float, range_: Range) -> float:
        return (value - range_.minimum) / (range_.maximum - range_.minimum)

    def transform(self, *, centroid, f0, flatness, is_voiced, rms, rolloff):
        return (
            self.scale(f0, self.f0) if is_voiced else -1.0,
            self.scale(centroid, self.centroid),
            self.scale(flatness, self.flatness),
            self.scale(rms, self.rms),
            self.scale(rolloff, self.rolloff),
        )


@dataclasses.dataclass
class Database:
    config: ArchonConfig
    entries: List[Entry]
    kdtree: KDTree
    range_set: RangeSet

    @classmethod
    def build_point(
        cls,
        range_set: RangeSet,
        use_pitch: bool,
        use_spectral: bool,
        use_mfcc: bool,
        centroid: float,
        f0: float,
        flatness: float,
        is_voiced: bool,
        mfcc: List[float],
        rms: float,
        rolloff: float,
    ):
        (
            _,
            scaled_centroid,
            scaled_flatness,
            scaled_rms,
            scaled_rolloff,
        ) = range_set.transform(
            centroid=centroid,
            f0=f0,
            flatness=flatness,
            is_voiced=is_voiced,
            rms=rms,
            rolloff=rolloff,
        )
        point = []
        if use_pitch:
            point.append(f0 if is_voiced else -1.0)
        if use_spectral:
            point.extend([scaled_centroid, scaled_flatness, scaled_rms, scaled_rolloff])
        if use_mfcc:
            point.extend(mfcc)
        return tuple(point)

    @classmethod
    def new(cls, config: ArchonConfig) -> "Database":
        logger.info(f"Loading database from {config.analysis_path} ...")
        with timer() as t:
            analysis = json.loads(config.analysis_path.read_text())
            range_set = RangeSet(
                centroid=Range(**analysis["statistics"]["centroid"]),
                f0=Range(**analysis["statistics"]["f0"]),
                flatness=Range(**analysis["statistics"]["flatness"]),
                rms=Range(**analysis["statistics"]["rms"]),
                rolloff=Range(**analysis["statistics"]["rolloff"]),
            )
            entries = []
            points: List[Tuple[float, ...]] = []
            for partition in analysis["partitions"]:
                entries.append(
                    Entry(
                        path=Path(partition["path"]),
                        starting_frame=partition["start_frame"],
                        frame_count=partition["frame_count"],
                        digest=partition["digest"],
                    )
                )
                points.append(
                    cls.build_point(
                        range_set=range_set,
                        use_pitch=config.use_pitch,
                        use_spectral=config.use_spectral,
                        use_mfcc=config.use_mfcc,
                        centroid=partition["centroid"],
                        f0=partition["f0"],
                        flatness=partition["flatness"],
                        is_voiced=partition["is_voiced"],
                        mfcc=partition["mfcc"],
                        rms=partition["rms"],
                        rolloff=partition["rolloff"],
                    )
                )
            database = cls(
                config=config,
                entries=entries,
                kdtree=KDTree(numpy.asarray(points, dtype=numpy.float32)),
                range_set=range_set,
            )
            logger.info(
                f"... Loaded {len(points)} points from {config.analysis_path} ",
                f"in {t():.4f} seconds",
            )
        return database

    def query(
        self,
        *,
        centroid: float,
        f0: float,
        flatness: float,
        is_voiced: bool,
        mfcc: List[float],
        rms: float,
        rolloff: float,
        k: int = 25,
    ) -> List[Tuple[Entry, float]]:
        point = self.build_point(
            range_set=self.range_set,
            use_pitch=self.config.use_pitch,
            use_spectral=self.config.use_spectral,
            use_mfcc=self.config.use_mfcc,
            centroid=centroid,
            f0=f0,
            flatness=flatness,
            is_voiced=is_voiced,
            mfcc=mfcc,
            rms=rms,
            rolloff=rolloff,
        )
        logger.info(f"Querying point: {point}")
        with timer() as t:
            distances, indices = self.kdtree.query(point, k=k)
            logger.info(f"... Queried in {t():.4f} seconds")
        logger.info(f"Distances: {[round(x, 3) for x in distances]}")
        return [
            (self.entries[indices[i]], round(distances[i], 6))
            for i in range(len(distances))
        ]

    def query_analysis_target(
        self, analysis_target: AnalysisTarget, k: int = 25
    ) -> List[Entry]:
        return [
            entry
            for entry, distance in self.query(
                centroid=analysis_target.centroid,
                f0=analysis_target.f0,
                flatness=analysis_target.flatness,
                is_voiced=analysis_target.is_voiced,
                mfcc=analysis_target.mfcc,
                rms=analysis_target.rms,
                rolloff=analysis_target.rolloff,
                k=analysis_target.k,
            )
        ]
