from supriya import DoneAction
from supriya.synthdefs import Envelope, synthdef
from supriya.ugens import (
    FFT,
    HPF,
    LPF,
    MFCC,
    AllpassL,
    Amplitude,
    BufDur,
    BufFrames,
    BufRateScale,
    BufWr,
    CombL,
    CompanderD,
    DelayN,
    Dust,
    EnvGen,
    ExpRand,
    GrainBuf,
    Impulse,
    In,
    LFDNoise3,
    LFNoise1,
    LFNoise2,
    LeakDC,
    Limiter,
    Line,
    LocalBuf,
    Mix,
    Onsets,
    Out,
    Pan2,
    Pitch,
    PlayBuf,
    Rand,
    ReplaceOut,
    SendReply,
    SpecCentroid,
    SpecFlatness,
    SpecPcile,
    Warp1,
    WhiteNoise,
    XOut,
)


def build_offline_analysis_synthdef(
    frame_length: int = 2048,
    hop_ratio: float = 0.5,
    pitch_detection_max_frequency: float = 3000.0,
    pitch_detection_min_frequency: float = 60.0,
):
    @synthdef()
    def analysis(in_, output_buffer_id, duration):
        source = In.ar(bus=in_)
        peak = Amplitude.ar(source=source).amplitude_to_db()
        rms = (
            LPF.ar(source=source * source, frequency=10.0)
            .square_root()
            .amplitude_to_db()
        )
        frequency, is_voiced = Pitch.kr(
            source=source,
            min_frequency=pitch_detection_min_frequency,
            max_frequency=pitch_detection_max_frequency,
        )
        pv_chain = FFT.kr(
            buffer_id=LocalBuf(frame_length), source=source, hop=hop_ratio
        )
        is_onset = Onsets.kr(
            pv_chain=pv_chain,
            floor=0.000001,
            relaxtime=0.1,
            threshold=0.01,
            odftype=Onsets.ODFType.WPHASE,
        )
        centroid = SpecCentroid.kr(pv_chain=pv_chain)
        flatness = SpecFlatness.kr(pv_chain=pv_chain)
        rolloff = SpecPcile.kr(pv_chain=pv_chain)
        mfcc = MFCC.kr(pv_chain=pv_chain, coeff_count=42)
        phase = Line.ar(
            start=0,
            stop=BufFrames.kr(buffer_id=output_buffer_id),
            duration=duration,
            done_action=2,
        )
        BufWr.kr(
            buffer_id=output_buffer_id,
            phase=phase,
            source=[
                peak,
                rms,
                frequency.hz_to_midi(),
                is_voiced,
                is_onset,
                centroid,
                flatness,
                rolloff,
                *mfcc,
            ],
        )

    return analysis


def build_online_analysis_synthdef(
    mfcc_count=13,
    pitch_detection_max_frequency=3000.0,
    pitch_detection_min_frequency=60.0,
):
    @synthdef()
    def analysis(in_=0, tps=10):
        source = In.ar(bus=in_)
        trigger = Impulse.kr(frequency=tps)
        peak = Amplitude.ar(source=source).amplitude_to_db()
        rms = (
            LPF.ar(source=source * source, frequency=10.0)
            .square_root()
            .amplitude_to_db()
        )
        frequency, is_voiced = Pitch.kr(
            source=source,
            min_frequency=pitch_detection_min_frequency,
            max_frequency=pitch_detection_max_frequency,
        )
        pv_chain = FFT.kr(buffer_id=LocalBuf(2048), source=source)
        is_onset = Onsets.kr(
            pv_chain=pv_chain,
            floor=0.000001,
            relaxtime=0.1,
            threshold=0.01,
            odftype=Onsets.ODFType.WPHASE,
        )
        centroid = SpecCentroid.kr(pv_chain=pv_chain)
        flatness = SpecFlatness.kr(pv_chain=pv_chain)
        rolloff = SpecPcile.kr(pv_chain=pv_chain)
        mfcc = MFCC.kr(pv_chain=pv_chain, coeff_count=mfcc_count)
        SendReply.kr(
            command_name="/analysis",
            source=[
                peak,
                rms,
                frequency.hz_to_midi(),
                is_voiced,
                is_onset,
                centroid,
                flatness,
                rolloff,
                *mfcc,
            ],
            trigger=trigger,
        )

    return analysis


@synthdef()
def playback(
    attack_time=0.1,
    buffer_id=0,
    gain=0.0,
    out=0,
    panning=0.0,
    transposition=0.0,
    release_time=0.4,
):
    signal = PlayBuf.ar(
        buffer_id=buffer_id,
        done_action=DoneAction.FREE_SYNTH,
        rate=BufRateScale.ir(buffer_id=buffer_id) * transposition.semitones_to_ratio(),
    )
    signal *= EnvGen.kr(
        envelope=Envelope.percussive(
            attack_time=attack_time, release_time=release_time
        ),
        done_action=DoneAction.FREE_SYNTH,
    )
    signal = Pan2.ar(source=signal, position=panning, level=gain.db_to_amplitude())
    Out.ar(bus=out, source=signal)


@synthdef()
def granulate(buffer_id=0, gain=0.0, out=0, panning=0.0, time_scaling=1.0):
    duration = BufDur.kr(buffer_id=buffer_id) * time_scaling
    window = Line.kr(
        duration=duration, done_action=DoneAction.FREE_SYNTH
    ).hanning_window()
    signal = (
        GrainBuf.ar(
            buffer_id=buffer_id,
            channel_count=2,
            duration=WhiteNoise.ar().scale(-1, 1, 0.1, 0.2, exponential=True),
            interpolate=4,
            pan=WhiteNoise.ar(),
            position=panning + (WhiteNoise.ar() * 0.1),
            rate=WhiteNoise.ar().scale(-1, 1, -1, 0).semitones_to_ratio(),
            trigger=Dust.ar(density=window.scale(0, 1, 0, 100)),
        )
        * window
        * gain.db_to_amplitude()
    )
    Out.ar(bus=out, source=signal)


@synthdef()
def warp(
    buffer_id=0,
    gain=0.0,
    highpass_frequency=100.0,
    out=0,
    overlaps=4,
    panning=0.0,
    start=0.0,
    stop=1.0,
    time_scaling=1.0,
    transposition=0.0,
):
    duration = BufDur.kr(buffer_id=buffer_id) * time_scaling
    window = Line.kr(
        duration=duration, done_action=DoneAction.FREE_SYNTH
    ).hanning_window()
    pointer = Line.kr(start=start, stop=stop, duration=duration)
    signals = []
    for _ in range(2):
        window_size = LFDNoise3.kr(
            frequency=ExpRand.ir(minimum=0.01, maximum=0.1)
        ).exponential_range(0.05, 0.5)
        position = panning * LFNoise2.kr(frequency=0.5).scale(-1, 1, 0.5, 1)
        frequency_scaling = (
            transposition + LFNoise2.kr(0.1).scale(-1, 1, 0, 0.1)
        ).semitones_to_ratio()
        signal = Warp1.ar(
            buffer_id=buffer_id,
            frequency_scaling=frequency_scaling,
            interpolation=4,
            overlaps=overlaps,
            pointer=(
                (pointer + LFNoise2.kr(1.0) * 0.05).clip(0.0, 1.0)
                * ((duration - window_size) / duration)
            ),
            window_rand_ratio=0.15,
            window_size=window_size,
        )
        signal = HPF.ar(source=signal, frequency=highpass_frequency)
        signal *= window * 0.5
        signal = Pan2.ar(source=signal, position=position, level=gain.db_to_amplitude())
        signals.append(signal)
    signal = LeakDC.ar(Mix.multichannel(signal, 2)).tanh()
    Out.ar(bus=out, source=signal)


@synthdef()
def compander(in_=0, out=0):
    pass


@synthdef()
def limiter(in_=0, out=0):
    source = In.ar(bus=in_, channel_count=2)
    bands, rest = [], source
    for frequency in [150, 1500, 6000]:
        band = LPF.ar(source=rest, frequency=frequency)
        bands.append(band)
        rest = rest - band
    bands.append(rest)
    source = Mix.multichannel(
        sources=[
            CompanderD.ar(source=band, slope_above=0.25, threshold=0.25)
            for band in bands
        ],
        channel_count=2,
    )
    source = Limiter.ar(source=source, duration=0.1)
    ReplaceOut.ar(bus=out, source=source)


@synthdef()
def freezeverb(in_=0, out=0):
    pass


@synthdef()
def hdverb(in_=0, out=0, decay=3.5, mix=0.08, lpf1=2000, lpf2=6000, predelay=0.025):
    comb_count = 16 // 2
    allpass_count = 8
    source = In.ar(bus=in_, channel_count=2)
    source = DelayN.ar(
        source=source, maximum_delay_time=0.5, delay_time=predelay.clip(0.0001, 0.5)
    )
    source = (
        Mix.new(
            LPF.ar(
                source=CombL.ar(
                    source=source,
                    maximum_delay_time=0.1,
                    delay_time=LFNoise1.kr(
                        frequency=[
                            ExpRand.ir(minimum=0.02, maximum=0.04) for _ in range(2)
                        ]
                    ).exponential_range(0.02, 0.099),
                    decay_time=decay,
                ),
                frequency=lpf1,
            )
            for _ in range(comb_count)
        )
        * 0.25
    )
    for _ in range(allpass_count):
        source = AllpassL.ar(
            source=source,
            maximum_delay_time=0.1,
            delay_time=LFNoise1.kr(
                frequency=[ExpRand.ir(minimum=0.02, maximum=0.04) for _ in range(2)]
            ).exponential_range(0.02, 0.099),
            decay_time=decay,
        )
    source = LeakDC.ar(source=source)
    source = LPF.ar(source=source, frequency=lpf2) * 0.5
    XOut.ar(bus=out, source=source, crossfade=mix)
