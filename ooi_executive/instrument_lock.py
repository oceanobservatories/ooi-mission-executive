from contextlib import contextmanager
import logging

__author__ = 'petercable'

log = logging.getLogger(__name__)


@contextmanager
def lock_instrument(instruments, executor, add_event):
    try:
        log.info('Locking instruments %r', instruments)
        executor.lock(instruments)
        add_event('lock', '\n'.join(instruments))
        yield
    finally:
        log.info('Releasing lock on instruments %r', instruments)
        executor.unlock(instruments)
        add_event('unlock', '\n'.join(instruments))
