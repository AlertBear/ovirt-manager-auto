#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from test_handler.plmanagement import logger as root_logger
from test_handler.plmanagement import Component, implements
from test_handler.plmanagement.interfaces.application import IConfigurable
from test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler


logger = logging.getLogger(root_logger.name+'.vital_disable')


class NoVitalError(Exception):
    pass


class VitalDisable(Component):
    """
    Plugin provides option to disable vital tests.
    """
    implements(IConfigurable, ITestCaseHandler)
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




