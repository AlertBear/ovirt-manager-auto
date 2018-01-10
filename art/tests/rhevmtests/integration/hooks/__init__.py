from . import config


def get_property_value(key):
    prop = config.ENGINE.engine_config(
        "get",
        key,
        restart=False
    )
    return prop["results"][key]["value"]


def set_property_value(key, value):
    return config.ENGINE.engine_config(
        "set",
        [
            "{0}={1} ".format(key, value),
            "--cver={0}".format(config.COMP_VERSION)
        ]
    )["results"]
