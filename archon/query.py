import dataclasses
import json
from pathlib import Path
from typing import List, Tuple

import numpy
from scipy.spatial import KDTree


@dataclasses.dataclass
class Entry:
    path: Path
    start_frame: int
    frame_count: int


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
            self.scale(centroid, self.centroid),
            self.scale(f0, self.f0) if is_voiced else -1.0,
            self.scale(flatness, self.flatness),
            self.scale(rms, self.rms),
            self.scale(rolloff, self.rolloff),
        )


@dataclasses.dataclass
class Database:
    entries: List[Entry]
    kdtree: KDTree
    range_set: RangeSet

    def new(cls, analysis_path: Path) -> "Database":
        analysis = json.loads(analysis_path.read_text())
        range_set = RangeSet(
            centroid=Range(**analysis["statistics"]["centroid"]),
            f0=Range(**analysis["statistics"]["f0"]),
            flatness=Range(**analysis["statistics"]["flatness"]),
            rms=Range(**analysis["statistics"]["rms"]),
            rolloff=Range(**analysis["statistics"]["rolloff"]),
        )
        entries = []
        points = []
        for partition in analysis["partitions"]:
            entries.append(
                Entry(
                    path=analysis_path.parent / Path(partition["path"]),
                    start_frame=partition["start_frame"],
                    frame_count=partition["frame_count"],
                )
            )
            points.append(
                range_set.transform(
                    centroid=partition["centroid"],
                    f0=partition["f0"],
                    flatness=partition["flatness"],
                    is_voiced=partition["is_voiced"],
                    rms=partition["rms"],
                    rolloff=partition["rolloff"],
                )
            )
        database = Database(
            kdtree=KDTree(numpy.ndarray(points, dtype=numpy.float32)),
            entries=entries,
            range_set=range_set,
        )
        return database

    def query(
        self,
        *,
        centroid: float,
        f0: float,
        flatness: float,
        is_voiced: bool,
        rms: float,
        rolloff: float,
        k: int = 25,
    ) -> List[Tuple[Entry, float]]:
        point = self.range_set.transform(
            centroid=centroid,
            f0=f0,
            flatness=flatness,
            is_voiced=is_voiced,
            rms=rms,
            rolloff=rolloff,
        )
        distances, indices = self.kdtree.query(point, k=k)
        return [(self.entries[indices[i]], distances[i]) for i in range(len(distances))]
