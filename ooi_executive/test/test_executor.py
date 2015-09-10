import json
import unittest
import httpretty
import time
from ooi_executive import log_manager
from ooi_executive.executors import RestExecutor

__author__ = 'petercable'

log_manager.setup()


class RestExecutorUnitTest(unittest.TestCase):
    def setUp(self):
        self.executor = RestExecutor('test', 'test', 12345)
        self.response = {'cmd': 'cmd', 'type': 'type', 'value': 'value', 'time': time.time()}
        self.response_json = json.dumps(self.response)

    def assert_response(self, response):
        self.assertEqual(response.cmd, self.response.get('cmd'))
        self.assertEqual(response.type, self.response.get('type'))
        self.assertEqual(response.value, self.response.get('value'))
        self.assertEqual(response.time, self.response.get('time'))
        self.assertEqual(response.status_code, 200)

    def test_url(self):
        expected = 'http://test:12345/instrument/api/target/name'
        returned = self.executor._url('target', 'name')
        self.assertEqual(expected, returned)

    @httpretty.activate
    def test_execute_resource(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'execute'), body=self.response_json)
        response = self.executor.execute_resource('target', 'test', {'key1': 'value1'}, timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_reset(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'shutdown'), body=self.response_json)
        response = self.executor.reset('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_ping(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'ping'), body=self.response_json)
        response = self.executor.ping('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_discover(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'discover'), body=self.response_json)
        response = self.executor.discover('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_get_state(self):
        httpretty.register_uri(httpretty.GET, self.executor._url('target', 'state'), body=self.response_json)
        response = self.executor.get_state('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_get_resource(self):
        httpretty.register_uri(httpretty.GET, self.executor._url('target', 'resource'), body=self.response_json)
        response = self.executor.get_resource('target', 'parameter', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_set_resource(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'resource'), body=self.response_json)
        response = self.executor.set_resource('target', {}, timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_disconnect(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'disconnect'), body=self.response_json)
        response = self.executor.disconnect('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_connect(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'connect'), body=self.response_json)
        response = self.executor.connect('target', timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_set_init_params(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'initparams'), body=self.response_json)
        response = self.executor.set_init_params('target', {}, timeout=60000)
        self.assert_response(response)

    @httpretty.activate
    def test_lock(self):
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'lock'), body=self.response_json)
        self.executor.lock(['target'])

    @httpretty.activate
    def test_unlock(self):
        httpretty.register_uri(httpretty.GET, self.executor._url('target', 'lock'), body='"test"')
        httpretty.register_uri(httpretty.POST, self.executor._url('target', 'unlock'), body=self.response_json)
        self.executor.unlock(['target'])

