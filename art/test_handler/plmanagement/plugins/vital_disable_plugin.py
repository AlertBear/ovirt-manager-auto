#!/usr/bin/env python
# -*- coding: utf-8 -*-

from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging


logger = get_logger('vital_disable')


class NoVitalError(Exception):
    pass


class VitalDisable(Component):
    """
    Plugin provides option to disable vital tests.
    """
    implements(IConfigurable, ITestCaseHandler, IPackaging)
    name = "Vital_Disable"

    def __init__(self):
        super(VitalDisable, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--vital-disable', action='store_true', \
                dest='vital_disabled', help="enable plugin", default=False)

    @classmethod
    def is_enabled(cls, params, conf):
        return conf.get('vital_disabled', False) or params.vital_disabled


    def configure(self, params, conf):
        if self.is_enabled(params, conf):
            logger.info("Will disable all vital tests.")


    def pre_test_case(self, t):
        try:
            t.test_vital = "false"
        except AttributeError:
            raise NoVitalError(t.test_name)


    def post_test_case(self, t):
        pass

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'vital-disable'
        params['version'] = '1.0'
        params['author'] = 'Elena Dolinin'
        params['author_email'] = 'edolinin@redhat.com'
        params['description'] = cls.__doc__.strip().replace('\n', ' ')
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.vital_disable_plugin']

