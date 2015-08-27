"""
This file provides utilities to manage ADs using AAA.
(Authentication, Authorization and Accounting)

You can find description of feature here:
http://www.ovirt.org/Features/AAA#Mapping
"""

import logging
import os
import test_utils

from art.test_handler import find_test_file

LOGGER = logging.getLogger(__name__)


def copy_extension_file(host, ext_file, target_file, chown='ovirt'):
    """
    :param host: host where copy file to
    :type host: instance of resources.Host
    :param ext_file: file to copy
    :type ext_file: str
    :param target_file: file to create
    :type target_file: str
    :param chown: permission to set
    :type chown: str / int
    """
    with host.executor().session() as ss:
        with open(ext_file) as fhs:
            with ss.open_file(target_file, 'w') as fhd:
                fhd.write(fhs.read())
        if chown:
            chown_cmd = [
                'chown', '%s:%s' % (chown, chown), target_file,
            ]
            res = ss.run_cmd(chown_cmd)
            assert not res[0], res[1]
    LOGGER.info('Configuration "%s" has been copied.', ext_file)


class Extension(object):
    module_name = ''
    INTERVAL = 5
    TIMEOUT = 60
    CONFIG_DIRECTORY = 'tests/ldap/'
    EXTENSIONS_DIR = '/etc/ovirt-engine/extensions.d/'

    def __init__(self, host, engine):
        """
        :param host: host where engine is running
        :type host: instance of resources.Host
        :param engine: the engine
        :type engine: instance of resources.Engine
        """
        self.host = host
        self.engine = engine
        self.module_dir = find_test_file(
            '%s%s' % (self.CONFIG_DIRECTORY, self.module_name)
        )

    def __get_confs(self):
        """ get configuration from directory module_name """
        return os.listdir(self.module_dir)

    def add(self, apply=True):
        """
        :param apply: if true ovirt engine will be restarted
        :type apply: boolean
        """
        LOGGER.info(self.module_name)
        for conf in self.__get_confs():
            ext_file = os.path.join(self.module_dir, conf)
            target_file = os.path.join(self.EXTENSIONS_DIR, conf)
            try:
                copy_extension_file(self.host, ext_file, target_file)
            except AssertionError as e:
                LOGGER.error(
                    'Configuration "%s" has NOT been copied. Tests with '
                    'this configuration should be skipped. %s', conf, e
                )
        if apply:
            self.apply()

    def apply(self):
        test_utils.restart_engine(self.engine, self.INTERVAL, self.TIMEOUT)

    def remove(self, apply=True):
        with self.host.executor().session() as ss:
            for conf in self.__get_confs():
                ss.run_cmd([
                    'rm', '-f', os.path.join(self.EXTENSIONS_DIR, conf)
                ])
        if apply:
            self.apply()


class ADTLV(Extension):
    module_name = 'ad_tlv'


class BRQOpenLDAP(Extension):
    module_name = 'brq_openldap'
