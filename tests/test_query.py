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
                "126a79d30444d49c58f572487f06d6bd390c9e16",
                "ff3130073a1c6d1394a93a461a0ee6da773462b2",
                "a2cdee918e642a86abe3927802f880d7031e91b8",
                "93e8c39ecd95897ce5a7a6afc1e0b99ddf5dcb3f",
                "c94a1f9c790f47c71706a5dcda3c4f106896db0b",
            ],
            [0.0, 0.223626, 0.230341, 0.235912, 0.251648],
        ),
        (
            False,
            True,
            True,
            [
                "126a79d30444d49c58f572487f06d6bd390c9e16",
                "1b5af811fc59140da5c90ae449f5d4bc47b035b1",
                "93e8c39ecd95897ce5a7a6afc1e0b99ddf5dcb3f",
                "a2cdee918e642a86abe3927802f880d7031e91b8",
                "15e2d25c276f98ddef1959939b0b83c4f942f769",
            ],
            [0.0, 0.056845, 0.061365, 0.082172, 0.091955],
        ),
        (
            True,
            True,
            False,
            [
                "126a79d30444d49c58f572487f06d6bd390c9e16",
                "c94a1f9c790f47c71706a5dcda3c4f106896db0b",
                "ff3130073a1c6d1394a93a461a0ee6da773462b2",
                "a2cdee918e642a86abe3927802f880d7031e91b8",
                "93e8c39ecd95897ce5a7a6afc1e0b99ddf5dcb3f",
            ],
            [0.0, 0.180947, 0.181316, 0.215186, 0.227791],
        ),
        (
            True,
            False,
            False,
            [
                "126a79d30444d49c58f572487f06d6bd390c9e16",
                "05a33fa28cf78dc7c2dc014bfdc489b60f234765",
                "c94a1f9c790f47c71706a5dcda3c4f106896db0b",
                "ff3130073a1c6d1394a93a461a0ee6da773462b2",
                "a2cdee918e642a86abe3927802f880d7031e91b8",
            ],
            [0.0, 0.170923, 0.180947, 0.181316, 0.215186],
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
        is_voiced=partition["is_voiced"],
        mfcc=partition["mfcc"],
        rms=partition["rms"],
        rolloff=partition["rolloff"],
        k=5,
    )
    actual_digests = [entry.digest for entry, _ in pairs]
    actual_distances = [distance for _, distance in pairs]
    assert expected_digests == actual_digests
    assert expected_distances == actual_distances
