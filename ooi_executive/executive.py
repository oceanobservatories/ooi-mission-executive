from __future__ import print_function

import httplib
import logging
import time
from uuid import uuid4
import yaml

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from flask import request, jsonify, Response
from jsonschema import validate, ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from yaml.scanner import ScannerError

from ooi_executive import log_manager
from ooi_executive.jms_reader import JmsReader
from ooi_executive.mission import Mission
from ooi_executive import app
import mission_schema
from ooi_executive.shared import MissionNotFoundException

__author__ = 'petercable'


log_manager.setup()
log = logging.getLogger(__name__)


def setup():
    app.jms_reader = JmsReader()
    app.jms_reader.daemon = True
    app.jms_reader.start()
    app.scheduler = BackgroundScheduler()
    app.scheduler.configure(executors={'default': ThreadPoolExecutor(20)}, job_defaults={'max_instances': 1})
    app.scheduler.start()

    app.engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    app.Session = sessionmaker(bind=app.engine)

    from backing_store import create_db
    create_db(app)
    app.missions = Mission.load_all()


@app.errorhandler(MissionNotFoundException)
def handle_not_found_exception(error):
    response = {'message': 'not found', 'exception': error}
    status_code = 400
    if hasattr(error, 'status_code'):
        status_code = error.status_code
    return jsonify(response), status_code


@app.before_request
def log_request():
    request.start = time.time()
    request.id = uuid4()
    log.debug('REQUEST (%s): %r %r', request.id, request.url, request.data)


@app.after_request
def log_request_time(response):
    if hasattr(request, 'start') and hasattr(request, 'id'):
        elapsed = time.time() - request.start
        log.debug('REQUEST (%s) finished in %.4f secs', request.id, elapsed)
    return response


def check_mission_exists(mission_id):
    if mission_id not in app.missions:
        raise MissionNotFoundException('Cannot find mission: %r', mission_id)


@app.route('/missions', methods=['GET'])
def missions():
    state = request.args.get('state')
    if state == 'active':
        return jsonify({mid: app.missions[mid].small() for mid in app.missions if app.missions[mid].active})
    elif state == 'inactive':
        return jsonify({mid: app.missions[mid].small() for mid in app.missions if not app.missions[mid].active})
    # elif state == 'archived':
    # TODO: query database for archived missions
    #     return jsonify({mid: app.missions[mid].small() for mid in app.missions if not app.missions[mid].script})

    return jsonify({mid: app.missions[mid].small() for mid in app.missions})


@app.route('/missions', methods=['POST'])
def add_mission():
    mission = Mission(script=request.data)
    if mission is None:
        return Response(status=httplib.BAD_REQUEST)

    app.missions[mission.id] = mission
    return jsonify(mission.full())


@app.route('/missions/<int:mission_id>', methods=['GET'])
def get_mission(mission_id):
    check_mission_exists(mission_id)
    return jsonify(app.missions[mission_id].full())


@app.route('/missions/<int:mission_id>', methods=['DELETE'])
def del_mission(mission_id):
    check_mission_exists(mission_id)
    app.missions[mission_id].delete()
    del app.missions[mission_id]
    return Response()


@app.route('/missions/<int:mission_id>/activate')
def activate_mission(mission_id):
    check_mission_exists(mission_id)
    app.missions[mission_id].activate()
    return jsonify(app.missions[mission_id].full())


@app.route('/missions/<int:mission_id>/deactivate')
def deactivate_mission(mission_id):
    check_mission_exists(mission_id)
    app.missions[mission_id].deactivate()
    return jsonify(app.missions[mission_id].full())


@app.route('/missions/<int:mission_id>/versions')
def get_versions(mission_id):
    check_mission_exists(mission_id)
    versions = app.missions[mission_id].versions()
    return jsonify({'versions': versions})


@app.route('/missions/<int:mission_id>/versions/<int:version_id>')
def get_version(mission_id, version_id):
    check_mission_exists(mission_id)
    version = app.missions[mission_id].get_version(version_id)
    return jsonify({'version': version})


@app.route('/missions/<int:mission_id>/versions/<int:version_id>', methods=['PUT'])
def set_version(mission_id, version_id):
    check_mission_exists(mission_id)
    if app.missions[mission_id].set_version(version_id):
        return jsonify(app.missions[mission_id].full())
    else:
        return Response(status=httplib.BAD_REQUEST)


@app.route('/missions/<int:mission_id>/runs')
def get_runs(mission_id):
    check_mission_exists(mission_id)
    runs = app.missions[mission_id].runs()
    return jsonify({'runs': runs})


@app.route('/missions/<int:mission_id>/runs/<int:run_id>')
def get_mission_run(mission_id, run_id):
    check_mission_exists(mission_id)
    run = app.missions[mission_id].get_run(run_id)
    return jsonify({'run': run})


@app.route('/missions/schema')
def get_schema():
    return jsonify(mission_schema.Mission.get_schema(ordered=True))


@app.route('/missions/validate', methods=['POST'])
def validate_mission():
    mission = request.data
    if mission is None:
        return Response(status=httplib.BAD_REQUEST)

    try:
        mission_data = yaml.load(mission)
        validate(mission_data, mission_schema.Mission.get_schema())
    except (ValidationError, ScannerError) as e:
        log.error(e)
        return Response(status=httplib.BAD_REQUEST)
    return Response()


setup()
