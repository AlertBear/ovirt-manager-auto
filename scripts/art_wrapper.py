#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
ART wrapper
"""

from collections import defaultdict
from art.core_api.external_api import TestRunnerWrapper
import art.test_handler.settings as settings

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


def art(path_to_config):
    """
    ART wrapper
    :param path_to_config: Path to config file
    :type path_to_config: str
    """
    TestRunnerWrapper(
        ip=VDC, scheme="https", port=443, user=USER,
        user_domain=DOMAIN, password=PASS,
        headers={"Prefer": "persistent-auth"}, logger_init=False
    )
    settings.opts["standalone"] = True
    settings.opts["data_struct_mod"] = DS_MOD
    settings.opts["engine"] = "java"
    settings.opts["persistent_auth"] = True
    settings.opts["confSpec"] = "conf/specs/main.spec"
    settings.readTestRunOpts(
        path_to_config, [
            "DEFAULT.PRODUCT=rhevm",
            "DEFAULT.VERSION=3.5",
        ]
    )
    settings.opts["host"] = VDC
    ds_conf = settings.opts.setdefault("GENERATE_DS", {})
    ds_conf.setdefault("encoding", "utf8")
    ds_conf.setdefault("enabled", False)
    settings.opts["user"] = USER
    settings.opts["password"] = PASS
    settings.opts["user_domain"] = DOMAIN
    rhevm_api.generate_ds(rhevm_api.opts)
    settings.ART_CONFIG["PARAMETERS"]["vds"] = ["1.1.1.1"] * 4
    settings.ART_CONFIG["RUN"]["engine"] = VDC
    settings.ART_CONFIG["PARAMETERS"]["disk_size"] = "1000"
