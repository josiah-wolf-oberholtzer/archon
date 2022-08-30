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
                "10acdc0bf8d443f4bf93cd35fb9b93ead4285be66721ebcb07e332c0d229b3a5",
                "449397dd5409f84405864db100d3d5d8f5096ce4ccd3eb97c6b131bb5a9ec6b2",
                "e18351e60f0440e25bfdcfd04e57bff2929e79dd5936d16766f0d5493f3183cf",
                "56a78ec168b951155f7218c59cde2c54569a8decbb327441e9bbf8bb5204a455",
                "30e70939de42b5559d6bd8d5a453c4ddac65f22fb15657466430049290d648f6",
            ],
            [0.0, 0.196038, 0.334901, 0.344708, 0.365163],
        ),
        (
            False,
            True,
            True,
            [
                "10acdc0bf8d443f4bf93cd35fb9b93ead4285be66721ebcb07e332c0d229b3a5",
                "a5f108079ec54d2c9d8404bf070df7cb2a05032d80f2b8d35326bf350bfd13d3",
                "6e8d3eb0dfad14db3940459a16f38bdef101a310b115f83466e085c64bacb764",
                "56a78ec168b951155f7218c59cde2c54569a8decbb327441e9bbf8bb5204a455",
                "e18351e60f0440e25bfdcfd04e57bff2929e79dd5936d16766f0d5493f3183cf",
            ],
            [0.0, 0.076624, 0.098552, 0.118218, 0.143284],
        ),
        (
            True,
            True,
            False,
            [
                "10acdc0bf8d443f4bf93cd35fb9b93ead4285be66721ebcb07e332c0d229b3a5",
                "449397dd5409f84405864db100d3d5d8f5096ce4ccd3eb97c6b131bb5a9ec6b2",
                "0cba6bc4595ab466498038cc6fdc37764cf5754ee2a336c2057e4a69bedfea4c",
                "3dc772dc1364e9e00b74ebcfc1feafc7a97cb357f56aef0f3598f743218ef1f7",
                "30e70939de42b5559d6bd8d5a453c4ddac65f22fb15657466430049290d648f6",
            ],
            [0.0, 0.129665, 0.241927, 0.244753, 0.248423],
        ),
        (
            True,
            False,
            False,
            [
                "10acdc0bf8d443f4bf93cd35fb9b93ead4285be66721ebcb07e332c0d229b3a5",
                "449397dd5409f84405864db100d3d5d8f5096ce4ccd3eb97c6b131bb5a9ec6b2",
                "0cba6bc4595ab466498038cc6fdc37764cf5754ee2a336c2057e4a69bedfea4c",
                "3dc772dc1364e9e00b74ebcfc1feafc7a97cb357f56aef0f3598f743218ef1f7",
                "30e70939de42b5559d6bd8d5a453c4ddac65f22fb15657466430049290d648f6",
            ],
            [0.0, 0.129665, 0.241927, 0.244753, 0.248423],
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
