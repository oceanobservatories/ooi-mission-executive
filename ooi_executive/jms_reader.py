from threading import Thread
import logging
import json

from ooi_executive import app

from kombu.mixins import ConsumerMixin
from kombu import Connection, Queue, Exchange

__author__ = 'petercable'

log = logging.getLogger(__name__)


class JmsReader(ConsumerMixin):
    def __init__(self):

        self.listeners = []

        oms_server = app.config['OMS_SERVER']

        self.connection = Connection(oms_server)
        self.exchange = Exchange(name='amq.topic', type='topic', channel=self.connection)
        self.queue = Queue(name='', exchange=self.exchange, routing_key='oms.alertalarm.msg',
                      channel=self.connection, durable=False, auto_delete=True)

        log.info('JMS reader initialized')

    def get_consumers(self, Consumer, channel):
        return [
            Consumer([self.queue], callbacks=[self.on_message]),
        ]

    def on_message(self, body, message):
        log.info("RECEIVED JMS MESSAGE: %s" % (body, ))

        message.ack()

        oms_msg = json.loads(body)
        attributes = oms_msg.get('attributes')
        source = attributes.get('omsplatformId')
        event = oms_msg.get('messageText')

        for listener in self.listeners:
            listener(source, event)

    def start(self):
        reader_thread = Thread(target=self.run)
        reader_thread.setDaemon(True)
        reader_thread.start()

    def add_listener(self, callback):
        self.listeners.append(callback)

    def interrupt(self, *args):
        self.should_stop = True
