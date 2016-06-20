import logging

IA_HOST = 'localhost'
IA_PORT = 12572
DEBUG = False
LOG_LEVEL = logging.DEBUG
OMS_SRVER = 'amqp://guest:guest@uframe-3-test.ooi.rutgers.edu:5672//'

# Currently only postgres is supported
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://awips@localhost/metadata'