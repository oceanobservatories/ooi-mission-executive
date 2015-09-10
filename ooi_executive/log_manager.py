import logging
from ooi_executive import app

__author__ = 'petercable'


def setup():
    formatter = logging.Formatter('%(asctime)s %(levelname)-5s %(name)-30s %(message)s')
    root_logger = logging.getLogger()
    root_logger.setLevel(app.config['LOG_LEVEL'])

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)

    fh = logging.FileHandler('executive.log')
    fh.setFormatter(formatter)
    root_logger.addHandler(fh)
