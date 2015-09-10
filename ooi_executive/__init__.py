import os
from flask import Flask
from ooi_executive.shared import MyEncoder

__author__ = 'petercable'

CONFIG_ENV_VAR = 'MSNEXEC_CONFIG'

app = Flask(__name__)
app.json_encoder = MyEncoder
app.config.from_object('ooi_executive.default_config')
if CONFIG_ENV_VAR in os.environ:
    app.config.from_envvar(CONFIG_ENV_VAR)
