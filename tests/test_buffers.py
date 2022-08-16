import json
from pathlib import Path
from uuid import uuid4

from supriya import Provider

from archon.buffers import BufferManager
from archon.query import Database, Entry


def test_BufferManager():
    root_path = Path(__file__).parent
    analysis_path = root_path / "analysis.json"
    analysis = json.loads(analysis_path.read_text())
    provider = Provider.realtime()
    database = Database.new(analysis_path)
    partition = analysis["partitions"][0]
    entries = [
        entry
        for entry, _ in database.query(
            centroid=partition["centroid"],
            f0=partition["f0"],
            flatness=partition["flatness"],
            is_voiced=partition["is_voiced"],
            rms=partition["rms"],
            rolloff=partition["rolloff"],
            k=5,
        )
    ]
    uuid = uuid4()
    manager = BufferManager(provider, root_path=root_path)
    with provider.at(0):
        manager.increment_multiple(entries, uuid)
    assert manager.buffers_to_entities == {
        0: {uuid},
        1: {uuid},
        2: {uuid},
        3: {uuid},
        4: {uuid},
    }
    assert manager.buffers_to_entries == {
        0: entries[0],
        1: entries[1],
        2: entries[2],
        3: entries[3],
        4: entries[4],
    }
    assert manager.entities_to_buffers == {uuid: {0, 1, 2, 3, 4}}
    assert manager.entries_to_buffers == {
        entries[0]: 0,
        entries[1]: 1,
        entries[2]: 2,
        entries[3]: 3,
        entries[4]: 4,
    }
