from supriya.synthdefs import synthdef
from supriya.ugens import (  # RMS,
    FFT,
    LPF,
    Amplitude,
    Impulse,
    In,
    LocalBuf,
    Onsets,
    Pitch,
    SendReply,
    SpecCentroid,
    SpecFlatness,
    SpecPcile,
)

from . import config


@synthdef()
def analysis(in_=0, tps=10):
    source = In.ar(bus=in_)
    trigger = Impulse.kr(frequency=tps)
    peak = Amplitude.ar(source=source)
    rms = LPF.ar(source=source * source, frequency=10.0).square_root().amplitude_to_db()
    frequency, is_voiced = Pitch.kr(
        source=source,
        min_frequency=config.PITCH_DETECTION_MIN_FREQUENCY,
        max_frequency=config.PITCH_DETECTION_MAX_FREQUENCY,
    )
    pv_chain = FFT.new(buffer_id=LocalBuf(4096), source=source)
    onsets = Onsets.kr(
        pv_chain=pv_chain,
        floor=0.000001,
        # relaxtime=0.1,
        threshold=0.01,
        odftype=Onsets.ODFType.WPHASE,
    )
    centroid = SpecCentroid.kr(pv_chain=pv_chain)
    flatness = SpecFlatness.kr(pv_chain=pv_chain)
    rolloff = SpecPcile.kr(pv_chain=pv_chain)
    SendReply.kr(
        command_name="/analysis",
        source=[peak, rms, frequency, is_voiced, onsets, centroid, flatness, rolloff],
        trigger=trigger,
    )


@synthdef()
def playback(buffer_id=0, out=0):
    pass


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
