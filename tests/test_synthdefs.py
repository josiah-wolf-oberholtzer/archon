from uqbar.strings import normalize

from archon import synthdefs


def test_analysis():
    assert str(synthdefs.analysis) == normalize(
        """
        synthdef:
            name: analysis
            ugens:
            -   Control.kr: null
            -   In.ar:
                    bus: Control.kr[0:in_]
            -   Amplitude.ar:
                    source: In.ar[0]
                    attack_time: 0.01
                    release_time: 0.01
            -   Pitch.kr:
                    source: In.ar[0]
                    initial_frequency: 440.0
                    min_frequency: 60.0
                    max_frequency: 4000.0
                    exec_frequency: 100.0
                    max_bins_per_octave: 16.0
                    median: 1.0
                    amplitude_threshold: 0.01
                    peak_threshold: 0.5
                    down_sample_factor: 1.0
                    clarity: 0.0
            -   BinaryOpUGen(FLOAT_DIVISION).kr:
                    left: 1.0
                    right: Control.kr[1:rate]
            -   Impulse.kr:
                    frequency: BinaryOpUGen(FLOAT_DIVISION).kr[0]
                    phase: 0.0
            -   MaxLocalBufs.ir:
                    maximum: 1.0
            -   LocalBuf.ir:
                    channel_count: 1.0
                    frame_count: 4096.0
            -   FFT.kr:
                    buffer_id: LocalBuf.ir[0]
                    source: In.ar[0]
                    hop: 0.5
                    window_type: 0.0
                    active: 1.0
                    window_size: 0.0
            -   SpecCentroid.kr:
                    pv_chain: FFT.kr[0]
            -   SpecFlatness.kr:
                    pv_chain: FFT.kr[0]
            -   SpecPcile.kr:
                    pv_chain: FFT.kr[0]
                    fraction: 0.5
                    interpolate: 0.0
            -   SendReply.kr:
                    trigger: Impulse.kr[0]
                    reply_id: -1.0
                    size: 9.0
                    char[0]: 47.0
                    char[1]: 97.0
                    char[2]: 110.0
                    char[3]: 97.0
                    char[4]: 108.0
                    char[5]: 121.0
                    char[6]: 115.0
                    char[7]: 105.0
                    char[8]: 115.0
                    source[0]: Amplitude.ar[0]
                    source[1]: Pitch.kr[0]
                    source[2]: Pitch.kr[1]
                    source[3]: SpecCentroid.kr[0]
                    source[4]: SpecFlatness.kr[0]
                    source[5]: SpecPcile.kr[0]
        """
    )
