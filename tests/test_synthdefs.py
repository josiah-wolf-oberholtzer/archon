from uqbar.strings import normalize

from archon import synthdefs


def test_build_online_analysis_synthdef():
    assert str(synthdefs.build_online_analysis_synthdef()) == normalize(
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
            -   UnaryOpUGen(AMPLITUDE_TO_DB).ar/0:
                    source: Amplitude.ar[0]
            -   BinaryOpUGen(MULTIPLICATION).ar:
                    left: In.ar[0]
                    right: In.ar[0]
            -   LPF.ar:
                    source: BinaryOpUGen(MULTIPLICATION).ar[0]
                    frequency: 10.0
            -   UnaryOpUGen(SQUARE_ROOT).ar:
                    source: LPF.ar[0]
            -   UnaryOpUGen(AMPLITUDE_TO_DB).ar/1:
                    source: UnaryOpUGen(SQUARE_ROOT).ar[0]
            -   Pitch.kr:
                    source: In.ar[0]
                    initial_frequency: 440.0
                    min_frequency: 60.0
                    max_frequency: 3000.0
                    exec_frequency: 100.0
                    max_bins_per_octave: 16.0
                    median: 1.0
                    amplitude_threshold: 0.01
                    peak_threshold: 0.5
                    down_sample_factor: 1.0
                    clarity: 0.0
            -   Impulse.kr:
                    frequency: Control.kr[1:tps]
                    phase: 0.0
            -   MaxLocalBufs.ir:
                    maximum: 1.0
            -   LocalBuf.ir:
                    channel_count: 1.0
                    frame_count: 2048.0
            -   FFT.kr:
                    buffer_id: LocalBuf.ir[0]
                    source: In.ar[0]
                    hop: 0.5
                    window_type: 0.0
                    active: 1.0
                    window_size: 0.0
            -   Onsets.kr:
                    pv_chain: FFT.kr[0]
                    threshold: 0.01
                    odftype: 5.0
                    relaxtime: 0.1
                    floor: 1.0e-06
                    mingap: 10.0
                    medianspan: 11.0
                    whtype: 1.0
                    rawodf: 0.0
            -   SpecCentroid.kr:
                    pv_chain: FFT.kr[0]
            -   SpecFlatness.kr:
                    pv_chain: FFT.kr[0]
            -   SpecPcile.kr:
                    pv_chain: FFT.kr[0]
                    fraction: 0.5
                    interpolate: 0.0
            -   MFCC.kr:
                    pv_chain: FFT.kr[0]
                    coeff_count: 13.0
            -   UnaryOpUGen(HZ_TO_MIDI).kr:
                    source: Pitch.kr[0]
            -   SendReply.kr:
                    trigger: Impulse.kr[0]
                    reply_id: -1.0
                    character_count: 9.0
                    character[0]: 47.0
                    character[1]: 97.0
                    character[2]: 110.0
                    character[3]: 97.0
                    character[4]: 108.0
                    character[5]: 121.0
                    character[6]: 115.0
                    character[7]: 105.0
                    character[8]: 115.0
                    source[0]: UnaryOpUGen(AMPLITUDE_TO_DB).ar/0[0]
                    source[1]: UnaryOpUGen(AMPLITUDE_TO_DB).ar/1[0]
                    source[2]: UnaryOpUGen(HZ_TO_MIDI).kr[0]
                    source[3]: Pitch.kr[1]
                    source[4]: Onsets.kr[0]
                    source[5]: SpecCentroid.kr[0]
                    source[6]: SpecFlatness.kr[0]
                    source[7]: SpecPcile.kr[0]
                    source[8]: MFCC.kr[0]
                    source[9]: MFCC.kr[1]
                    source[10]: MFCC.kr[2]
                    source[11]: MFCC.kr[3]
                    source[12]: MFCC.kr[4]
                    source[13]: MFCC.kr[5]
                    source[14]: MFCC.kr[6]
                    source[15]: MFCC.kr[7]
                    source[16]: MFCC.kr[8]
                    source[17]: MFCC.kr[9]
                    source[18]: MFCC.kr[10]
                    source[19]: MFCC.kr[11]
                    source[20]: MFCC.kr[12]
        """
    )
