#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
ART wrapper
"""

from collections import defaultdict
from art.test_handler import settings

GIT = False
DS_MOD = "rhevm_api.data_struct.data_structures"

try:
    import rhevm_api
except ImportError:
    GIT = True
    DS_MOD = "art.%s" % DS_MOD
    import art.rhevm_api as rhevm_api

USER = "jenkins"
PASS = "jenkins"
DOMAIN = "qa.lab.tlv.redhat.com"
VDC = "rhevm-3.qa.lab.tlv.redhat.com"


class FakeDict(defaultdict):
    """
    Class to return fake values for non exist values in dict
    """
    def as_list(self, key):
        """
        Return fake value as list
        :param key: Dict key
        :type key: str
        :returns: Fake key list
        :rtype: list
        """
        value = [key]
        if isinstance(value, list):
            return value * 10
        elif isinstance(value, basestring):
            return value.split(",")
        return [value] * 10

    def as_int(self, key):
        """
        Return fake value as int
        :param key: Dict key
        :type key: str
        :returns: Fake int key
        :rtype: int
        """
        return int(key)

    def as_bool(self, key):
        """
        Return fake bool key
        :param key: Dict key
        :type key: str
        :return: Fake bool key
        :rtype: bool
        """
        return True


def art(path_to_defaults, template_yaml):
    """
    ART wrapper

    Args:
        path_to_defaults (str): Path to defaults.yaml
        template_yaml (str): Path to template.yaml
    """
    settings.create_runtime_config(
        path_to_defaults, [
            "RUN.golden_environment={ge_yaml}".format(ge_yaml=template_yaml),
        ]
    )
    settings.ART_CONFIG["REST_CONNECTION"]["password"] = PASS
    settings.ART_CONFIG["REST_CONNECTION"]["user"] = USER
    settings.ART_CONFIG["REST_CONNECTION"]["host"] = VDC
    settings.ART_CONFIG["REST_CONNECTION"]["user_domain"] = DOMAIN
    settings.ART_CONFIG["REST_CONNECTION"]["uri"] = (
        "https://%s:443/ovirt-engine/api/" % VDC
    )

    rhevm_api.generate_ds(settings.ART_CONFIG)


if __name__ == "__main__":
    root = None  # Path to root git folder
    art(
        path_to_defaults="%s/rhevm-art/art/conf/defaults.yaml" % root,
        template_yaml="%s/rhevm-jenkins/qe/GE-yamls/template.yaml" % root
    )
