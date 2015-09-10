from threading import Thread
import logging
import time

__author__ = 'petercable'

log = logging.getLogger(__name__)


class JmsReader(Thread):
    def __init__(self):
        self.running = True
        self.listeners = []
        super(JmsReader, self).__init__()
        log.info('JMS reader initialized')

    def run(self):
        while self.running:
            # get event from JMS
            # self._forward_event(event)
            time.sleep(1)

    def _forward_event(self, event):
        for listener in self.listeners:
            listener(event)

    def add_listener(self, callback):
        self.listeners.append(callback)

    def interrupt(self, *args):
        self.running = False
