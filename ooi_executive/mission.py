import json
import time
import logging
import functools
from contextlib import contextmanager

import yaml
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from requests import ConnectionError
from jsonschema import validate

import mission_schema
from ooi_executive.backing_store import MissionData, Script, Run, EventType, Event
from ooi_executive.executors import RestExecutor
from ooi_executive.instrument_lock import lock_instrument
from ooi_executive import app
from ooi_executive.policies import ErrorPolicy
from ooi_executive.shared import Tags, MyEncoder, InstrumentException,\
    LockException, CommandArgumentException, PolicyException, DuplicateScriptException

__author__ = 'petercable'

log = logging.getLogger(__name__)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = app.Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class Mission(object):
    DEFAULT_TIMEOUT = 30000

    def __init__(self, mission_id=None, script=None, dbobj=None):
        self.mission = None
        self.id = None
        self.name = None
        self.blocks = None
        self.version = None
        self.schedule = None
        self.active = False
        self.run_count = 0
        self.created = 0
        self.event_types = self._get_event_types()

        if dbobj is not None:
            self._load(dbobj)

        elif script is not None:
            with session_scope() as session:
                dbobj = self._create(session, script)
                self._load(dbobj)

        elif mission_id is not None:
            with session_scope() as session:
                dbobj = session.query(MissionData).filter(MissionData.id == mission_id)
                if dbobj:
                    self._load(dbobj)

        # RUN PARAMETERS
        self.running = False
        self.job = None
        self.state = None
        self.current_step = None

        self.vars = {}
        # self.executor = DummyExecutor()
        host = app.config['IA_HOST']
        port = app.config['IA_PORT']
        self.executor = RestExecutor(self.name, host, port, timeout=self.DEFAULT_TIMEOUT)
        app.scheduler.add_listener(self._job_event_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        app.jms_reader.add_listener(self.jms_listener)

        if self.active:
            self.state = Tags.MISSION
            self._schedule_mission()

    def _get_event_types(self):
        session = app.Session()
        d = {}
        for event_type in session.query(EventType).all():
            d[event_type.name] = event_type.id
        return d

    def _create(self, session, data):
        log.info('Creating mission in database')
        mission_dict = yaml.load(data)
        validate(mission_dict, mission_schema.Mission.get_schema())
        name = mission_dict['name']
        version = mission_dict['version']

        # check if mission already exists, create if not
        mission = session.query(MissionData).filter(MissionData.name == name).one_or_none()
        if mission is None:
            mission = MissionData(name=name)
            session.add(mission)

        script = session.query(Script).filter(Script.name == name).filter(Script.version == version).one_or_none()
        if script is None:
            script = Script(script=data, name=name, version=version, mission=mission)
            session.add(script)

        if script.script != data:
            log.info('%r %r', script.script, data)
            raise DuplicateScriptException

        session.commit()

        # Set the current script to this script
        mission.script = script
        session.commit()
        return mission

    def _load(self, dbobj):
        log.info('Loading mission from database')
        self.mission_txt = dbobj.script.script
        self.mission = yaml.load(self.mission_txt)
        self.id = dbobj.id
        self.name = dbobj.name
        self.active = dbobj.active
        validate(self.mission, mission_schema.Mission.get_schema())
        self.blocks = self._load_blocks()
        self.version = dbobj.script.version
        self.run_count = len(dbobj.runs)
        self.schedule = self.mission.get('schedule')
        self.created = dbobj.script.create_time
        self.description = self.mission.get('desc')

    def delete(self):
        with session_scope() as session:
            dbobj = self._get_dbobj(session)
            dbobj.script = None
            session.commit()

    def _get_dbobj(self, session):
        return session.query(MissionData).filter(MissionData.id == self.id).one()

    def __repr__(self):
        return repr(self.mission)

    def _load_blocks(self):
        d = {}
        for block in self.mission.get('blocks', []):
            d[block['label']] = block
        return d

    def _job_event_listener(self, event):
        if event.job_id.startswith(self.name):
            if Tags.SCHEDULE not in self.mission:
                with session_scope() as session:
                    dbobj = self._get_dbobj(session)
                    dbobj.active = False
                    session.commit()
                    self.active = False

    def jms_listener(self, source, event):
        """
        Listen for JMS events
        Trigger an execute if a target event is received
        :param event:
        :return:
        """

        schedule = self.mission.get(Tags.SCHEDULE, {})

        # check if the incoming event is a trigger to execute the mission
        if schedule.get('source') == source and schedule.get('event') == event:

            log.debug('Scheduling Mission to Run immediately...')

            # Schedule the mission to run immediately
            self._add_job()

    def _get_events(self, session, run_id=None):
        events = []
        dbobj = self._get_dbobj(session)
        if not dbobj.runs:
            return []

        if run_id is None:
            run = dbobj.runs[0]
        else:
            run = session.query(Run).filter(Run.mission_id == self.id).filter(Run.id == run_id).one_or_none()

        if run and run.events:
            for event in run.events[:10]:
                try:
                    e = json.loads(event.event)
                except ValueError:
                    e = event.event
                events.append((event.timestamp.isoformat(), event.type.name, e))
            return events
        return []

    def small(self):
        job = app.scheduler.get_job(self.name)
        next_run = job.next_run_time.isoformat() if job else None
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'desc': self.description,
            'active': self.active,
            'running': self.running,
            'current_step': self.current_step,
            'run_count': self.run_count,
            'schedule': self.schedule,
            'next_run': next_run,
            'created': self.created.isoformat(),
        }

    def full(self):
        with session_scope() as session:
            events = self._get_events(session)
            base = self.small()
            base['events'] = events
            base['script'] = self.mission_txt
            return base

    def activate(self):
        if not self.active:
            with session_scope() as session:
                log.debug('Activating mission: %s', self.name)
                dbobj = self._get_dbobj(session)
                dbobj.active = True
                session.commit()

                self.active = True
                self.state = Tags.MISSION
                self._schedule_mission()

    def _add_job(self, trigger=None, kwargs=None):
        trigger = trigger or 'date'
        kwargs = kwargs or {}
        job_id = self.name
        app.scheduler.add_job(self._execute_mission, trigger, id=job_id, **kwargs)

    def _schedule_mission(self):
        """
        schedule the mission
        :return:
        """
        schedule = self.mission.get(Tags.SCHEDULE, {})
        cron_keys = {'year', 'month', 'day', 'week', 'day_of_week',
                     'hour', 'minute', 'second', 'start_date', 'end_date'}

        event_keys = {'source', 'event'}

        trigger = None

        if len(cron_keys.intersection(schedule.keys())) > 0:
            trigger = Tags.CRON
        elif len(event_keys.intersection(schedule.keys())) == 0:
            trigger = 'date'

        if trigger:
            self._add_job(trigger, schedule)

    def deactivate(self):
        if self.active:
            with session_scope() as session:
                log.debug('Deactivating mission: %s', self.name)
                dbobj = self._get_dbobj(session)
                dbobj.active = False
                job_id = self.name
                app.scheduler.remove_job(job_id)
                self.active = False

    def _add_event(self, session, run, event_type, event=''):
        if event_type not in self.event_types:
            et = EventType(name=event_type)
            session.add(et)
            session.commit()
            self.event_types[event_type] = et.id

        if not isinstance(event, basestring):
            try:
                event = json.dumps(event, cls=MyEncoder)
            except TypeError:
                log.error('Unable to create JSON from: %r %r', type(event), event)
                event = str(event)

        event = Event(run=run, event_type_id=self.event_types[event_type], event=event)
        session.add(event)
        session.commit()

    def _execute_mission(self):
        with session_scope() as session:
            dbobj = self._get_dbobj(session)
            run = Run(mission=dbobj, script=dbobj.script)
            session.add(run)
            session.commit()
            add_event = functools.partial(self._add_event, session, run)

            add_event('start')

            error_policy = ErrorPolicy(self.mission.get('onerror', {}))
            sequence = self.blocks.get(Tags.MISSION)
            if sequence is not None:
                complete = False
                attempt = 0
                max_attempts = error_policy.count
                backoff = error_policy.backoff
                while not complete and attempt < max_attempts:
                    try:
                        with lock_instrument(self.mission.get(Tags.INSTRUMENT, []), self.executor, add_event):
                            self.running = True
                            self.run_count += 1
                            self._execute_sequence(Tags.MISSION, add_event)
                            complete = True
                    except (LockException, ConnectionError) as e:
                        log.error('Exception locking instruments for mission: %s (%r)', self.name, e)
                        if error_policy.action == 'retry':
                            attempt += 1
                            time.sleep(backoff)
                        else:
                            break
                    except (InstrumentException, PolicyException, CommandArgumentException, ConnectionError) as e:
                        log.error('Exception when processing mission, aborting mission (%r)', e)
                        add_event('exception', str(e))
                        break
                    finally:
                        self.running = False
                        self.current_step = None

                if not complete:
                    log.error('Unable to complete mission: %s', self.name)

            add_event('completion')

    def _execute_sequence(self, section, add_event):
        block = self.blocks.get(section)
        sequence = block.get('sequence', [])
        block_error_policy = ErrorPolicy(block.get('onerror', self.mission.get('onerror', {})))
        if sequence is not None:
            for index, step in enumerate(sequence):
                error_policy = ErrorPolicy(step.get('onerror', {})) if 'onerror' in block else block_error_policy
                self.current_step = (index, step)
                log.info('Executing step: %s from mission: %s section: %s', step, self.name, section)
                add_event('step', step)
                rval = self._handle_step(step, error_policy, add_event)
                if rval is not None:
                    add_event('result', rval)

    def _handle_step(self, step, error_policy, add_event):
        log.info('step: %r', step)
        count = 0
        while count < error_policy.count:
            count += 1
            try:
                if 'block_name' in step:
                    if self._eval_conditional(step):
                        loop = step.get('loop', 1)
                        for _ in xrange(loop):
                            self._execute_sequence(step['block_name'], add_event)
                    return

                if 'sleep' in step:
                    return time.sleep(step['sleep'])

                rval = self.executor.command(step)
                if step.get('get_state'):
                    self.vars['driver_state'] = rval.value
                elif step.get('get') and step.get('parameter'):
                    self.vars[step.get('parameter')] = rval.value
                return rval

            except Exception as e:
                if error_policy.action == 'abort':
                    raise e
                if error_policy.action == 'continue':
                    log.error('Exception in step: %r executing continue policy: %r', step, e)
                    return

        raise PolicyException

    def _eval_conditional(self, step):
        log.debug('eval_conditional: %r', step)
        conditional = step.get('condition')
        if not conditional:
            return True

        expected_value = conditional.get('value')
        current_value = self.vars.get(conditional.get('variable'))
        comparator = conditional.get('comparator', 'equal')
        log.debug('eval_conditional %r %r %r', expected_value, comparator, current_value)
        return (comparator == 'equal') ^ (not expected_value == current_value)

    @staticmethod
    def from_script(data):
        return Mission(script=data)

    @staticmethod
    def load_all():
        log.error('LOAD ALL')
        session = app.Session()
        missions = session.query(MissionData).all()
        d = {}
        for m in missions:
            if m.script is not None:
                m = Mission(dbobj=m)
                d[m.id] = m
        return d

    def versions(self):
        with session_scope() as session:
            scripts = session.query(Script).filter(Script.mission_id == self.id).all()
            return [script.id for script in scripts]

    def get_version(self, version_id):
        with session_scope() as session:
            script = session.query(Script).filter(Script.mission_id == self.id)\
                .filter(Script.id == version_id).one_or_none()
            if script is not None:
                return script.script

    def set_version(self, version_id):
        with session_scope() as session:
            script = session.query(Script).filter(Script.mission_id == self.id)\
                .filter(Script.id == version_id).one_or_none()
            if script is None:
                return False

            dbobj = self._get_dbobj(session)
            dbobj.script = script
            self.version = dbobj.script.version
            session.commit()
            return True

    def runs(self):
        with session_scope() as session:
            runs = session.query(Run).filter(Run.mission_id == self.id).all()
            runs = [run.id for run in runs]
            return runs

    def get_run(self, run_id):
        with session_scope() as session:
            return self._get_events(session, run_id)
