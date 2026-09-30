import fcntl
from contextlib import contextmanager
from pathlib import Path
from .model import DataError

@contextmanager
def writer_lock(path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise DataError('Another publisher holds the state lock') from None
        try:yield
        finally:fcntl.flock(f,fcntl.LOCK_UN)
