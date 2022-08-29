import logging
import shutil
from pathlib import Path

import pytest

import archon.pipeline
from archon.config import ArchonConfig


@pytest.mark.parametrize(
    "filename, expected_shape",
    [
        ("audio-a.wav", (50, 689)),
        ("audio-b.wav", (50, 689)),
        ("audio-c.wav", (50, 750)),
    ],
)
def test_analyze(archon_config, filename, expected_shape, caplog):
    caplog.set_level(logging.INFO)
    root_path = Path(__file__).parent
    analysis = archon.pipeline.analyze(archon_config, root_path / filename)
    assert analysis.array.shape == expected_shape


@pytest.mark.parametrize("filename", ["audio-a.wav", "audio-b.wav", "audio-c.wav"])
def test_partition(archon_config, filename):
    root_path = Path(__file__).parent
    analysis = archon.pipeline.analyze(archon_config, root_path / filename)
    archon.pipeline.partition(analysis)


def test_run(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    config = ArchonConfig(analysis_path=tmp_path / "analysis.json")
    for filename in ["audio-a.wav", "audio-b.wav", "audio-c.wav"]:
        shutil.copy(Path(__file__).parent / filename, tmp_path / filename)
    archon.pipeline.run(config)
