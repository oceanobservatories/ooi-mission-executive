from json import JSONEncoder
from flask import Response

__author__ = 'petercable'


class MissionNotFoundException(Exception):
    status_code = 400


class PolicyException(Exception):
    pass


class CommandArgumentException(Exception):
    pass


class LockException(Exception):
    pass


class TimeoutException(Exception):
    pass


class InstrumentException(Exception):
    pass


class DuplicateScriptException(Exception):
    pass


class MyEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, 'to_dict'):
            return o.to_dict()
        return super(MyEncoder, self).default(o)


class Enumeration(object):
    ALL = 'ALL'
    _keys = None
    _values = None
    _dict = None

    def __init__(self):
        self._keys = tuple(attr for attr in dir(self) if all((not callable(getattr(self, attr)),
                                                              not attr.startswith('_'),
                                                              not attr == 'ALL')))
        self._values = tuple(getattr(self, attr) for attr in self._keys)
        self._dict = {attr: getattr(self, attr) for attr in self._keys}

    def values(self):
        """Return the values of this enum."""
        return self._values

    def dict(self):
        """Return a dict representation of this enum."""
        return self._dict

    def keys(self):
        """Return the keys of this enum"""
        return self._keys

    def get_key(self, value, default=None):
        for key in self._dict:
            if self._dict == value:
                return key
        return default

    def __iter__(self):
        return self._values.__iter__

    def __contains__(self, item):
        return item in self._values


class _Tags(Enumeration):
    MISSION = 'mission'
    PREMISSION = 'premission'
    POSTMISSION = 'postmission'
    STOPPING = 'stopping'
    SCHEDULE = 'schedule'
    CRON = 'cron'
    INSTRUMENT = 'drivers'
    PLATFORM = 'platform'
    DATETIME = 'datetime'


class _LocalCommands(Enumeration):
    SLEEP = 'sleep'
    WAIT = 'wait'


class _RemoteCommands(Enumeration):
    EXECUTE = 'execute_resource'
    DISCONNECT = 'disconnect'
    PING = 'ping'
    DISCOVER = 'discover'
    GET_STATE = 'get_state'
    GET_RESOURCE = 'get_resource'
    SET_RESOURCE = 'set_resource'


class Keywords(Enumeration):
    # CONTROL FLOW
    IF = 'if'
    ELSE = 'else'
    EQUAL = 'equal'
    NOT_EQUAL = 'not_equal'
    BLOCK = 'block'
    WHILE = 'while'
    ABORT = 'abort'
    CLEANUP = 'cleanup'

    # EXECUTIVE COMMANDS
    SLEEP = 'sleep'

    # DRIVER COMMANDS
    EXECUTE = 'execute'
    PING = 'ping'
    RESET = 'reset'
    GET_STATE = 'get_state'
    DISCOVER = 'discover'
    GET_PARAM = 'get'
    SET_PARAM = 'set'

    # ARGS
    TARGET = 'target'
    ARGS = 'args'
    KWARGS = 'kwargs'
    COUNT = 'count'
    VAR = 'var'
    VALUE = 'value'

Tags = _Tags()
LocalCommands = _LocalCommands()
RemoteCommands = _RemoteCommands()
