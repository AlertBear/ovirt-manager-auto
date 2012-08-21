
from art.core_api import ActionSet


def generate_ds(conf):
    pass# TODO: generate DS for jasper


class JasperActionSet(ActionSet):
    MODULES = [
            'art.jasper_api.tests_lib.reports',
            ]


