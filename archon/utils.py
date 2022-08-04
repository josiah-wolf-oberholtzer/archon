import os
from contextlib import contextmanager
from time import perf_counter


@contextmanager
def cd(path: os.PathLike):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(cwd)


@contextmanager
def timer() -> float:
    start = perf_counter()
    yield lambda: perf_counter() - start
