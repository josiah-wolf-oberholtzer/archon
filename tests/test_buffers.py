import json
from pathlib import Path
from uuid import UUID, uuid4

from supriya.providers import BufferProxy, Provider

from archon.buffers import BufferManager
from archon.query import Database


def format_manager(manager, cache):
    """
    Create a compact representation of manager state.

    Replace effectively random values with stable ones, mapping first
    appearance to index formatted as character(s).
    """

    def sanitize(value):
        if isinstance(value, BufferProxy):
            return int(value)
        elif isinstance(value, UUID):
            if value not in cache.setdefault("uuids", []):
                cache["uuids"].append(value)
            return f"uuid:{chr(cache['uuids'].index(value) + 97)}"
        elif isinstance(value, str) and len(value) == 40:
            if value not in cache.setdefault("digests", []):
                cache["digests"].append(value)
            return f"sha:{chr(cache['digests'].index(value) + 97)}"
        return value

    return {
        "b2e": {
            sanitize(buffer_): sorted(
                (sanitize(entity) for entity in entities), key=lambda x: str(x)
            )
            for buffer_, entities in manager.buffers_to_entities.items()
        },
        "e2b": {
            sanitize(entity): {sanitize(buffer_) for buffer_ in buffers_}
            for entity, buffers_ in manager.entities_to_buffers.items()
        },
        "b2d": {
            sanitize(buffer_): sanitize(entry.digest)
            for buffer_, entry in manager.buffers_to_entries.items()
        },
        "d2b": {
            sanitize(entry.digest): sanitize(buffer_)
            for entry, buffer_ in manager.entries_to_buffers.items()
        },
    }


def test_BufferManager():
    root_path = Path(__file__).parent
    analysis_path = root_path / "analysis.json"
    analysis = json.loads(analysis_path.read_text())
    provider = Provider.realtime()
    database = Database.new(
        analysis_path=analysis_path, use_mfcc=True, use_pitch=True, use_spectral=True
    )
    partition = analysis["partitions"][0]
    entries = [
        entry
        for entry, _ in database.query(
            centroid=partition["centroid"],
            f0=partition["f0"],
            flatness=partition["flatness"],
            is_voiced=partition["is_voiced"],
            mfcc=partition["mfcc"],
            rms=partition["rms"],
            rolloff=partition["rolloff"],
            k=6,
        )
    ]
    cache = {}
    uuid_a, uuid_b = uuid4(), uuid4()
    manager = BufferManager(provider, root_path=root_path)
    assert format_manager(manager, cache) == {
        "b2d": {},
        "b2e": {},
        "d2b": {},
        "e2b": {},
    }

    with provider.at(0):
        buffers_a = manager.increment_multiple(entries[:4], uuid_a)
    assert format_manager(manager, cache) == {
        "b2d": {0: "sha:a", 1: "sha:b", 2: "sha:c", 3: "sha:d"},
        "b2e": {0: ["uuid:a"], 1: ["uuid:a"], 2: ["uuid:a"], 3: ["uuid:a"]},
        "d2b": {"sha:a": 0, "sha:b": 1, "sha:c": 2, "sha:d": 3},
        "e2b": {"uuid:a": {0, 1, 2, 3}},
    }

    with provider.at(0):
        manager.increment(buffers_a[0], 1000)
    assert format_manager(manager, cache) == {
        "b2d": {0: "sha:a", 1: "sha:b", 2: "sha:c", 3: "sha:d"},
        "b2e": {0: [1000, "uuid:a"], 1: ["uuid:a"], 2: ["uuid:a"], 3: ["uuid:a"]},
        "d2b": {"sha:a": 0, "sha:b": 1, "sha:c": 2, "sha:d": 3},
        "e2b": {1000: {0}, "uuid:a": {0, 1, 2, 3}},
    }

    # increment player B with some shared buffers
    with provider.at(0):
        buffers_b = manager.increment_multiple(entries[2:], uuid_b)
    assert format_manager(manager, cache) == {
        "b2d": {0: "sha:a", 1: "sha:b", 2: "sha:c", 3: "sha:d", 4: "sha:e", 5: "sha:f"},
        "b2e": {
            0: [1000, "uuid:a"],
            1: ["uuid:a"],
            2: ["uuid:a", "uuid:b"],
            3: ["uuid:a", "uuid:b"],
            4: ["uuid:b"],
            5: ["uuid:b"],
        },
        "d2b": {"sha:a": 0, "sha:b": 1, "sha:c": 2, "sha:d": 3, "sha:e": 4, "sha:f": 5},
        "e2b": {1000: {0}, "uuid:a": {0, 1, 2, 3}, "uuid:b": {2, 3, 4, 5}},
    }

    # emit a node from player B, for a buffer shared by A, B and the new node
    with provider.at(0):
        manager.increment(buffers_b[0], 1001)
    assert format_manager(manager, cache) == {
        "b2d": {0: "sha:a", 1: "sha:b", 2: "sha:c", 3: "sha:d", 4: "sha:e", 5: "sha:f"},
        "b2e": {
            0: [1000, "uuid:a"],
            1: ["uuid:a"],
            2: [1001, "uuid:a", "uuid:b"],
            3: ["uuid:a", "uuid:b"],
            4: ["uuid:b"],
            5: ["uuid:b"],
        },
        "d2b": {"sha:a": 0, "sha:b": 1, "sha:c": 2, "sha:d": 3, "sha:e": 4, "sha:f": 5},
        "e2b": {1000: {0}, 1001: {2}, "uuid:a": {0, 1, 2, 3}, "uuid:b": {2, 3, 4, 5}},
    }

    # decrement player A's node
    with provider.at(0):
        manager.decrement(1000)
    assert format_manager(manager, cache) == {
        "b2d": {0: "sha:a", 1: "sha:b", 2: "sha:c", 3: "sha:d", 4: "sha:e", 5: "sha:f"},
        "b2e": {
            0: ["uuid:a"],
            1: ["uuid:a"],
            2: [1001, "uuid:a", "uuid:b"],
            3: ["uuid:a", "uuid:b"],
            4: ["uuid:b"],
            5: ["uuid:b"],
        },
        "d2b": {"sha:a": 0, "sha:b": 1, "sha:c": 2, "sha:d": 3, "sha:e": 4, "sha:f": 5},
        "e2b": {1001: {2}, "uuid:a": {0, 1, 2, 3}, "uuid:b": {2, 3, 4, 5}},
    }

    # then decrement player A
    with provider.at(0):
        manager.decrement(uuid_a)
    assert format_manager(manager, cache) == {
        "b2d": {2: "sha:c", 3: "sha:d", 4: "sha:e", 5: "sha:f"},
        "b2e": {2: [1001, "uuid:b"], 3: ["uuid:b"], 4: ["uuid:b"], 5: ["uuid:b"]},
        "d2b": {"sha:c": 2, "sha:d": 3, "sha:e": 4, "sha:f": 5},
        "e2b": {1001: {2}, "uuid:b": {2, 3, 4, 5}},
    }

    # decrement player B before decrementing the node it emitted
    with provider.at(0):
        manager.decrement(uuid_b)
    assert format_manager(manager, cache) == {
        "b2d": {2: "sha:c"},
        "b2e": {2: [1001]},
        "d2b": {"sha:c": 2},
        "e2b": {1001: {2}},
    }

    with provider.at(0):
        manager.decrement(1001)
    assert format_manager(manager, cache) == {
        "b2d": {},
        "b2e": {},
        "d2b": {},
        "e2b": {},
    }
