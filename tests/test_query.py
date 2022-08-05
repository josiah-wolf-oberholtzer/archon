import json
from pathlib import Path

from archon.query import Database


def test_Database():
    analysis_path = Path(__file__).parent / "analysis.json"
    analysis = json.loads(analysis_path.read_text())
    database = Database.new(analysis_path)
    partition = analysis["partitions"][0]
    database.query(
        centroid=partition["centroid"],
        f0=partition["f0"],
        flatness=partition["flatness"],
        is_voiced=partition["is_voiced"],
        rms=partition["rms"],
        rolloff=partition["rolloff"],
        k=5,
    )
