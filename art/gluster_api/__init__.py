
from art.core_api import ActionSet


def generate_ds(conf):
    pass# TODO: generate DS for gluster


class GlusterActionSet(ActionSet):
    MODULES = [
            'art.gluster_api.tests_lib.volumes',
            ]


