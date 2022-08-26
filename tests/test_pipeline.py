import logging
import shutil
from pathlib import Path

import pytest

import archon.pipeline
from archon.config import ArchonConfig


@pytest.mark.parametrize(
    "filename, expected_shape",
    [("audio-a.wav", (1387,)), ("audio-b.wav", (1387,)), ("audio-c.wav", (1509,))],
)
def test_analyze(archon_config, filename, expected_shape):
    root_path = Path(__file__).parent
    analysis = archon.pipeline.analyze(archon_config, root_path / filename)
    assert analysis.f0.shape == expected_shape
    assert analysis.centroid.shape == expected_shape
    assert analysis.flatness.shape == expected_shape
    assert analysis.is_voiced.shape == expected_shape
    assert analysis.rms.shape == expected_shape
    assert analysis.rolloff.shape == expected_shape


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


@pytest.mark.parametrize(
    "filename, expected_shape",
    [
        ("audio-a.wav", (13, 1378)),
        ("audio-b.wav", (13, 1378)),
        ("audio-c.wav", (13, 3000)),  # would normally get SR-adjusted hop length
    ],
)
def test_analyze_mfcc(filename, expected_shape):
    root_path = Path(__file__).parent
    mfcc = archon.pipeline.analyze_mfcc(root_path / filename)
    assert mfcc.shape == expected_shape
