from supriya.synthdefs import synthdef
from supriya.ugens import (  # RMS,
    FFT,
    Amplitude,
    Impulse,
    In,
    LPF,
    LocalBuf,
    Pitch,
    SendReply,
    SpecCentroid,
    SpecFlatness,
    SpecPcile,
)


@synthdef()
def analysis(in_=0, rate=10):
    source = In.ar(bus=in_)
    trigger = Impulse.kr(frequency=1 / rate)
    peak = Amplitude.ar(source=source)
    rms = LPF.ar(source=source * source, frequency=10.0).square_root()
    frequency, is_voiced = Pitch.kr(source=source)
    chain = FFT.new(buffer_id=LocalBuf(4096), source=source)
    centroid = SpecCentroid.kr(pv_chain=chain)
    flatness = SpecFlatness.kr(pv_chain=chain)
    rolloff = SpecPcile.kr(pv_chain=chain)
    SendReply.kr(
        command_name="/analysis",
        source=[peak, rms, frequency, is_voiced, centroid, flatness, rolloff],
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
