import unittest

from jsonschema import validate, ValidationError

from ooi_executive.mission_schema import \
    RetryPolicy, Cron, DateTime, Event, \
    Mission, Execute, GetParameter, SetParameter, \
    GetState, Discover, Reset, SimplePolicy, Block, SetInitParams, Configure

__author__ = 'petercable'


class SchemaUnitTest(unittest.TestCase):
    # error policies
    def test_retry_policy(self):
        d = {'type': 'retry',
             'count': 5,
             'backoff': 5}
        schema = RetryPolicy.get_schema()
        validate(d, schema)

    def test_simple_policies(self):
        schema = SimplePolicy.get_schema()

        d = {'type': 'abort'}
        validate(d, schema)

        d = {'type': 'break'}
        validate(d, schema)

        d = {'type': 'continue'}
        validate(d, schema)

        d = {'type': 'ignore'}
        validate(d, schema)

    def test_bad_policy(self):
        schema = SimplePolicy.get_schema()

        d = {'type': 'fail whale'}
        with self.assertRaises(ValidationError):
            validate(d, schema)

    # schedules
    def test_cron_schedule(self):
        d = {'year': 2015,
             'month': '*',
             'day': '1,5,10,15',
             'day_of_week': '*',
             'hour': 0,
             'minute': '*',
             'second': 1,
             'start_date': '2015-11-06 16:30:05',
             'end_date': '2016-11-06 16:30:05',
             }
        schema = Cron.get_schema()
        validate(d, schema)

    def test_datetime_schedule(self):
        d = {'run_date': '2015-11-06 16:30:05'}
        schema = DateTime.get_schema()
        validate(d, schema)

    def test_event_schedule(self):
        d = {'source': 'OMS',
             'event': 'NO IDEA'}
        schema = Event.get_schema()
        validate(d, schema)

    def test_execute(self):
        d = {'execute': 'refdes',
             'command': 'DRIVER_EVENT_START_AUTOSAMPLE',
             'kwargs': {},
             'error_policy': {'type': 'abort'},
             }
        schema = Execute.get_schema()
        validate(d, schema)

    def test_get_param(self):
        d = {'get': 'refdes',
             'parameter': 'param1',
             'error_policy': {'type': 'abort'},
             }
        schema = GetParameter.get_schema()
        validate(d, schema)

    def test_set_param(self):
        d = {'set': 'refdes',
             'parameter': 'param1',
             'value': 'value1',
             'error_policy': {'type': 'abort'},
             }
        schema = SetParameter.get_schema()
        validate(d, schema)

    def test_get_state(self):
        d = {'get_state': 'refdes',
             'error_policy': {'type': 'abort'},
             }
        schema = GetState.get_schema()
        validate(d, schema)

    def test_discover(self):
        d = {'discover': 'refdes',
             'error_policy': {'type': 'abort'},
             }
        schema = Discover.get_schema()
        validate(d, schema)

    def test_reset(self):
        d = {'reset': 'refdes',
             'error_policy': {'type': 'abort'},
             }
        schema = Reset.get_schema()
        validate(d, schema)

    def test_init_params(self):
        d = {'set_init_params': 'refdes',
             'config': {}}
        schema = SetInitParams.get_schema()
        validate(d, schema)

    def test_configure(self):
        d = {'configure': 'refdes',
             'config': {'oms_uri': 'http://oms',
                        'driver_config_file': {
                            'node_cfg_file': 'mi/platform/rsn/node_config_files/LPJBox_LJ0CI.yml'
                        }, 'node_id': 'LPJBox_CI_Ben_Hall'}}
        schema = Configure.get_schema()
        validate(d, schema)

    def test_block(self):
        d = {'label': 'block',
             'sequence': [
                 {'execute': 'refdes', 'command': 'start_autosample'},
                 {'sleep': 2.5},
                 {'set': 'refdes', 'parameter': 'p1', 'value': 5},
                 {'block_name': 'capture'},
             ]
             }
        schema = Block.get_schema()
        validate(d, schema)

    # mission
    def test_mission_schema(self):
        d = {
            'name': 'HydrateRidgeSummit_Camera_Standard',
            'desc': 'Uses the Digital Still Camera at Hydrate Ridge to '
                    'take pictures on a scheduled time according to the OOI Sampling Policy',
            'version': '1-00',
            'drivers': ['RS01SUM1-MJ01B-05-CAMDSB103', 'RS01SUM1-MJ01B'],
            'schedule': {'hour': '0,6,12,18'},
            'error_policy': {'type': 'abort'},
            'debug': True,
            'blocks': [
                {
                    'label': 'mission',
                    'sequence': [
                        {'execute': 'RS01SUM1-MJ01B',
                         'command': 'RSN_PLATFORM_DRIVER_TURN_ON_PORT',
                         'kwargs': {'port_id': 'J05-IP1', 'src': 'HydrateRidgeSummit_Camera_Standard'}},
                        {'reset': 'RS01SUM1-MJ01B-05-CAMDSB103'},
                        {'sleep': 5},
                        {'discover': 'RS01SUM1-MJ01B-05-CAMDSB103'},
                        {'set': 'RS01SUM1-MJ01B-05-CAMDSB103', 'parameter': 'PRESET_NUMBER', 'value': 1},
                        {'block_name': 'capture'},
                        {'set': 'RS01SUM1-MJ01B-05-CAMDSB103', 'parameter': 'PRESET_NUMBER', 'value': 2},
                        {'block_name': 'capture'},
                        {'set': 'RS01SUM1-MJ01B-05-CAMDSB103', 'parameter': 'PRESET_NUMBER', 'value': 3},
                        {'block_name': 'capture'},
                        {'execute': 'RS01SUM1-MJ01B',
                         'command': 'RSN_PLATFORM_DRIVER_TURN_OFF_PORT',
                         'kwargs': {'port_id': 'J05-IP1', 'src': 'HydrateRidgeSummit_Camera_Standard'}},
                        {'reset': 'RS01SUM1-MJ01B-05-CAMDSB103'},
                        {'configure': 'refdes',
                         'config': {'oms_uri': 'http://oms',
                                    'driver_config_file': {
                                        'node_cfg_file': 'mi/platform/rsn/node_config_files/LPJBox_LJ0CI.yml'
                                    }, 'node_id': 'LPJBox_CI_Ben_Hall'}}
                    ]
                },
                {'label': 'capture',
                 'sequence': [
                     {'execute': 'RS01SUM1-MJ01B-05-CAMDSB103', 'command': 'DRIVER_EVENT_START_AUTOSAMPLE'},
                     {'sleep': 600},
                     {'execute': 'RS01SUM1-MJ01B-05-CAMDSB103', 'command': 'DRIVER_EVENT_STOP_AUTOSAMPLE'},
                 ]},
            ],
        }
        schema = Mission.get_schema()
        validate(d, schema)
