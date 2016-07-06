from datetime import datetime
import logging

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

__author__ = 'petercable'

Base = declarative_base()
log = logging.getLogger(__name__)


event_types = ('start', 'command', 'response', 'exception', 'completion')


class MissionData(Base):
    __tablename__ = 'missions'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    script_id = Column(Integer, ForeignKey('scripts.id'))
    active = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)

    script = relationship('Script', foreign_keys=[script_id])


class Script(Base):
    __tablename__ = 'scripts'
    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey('missions.id'))
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    script = Column(String, nullable=False)
    create_time = Column(DateTime, default=datetime.now)

    UniqueConstraint('name', 'version')
    mission = relationship('MissionData', foreign_keys=[mission_id])


class Run(Base):
    __tablename__ = 'runs'
    id = Column(Integer, primary_key=True)
    mission_id = Column(Integer, ForeignKey('missions.id'))
    script_id = Column(Integer, ForeignKey('scripts.id'))

    mission = relationship('MissionData', backref=backref('runs', order_by=id.desc()))
    script = relationship('Script', backref=backref('runs', order_by=id.desc()))


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('runs.id'))
    timestamp = Column(DateTime, default=datetime.now)
    event_type_id = Column(Integer, ForeignKey('event_types.id'))
    event = Column(String)

    run = relationship('Run', backref=backref('events', order_by=id))
    type = relationship('EventType')


class EventType(Base):
    __tablename__ = 'event_types'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


def create_db(app):
    log.info('Creating database')
    Base.metadata.create_all(app.engine)
    session = app.Session()

    for event in event_types:
        et_count = session.query(EventType).filter(EventType.name == event).count()
        if et_count == 0:
            et = EventType(name=event)
            session.add(et)

    session.commit()
