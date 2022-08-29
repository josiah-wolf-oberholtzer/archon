import json

import pytest

from archon.query import Database


@pytest.mark.parametrize(
    "use_mfcc, use_pitch, use_spectral, expected_digests, expected_distances",
    [
        (
            True,
            True,
            True,
            [
                "69b419255dc7a440ffeff0324feea3c35aba39e3",
                "f30d428ceb121d5bb4ef0b0b1a171ae6395553ed",
                "9ee808f4d00efe4bf56e8ec2c3d2fa7382ee648e",
                "f85b30516c1fbea2ea97c35b127a561cffd263f5",
                "35309d5dc893947df968d9de741f174b018bf9e6",
            ],
            [0.0, 0.230389, 0.233664, 0.244061, 0.263477],
        ),
        (
            False,
            True,
            True,
            [
                "69b419255dc7a440ffeff0324feea3c35aba39e3",
                "f85b30516c1fbea2ea97c35b127a561cffd263f5",
                "9ee808f4d00efe4bf56e8ec2c3d2fa7382ee648e",
                "f30d428ceb121d5bb4ef0b0b1a171ae6395553ed",
                "35309d5dc893947df968d9de741f174b018bf9e6",
            ],
            [0.0, 0.035333, 0.056886, 0.143401, 0.152101],
        ),
        (
            True,
            True,
            False,
            [
                "69b419255dc7a440ffeff0324feea3c35aba39e3",
                "b1e9f27d263ab8d809c454df0e8143cc973a697b",
                "d2629c0ebe4d3531af1e3b4bf0d2b4f36ad99d5c",
                "f30d428ceb121d5bb4ef0b0b1a171ae6395553ed",
                "35309d5dc893947df968d9de741f174b018bf9e6",
            ],
            [0.0, 0.170214, 0.177495, 0.18032, 0.215141],
        ),
        (
            True,
            False,
            False,
            [
                "69b419255dc7a440ffeff0324feea3c35aba39e3",
                "b1e9f27d263ab8d809c454df0e8143cc973a697b",
                "d2629c0ebe4d3531af1e3b4bf0d2b4f36ad99d5c",
                "f30d428ceb121d5bb4ef0b0b1a171ae6395553ed",
                "35309d5dc893947df968d9de741f174b018bf9e6",
            ],
            [0.0, 0.170214, 0.177495, 0.18032, 0.215141],
        ),
    ],
)
def test_Database(
    archon_config,
    use_mfcc,
    use_pitch,
    use_spectral,
    expected_digests,
    expected_distances,
):
    archon_config.use_mfcc = use_mfcc
    archon_config.use_pitch = use_pitch
    archon_config.use_spectral = use_spectral
    analysis = json.loads(archon_config.analysis_path.read_text())
    database = Database.new(archon_config)
    partition = analysis["partitions"][0]
    pairs = database.query(
        centroid=partition["centroid"],
        f0=partition["f0"],
        flatness=partition["flatness"],
        mfcc=partition["mfcc"],
        rms=partition["rms"],
        rolloff=partition["rolloff"],
        k=5,
    )
    actual_digests = [entry.digest for entry, _ in pairs]
    actual_distances = [distance for _, distance in pairs]
    assert expected_digests == actual_digests
    assert expected_distances == actual_distances
