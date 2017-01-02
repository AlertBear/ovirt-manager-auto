from . import config


def get_property_value(key):
    prop = config.engine.engine_config(
        "get",
        key,
        restart=False
    )
    return prop["results"][key]["value"]


def set_property_value(key, value):
    return config.engine.engine_config(
        "set",
        [
            "{0}={1} ".format(key, value),
            "--cver={0}".format(config.compatibility_version)
        ]
    )["results"]
