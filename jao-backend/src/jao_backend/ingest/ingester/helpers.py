import contextlib
import os
import tempfile


@contextlib.contextmanager
def cache_dir_contextmanager(cache_dir):
    yield cache_dir


def download_dir_or_tmp(cache_dir=None):
    if not cache_dir:
        return tempfile.TemporaryDirectory()

    if os.environ.get("JAO_DOWNLOAD_CACHE"):
        return cache_dir_contextmanager(cache_dir)
