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
                path=Path("audio-a-duplicate.wav"),
                starting_frame=0,
                frame_count=44544,
                digest="beda59d8aed1554cf6b40b2367bb769ebcfea773",
            ),
            0.0,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=45056,
                frame_count=44544,
                digest="2c6843729de42834ea044d6fc827c6d36b7120cc",
            ),
            0.056845,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=135168,
                frame_count=44544,
                digest="a952b666ed24cd95482ce3becfd5defa9acb02dd",
            ),
            0.061365,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=157696,
                frame_count=44544,
                digest="0fa2071872b9964efa6d8da4ab6fc3d14915c3fa",
            ),
            0.082172,
        ),
        (
            Entry(
                path=Path("audio-a-duplicate.wav"),
                starting_frame=180224,
                frame_count=44544,
                digest="93e47f54ad950d95e482c739e2e34be5f65846a4",
            ),
            0.091955,
        ),
    ]
