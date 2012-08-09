#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from art.test_handler.plmanagement import Component, implements, get_logger
from art.test_handler.plmanagement.interfaces.application import IConfigurable
from art.test_handler.plmanagement.interfaces.tests_listener import ITestCaseHandler
from art.test_handler.plmanagement.interfaces.packaging import IPackaging

logger = get_logger('validate_events')
CORRELATION_ID = 'Correlation-Id'
EVENTS_OPTION = 'VALIDATE_EVENTS'

class ValidateEvents(Component):
    """
    Plugin provides validation of events by correlation id.
    """
    implements(IConfigurable, ITestCaseHandler, IPackaging)
    name = "Validate_Events"

    def __init__(self):
        super(ValidateEvents, self).__init__()

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--validate-events', action='store_true', \
                dest='validate_events', help="enable plugin", default=False)

    @classmethod
    def is_enabled(cls, params, conf):
        conf_events = \
            conf.get(EVENTS_OPTION, {}).get('enabled', 'false').lower()== 'true'
        return conf_events or params.validate_events


    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        from art.rhevm_api.utils.test_utils import get_api
        self.event_api = get_api('event', 'events')
        logger.info("Plugin for event validations is enabled.")


    def pre_test_case(self, t):
       pass

    def post_test_case(self, t):

        if not t.conf:
            return

        from art.rhevm_api.utils.test_utils import searchForObj

        conf_val = re.sub(r'"|\'|\s', '', t.conf)
        corr_id = re.search(CORRELATION_ID + ':(\d+)', conf_val, re.I)

        if not corr_id:
            return

        if t.positive:
            exp_events_count = [1,2,4]
        else:
            exp_events_count = 0

        if t.status ==  t.TEST_STATUS_PASSED and \
        not searchForObj(self.event_api, 'correlation_id', corr_id.group(1),
        'correlation_id', expected_count = exp_events_count):
            t.status = t.TEST_STATUS_FAILED


    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = 'validate-events'
        params['version'] = '1.0'
        params['author'] = 'Elena Dolinin'
        params['author_email'] = 'edolinin@redhat.com'
        params['description'] = cls.__doc__.strip().replace('\n', ' ')
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.validate_events_plugin']

