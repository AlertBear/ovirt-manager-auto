
from art.core_api import ActionSet

class GlusterActionSet(ActionSet):
    MODULES = [
            'art.gluster_api.tests_lib.volumes',
            ]


