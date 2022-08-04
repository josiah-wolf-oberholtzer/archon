import os
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
def timer() -> Generator[Callable[[], float], None, None]:
    def get_time() -> float:
        return perf_counter() - start

    start = perf_counter()
    yield get_time
