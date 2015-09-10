import jsl


__author__ = 'petercable'


# ERROR HANDLING
class SimplePolicy(jsl.Document):
    type = jsl.StringField(enum=['abort', 'break', 'continue', 'ignore'], required=True)


class RetryPolicy(jsl.Document):
    type = jsl.StringField(enum=['retry'], required=True)
    count = jsl.IntField(required=True, description="Number of retries before aborting")
    backoff = jsl.IntField(required=True, description="Backoff before attempting again")


# SCHEDULING
class Cron(jsl.Document):
    year = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    month = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    day = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    week = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    day_of_week = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    hour = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    minute = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    second = jsl.OneOfField([jsl.StringField(), jsl.IntField()])
    start_date = jsl.DateTimeField()
    end_date = jsl.DateTimeField()


class DateTime(jsl.Document):
    run_date = jsl.DateTimeField(required=True)


class Event(jsl.Document):
    source = jsl.StringField(required=True)
    event = jsl.StringField(required=True)


# COMMANDS
class Command(jsl.Document):
    error_policy = jsl.OneOfField(
        [
            jsl.DocumentField(RetryPolicy),
            jsl.DocumentField(SimplePolicy),
        ])
    timeout = jsl.NumberField()


class Execute(Command):
    execute = jsl.StringField(required=True)
    command = jsl.StringField(required=True)
    kwargs = jsl.DictField()


class GetParameter(Command):
    get = jsl.StringField(required=True)
    parameter = jsl.StringField(required=True)


class SetParameter(Command):
    set = jsl.StringField(required=True)
    parameter = jsl.StringField(required=True)
    value = jsl.OneOfField(
        [
            jsl.StringField(),
            jsl.NumberField(),
        ],
        required=True
    )


class GetState(Command):
    get_state = jsl.StringField(required=True)


class Discover(Command):
    discover = jsl.StringField(required=True)


class Reset(Command):
    reset = jsl.StringField(required=True)


class Sleep(Command):
    sleep = jsl.NumberField(required=True)


class Connect(Command):
    connect = jsl.StringField(required=True)


class Disconnect(Command):
    disconnect = jsl.StringField(required=True)


class SetInitParams(Command):
    set_init_params = jsl.StringField(required=True)
    config = jsl.DictField()


class Configure(Command):
    configure = jsl.StringField(required=True)
    config = jsl.DictField()


# CONTROL

class Condition(jsl.Document):
    variable = jsl.StringField(required=True)
    value = jsl.OneOfField([jsl.StringField(), jsl.NumberField()], required=True)
    comparator = jsl.StringField(enum=['equal', 'not_equal'])


# BLOCK
class RunBlock(jsl.Document):
    block_name = jsl.StringField(required=True)
    condition = jsl.DocumentField(Condition)
    loop = jsl.IntField()


class Block(jsl.Document):
    label = jsl.StringField()
    sequence = jsl.ArrayField(
        jsl.OneOfField(
            [
                jsl.DocumentField(Execute),
                jsl.DocumentField(GetParameter),
                jsl.DocumentField(SetParameter),
                jsl.DocumentField(GetState),
                jsl.DocumentField(Discover),
                jsl.DocumentField(Reset),
                jsl.DocumentField(Sleep),
                jsl.DocumentField(Connect),
                jsl.DocumentField(Disconnect),
                jsl.DocumentField(SetInitParams),
                jsl.DocumentField(Configure),
                jsl.DocumentField(RunBlock),
                jsl.DocumentField(jsl.RECURSIVE_REFERENCE_CONSTANT),
            ]
        ),
        required=True
    )
    condition = jsl.DocumentField(Condition)
    loop = jsl.IntField()


# MISSION
class Mission(jsl.Document):
    name = jsl.StringField(required=True)
    desc = jsl.StringField(required=True)
    version = jsl.StringField(required=True)
    drivers = jsl.ArrayField(jsl.StringField(), required=True)
    error_policy = jsl.OneOfField(
        [
            jsl.DocumentField(RetryPolicy),
            jsl.DocumentField(SimplePolicy),
        ])
    schedule = jsl.OneOfField(
        [
            jsl.DocumentField(Cron),
            jsl.DocumentField(DateTime),
            jsl.DocumentField(Event),
        ])
    debug = jsl.BooleanField()
    verbose = jsl.BooleanField()
    blocks = jsl.ArrayField(jsl.DocumentField(Block), required=True)
