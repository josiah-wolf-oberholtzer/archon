import cProfile
import io
import os
import pstats
from contextlib import contextmanager
from time import perf_counter
from typing import Callable, Generator


@contextmanager
def cd(path: os.PathLike):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def profiler():
    profiler = cProfile.Profile()
    profiler.enable()
    yield
    profiler.disable()
    stream = io.StringIO()
    profiler_stats = pstats.Stats(profiler, stream=stream)
    profiler_stats = profiler_stats.sort_stats("cumulative")
    profiler_stats.print_stats()
    print(stream.getvalue())


def scale(x, in_min, in_max, out_min, out_max):
    return (((x - in_min) / (in_max - in_min)) * (out_max - out_min)) + out_min


@contextmanager
def timer() -> Generator[Callable[[], float], None, None]:
    def get_time() -> float:
        return perf_counter() - start

    start = perf_counter()
    yield get_time
