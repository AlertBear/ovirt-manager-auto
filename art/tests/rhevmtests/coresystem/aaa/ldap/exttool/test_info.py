"""
This module tests 'Extension tester tool'(ovirt-engine-extensions-tool) and
its info module. The info module can be used to see information about
specific extension.

polarion:
  https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
  System/Extension tester tool
"""

import logging
import pytest

from rhevmtests.coresystem.helpers import EngineCLI
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow

from rhevmtests.coresystem.aaa.ldap import config

logger = logging.getLogger('test_info')


@tier1
class TestExttoolInfo(TestCase):
    """ Test info module of ovirt-engine-extensions-tool """
    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        testflow.setup("Setting up class %s", cls.__name__)
        cls.info_cli = EngineCLI(
            tool=config.TOOL,
            log_level='FINEST',
            session=config.ENGINE_HOST.executor().session(),
        ).setup_module(
            module='info',
            output='stdout',
        )

    @polarion('RHEVM3-14041')
    def test_list_extensions(self):
        """ test list of existing extensions """

        testflow.step("Listing extensions")
        rc, out = self.info_cli.run('list-extensions', format='{instance}')
        extensions = out.split('\n')[:-1]
        logger.info('Enabled extensions: %s', extensions)
        assert rc, 'Failed to run info list-extensions'

        testflow.step("Checking for internal extensions")
        for extension in ['internal-authz', 'internal-authn']:
            assert extension in extensions, '%s was not found' % extension

    @polarion('RHEVM3-14042')
    def test_configuration(self):
        """ test of listing configuration of authz/authn """

        testflow.step("Listing configuration of authz/authn")
        for extension in ['internal-authz', 'internal-authn']:
            rc, out = self.info_cli.run(
                'configuration',
                extension_name=extension
            )
            logger.info('Extension configuration: %s', out)

            assert rc, 'Failed to run info configuration'
            assert 'aaa.jdbc' in out, 'Extension not found in conf'

    @polarion('RHEVM3-14043')
    def test_context(self):
        """ test of listing context of authz/authn """

        testflow.step("Listing context of authz/authn")
        for extension in ['internal-authz', 'internal-authn']:
            rc, out = self.info_cli.run('context', extension_name=extension)
            logger.info('Extension context : %s', out)

            assert rc, 'Failed to run info context'
            assert extension in out, (
                'Extension "%s" was not found in context' % extension
            )
