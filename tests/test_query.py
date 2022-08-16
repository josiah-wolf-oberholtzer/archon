import json
from pathlib import Path

from archon.query import Database, Entry


def test_Database():
    analysis_path = Path(__file__).parent / "analysis.json"
    analysis = json.loads(analysis_path.read_text())
    database = Database.new(analysis_path)
    partition = analysis["partitions"][0]
    pairs = database.query(
        centroid=partition["centroid"],
        f0=partition["f0"],
        flatness=partition["flatness"],
        is_voiced=partition["is_voiced"],
        rms=partition["rms"],
        rolloff=partition["rolloff"],
        k=5,
    )
    assert pairs == [
        (
            Entry(
                path=Path("audio-a-duplicate.wav"), starting_frame=0, frame_count=44544
            ),
            0.0,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=45056,
                frame_count=44544,
            ),
            0.056845,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=135168,
                frame_count=44544,
            ),
            0.061365,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=157696,
                frame_count=44544,
            ),
            0.082172,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=180224,
                frame_count=44544,
            ),
            0.091955,
        ),
    ]
