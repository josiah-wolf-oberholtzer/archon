from supriya import DoneAction
from supriya.synthdefs import Envelope, synthdef
from supriya.ugens import (  # RMS,
    FFT,
    LPF,
    MFCC,
    Amplitude,
    BufRateScale,
    EnvGen,
    Impulse,
    In,
    LocalBuf,
    Onsets,
    Out,
    Pan2,
    Pitch,
    PlayBuf,
    SendReply,
    SpecCentroid,
    SpecFlatness,
    SpecPcile,
)


def build_analysis_synthdef(
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
        pv_chain = FFT.new(buffer_id=LocalBuf(2048), source=source)
        is_onset = Onsets.kr(
            pv_chain=pv_chain,
            floor=0.000001,
            # relaxtime=0.1,
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
        rate=BufRateScale.ir(buffer_id) * transposition.semitones_to_ratio(),
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
def granulate(buffer_id=0, out=0):
    pass


@synthdef()
def warp(buffer_id=0, out=0):
    pass


@synthdef()
def compander(in_=0, out=0):
    pass


@synthdef()
def limiter(in_=0, out=0):
    pass


@synthdef()
def freezeverb(in_=0, out=0):
    pass


@synthdef()
def hdverb(in_=0, out=0):
    pass
