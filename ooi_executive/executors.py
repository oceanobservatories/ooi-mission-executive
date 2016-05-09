import json
import requests
import logging
from shared import InstrumentException, TimeoutException, CommandArgumentException, LockException

__author__ = 'petercable'

log = logging.getLogger(__name__)


class RestResponse(object):
    def __init__(self, response, timeout_ok=False):
        log.debug('Received response: %d %r', response.status_code, response.content)
        self.status_code = response.status_code
        if response.content == '' and not timeout_ok:
            raise TimeoutException
        try:
            data = response.json()
            self.cmd = data.get('cmd')
            self.value = data.get('value')
            self.time = data.get('time')
            self.type = data.get('type')
        except (ValueError, AttributeError):
            self.cmd = None
            self.value = None
            self.time = None
            self.type = None

        if self.type == 'DRIVER_ASYNC_EVENT_ERROR':
            raise InstrumentException(repr(self))

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        return repr(self.to_dict())

    def to_dict(self):
        return {k: self.__dict__[k] for k in self.__dict__ if not k.startswith('_')}


class Executor(object):
    """
    The base executor class contains the argument parsing and dispatch code
    for scripted events. The actual execution is defined in the child classes.
    """
    def __init__(self, mission_id, default_timeout):
        self.mission_id = mission_id
        self.default_timeout = default_timeout

    def command(self, step):
        if 'execute' in step:
            return self._execute_resource(step)
        if 'reset' in step:
            return self._reset(step)
        if 'ping' in step:
            return self._ping(step)
        if 'discover' in step:
            return self._discover(step)
        if 'get_state' in step:
            return self._get_state(step)
        if 'get' in step:
            return self._get_resource(step)
        if 'set' in step:
            return self._set_resource(step)
        if 'disconnect' in step:
            return self._disconnect(step)
        if 'connect' in step:
            return self._connect(step)
        if 'set_init_params' in step:
            return self._set_init_params(step)
        if 'configure' in step:
            return self._configure(step)

        log.error('UNKNOWN STEP: %r', step)

    def _extract_and_validate(self, step):
        target = step.get('target')
        args = step.get('args', [])
        kwargs = step.get('kwargs', {})
        timeout = step.get('timeout', self.default_timeout)
        if all((isinstance(target, basestring),
                isinstance(args, basestring) or isinstance(args, (list, tuple)),
                isinstance(kwargs, dict),
                isinstance(timeout, (float, int)))):
            return target, args, kwargs, timeout
        raise CommandArgumentException

    def _execute_resource(self, step):
        target = step.get('execute')
        command = step.get('command')
        kwargs = step.get('kwargs', {})
        timeout = step.get('timeout', self.default_timeout)
        return self.execute_resource(target, command, kwargs, timeout)

    def execute_resource(self, target, command, kwargs, timeout):
        raise NotImplemented

    def _reset(self, step):
        target = step.get('reset')
        timeout = step.get('timeout', self.default_timeout)
        return self.reset(target, timeout)

    def reset(self, target, timeout):
        raise NotImplemented

    def _ping(self, step):
        target = step.get('ping')
        timeout = step.get('timeout', self.default_timeout)
        return self.ping(target, timeout)

    def ping(self, target, timeout):
        raise NotImplemented

    def _discover(self, step):
        target = step.get('discover')
        timeout = step.get('timeout', self.default_timeout)
        return self.discover(target, timeout)

    def discover(self, target, timeout):
        raise NotImplemented

    def _get_state(self, step):
        target = step.get('get_state')
        timeout = step.get('timeout', self.default_timeout)
        return self.get_state(target, timeout)

    def get_state(self, target, timeout):
        raise NotImplemented

    def _get_resource(self, step):
        target = step.get('get')
        parameter = step.get('parameter')
        timeout = step.get('timeout', self.default_timeout)
        return self.get_resource(target, parameter, timeout)

    def get_resource(self, target, parameter, timeout):
        raise NotImplemented

    def _set_resource(self, step):
        target = step.get('set')
        parameter = step.get('parameter')
        value = step.get('value')
        timeout = step.get('timeout', self.default_timeout)
        kwargs = {parameter: value}
        return self.set_resource(target, kwargs, timeout)

    def set_resource(self, target, kwargs, timeout):
        raise NotImplemented

    def _disconnect(self, step):
        target = step.get('disconnect')
        timeout = step.get('timeout', self.default_timeout)
        return self.disconnect(target, timeout)

    def disconnect(self, target, timeout):
        raise NotImplemented

    def _connect(self, step):
        target = step.get('connect')
        timeout = step.get('timeout', self.default_timeout)
        return self.connect(target, timeout)

    def connect(self, target, timeout):
        raise NotImplemented

    def _set_init_params(self, step):
        target = step.get('set_init_params')
        config = step.get('config')
        timeout = step.get('timeout', self.default_timeout)
        return self.set_init_params(target, config, timeout)

    def set_init_params(self, target, config, timeout):
        raise NotImplemented

    def _configure(self, step):
        target = step.get('configure')
        config = step.get('config')
        timeout = step.get('timeout', self.default_timeout)
        return self.configure(target, config, timeout)

    def configure(self, target, config, timeout):
        raise NotImplemented

    def lock(self, instruments):
        raise NotImplemented

    def unlock(self, instruments):
        raise NotImplemented


class RestExecutor(Executor):
    def __init__(self, mission_id, rest_host, rest_port, base_url='instrument/api', timeout=30000):
        super(RestExecutor, self).__init__(mission_id, timeout)
        self.base_url = 'http://%s:%d/%s' % (rest_host, rest_port, base_url)

    def _url(self, target, name):
        return '/'.join((self.base_url, target, name))

    def execute_resource(self, target, command, kwargs, timeout):
        form = {'command': json.dumps(command), 'kwargs': json.dumps(kwargs),
                'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'execute'), data=form))

    def reset(self, target, timeout):
        """
        Reset the target instrument driver.
        We expect a TimeoutException on reset.
        :param target:
        :param timeout:
        :return:
        """
        form = {'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'shutdown'), data=form), timeout_ok=True)

    def ping(self, target, timeout):
        form = {'timeout': timeout}
        return RestResponse(requests.post(self._url(target, 'ping'), data=form))

    def discover(self, target, timeout):
        form = {'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'discover'), data=form))

    def get_state(self, target, timeout):
        form = {'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.get(self._url(target, 'state'), data=form))

    def get_resource(self, target, parameter, timeout):
        form = {'timeout': timeout, 'resource': json.dumps(parameter), 'key': self.mission_id}
        return RestResponse(requests.get(self._url(target, 'resource'), data=form))

    def set_resource(self, target, kwargs, timeout):
        form = {'timeout': timeout, 'resource': json.dumps(kwargs), 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'resource'), data=form))

    def disconnect(self, target, timeout):
        form = {'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'disconnect'), data=form))

    def connect(self, target, timeout):
        form = {'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'connect'), data=form))

    def set_init_params(self, target, config, timeout):
        form = {'config': json.dumps(config), 'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'initparams'), data=form))

    def configure(self, target, config, timeout):
        form = {'config': json.dumps(config), 'timeout': timeout, 'key': self.mission_id}
        return RestResponse(requests.post(self._url(target, 'configure'), data=form))

    def lock(self, instruments):
        for instrument in instruments:
            form = {'key': self.mission_id}
            response = requests.post(self._url(instrument, 'lock'), data=form)
            if response.status_code == 409:
                raise LockException

    def unlock(self, instruments):
        for instrument in instruments:
            locker = requests.get(self._url(instrument, 'lock')).json().get('locked-by')
            if locker == self.mission_id:
                log.info('Unlocking %s', instrument)
                requests.post(self._url(instrument, 'unlock'))
            else:
                log.warn('Unable to unlock %s, lock held by %r', instrument, locker)
