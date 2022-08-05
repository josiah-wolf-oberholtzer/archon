import logging
from pathlib import Path

import pytest

import archon.pipeline


@pytest.mark.parametrize("filename", ["audio-a.wav", "audio-b.wav", "audio-c.wav"])
def test_analyze(filename):
    analysis = archon.pipeline.analyze(Path(__file__).parent / filename)
    shape = analysis.f0.shape
    assert shape[0] > 1
    assert analysis.centroid.shape == shape
    assert analysis.flatness.shape == shape
    assert analysis.is_voiced.shape == shape
    assert analysis.rms.shape == shape
    assert analysis.rolloff.shape == shape


@pytest.mark.parametrize("filename", ["audio-a.wav", "audio-b.wav", "audio-c.wav"])
def test_partition(filename):
    analysis = archon.pipeline.analyze(Path(__file__).parent / filename)
    archon.pipeline.partition(analysis)


def test_run(caplog, tmp_path):
    caplog.set_level(logging.INFO)
    input_path = Path(__file__).parent
    output_path = tmp_path / "analysis.json"
    archon.pipeline.run(input_path, output_path)
