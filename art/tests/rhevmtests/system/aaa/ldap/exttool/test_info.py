"""
This module tests 'Extension tester tool'(ovirt-engine-extensions-tool) and
its info module. The info module can be used to see information about
specific extension.

polarion:
  https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
  System/Extension tester tool
"""
__test__ = True

import logging

from art.rhevm_api.utils.enginecli import EngineCLI
from art.test_handler.tools import polarion
from art.unittest_lib import attr, CoreSystemTest as TestCase

from rhevmtests.system.aaa.ldap import config

logger = logging.getLogger('test_info')


@attr(tier=1)
class ExttoolInfo(TestCase):
    """ Test info module of ovirt-engine-extensions-tool """
    __test__ = True

    @classmethod
    def setup_class(cls):
        cls.info_cli = EngineCLI(
            tool=config.TOOL,
            session=config.ENGINE_HOST.executor().session(),
        ).setup_module(
            module='info',
            output='stdout',
        )

    @polarion('RHEVM3-14041')
    def test_list_extensions(self):
        """ test list of existing extensions """
        rc, out = self.info_cli.run('list-extensions', format='{instance}')
        extensions = out.split('\n')[:-1]
        logger.info('Enabled extensions: %s', extensions)
        self.assertTrue(rc, 'Failed to run info list-extensions')

        for extension in ['internal-authz', 'internal-authn']:
            self.assertTrue(
                extension in extensions, '%s was not found' % extension
            )

    @polarion('RHEVM3-14042')
    def test_configuration(self):
        """ test of listing configuration of authz/authn """
        for extension in ['internal-authz', 'internal-authn']:
            rc, out = self.info_cli.run(
                'configuration',
                extension_name=extension
            )
            logger.info('Extension configuration: %s', out)

            self.assertTrue(rc, 'Failed to run info configuration')
            self.assertTrue('aaa.jdbc' in out, 'Extension not found in conf')

    @polarion('RHEVM3-14043')
    def test_context(self):
        """ test of listing context of authz/authn """
        for extension in ['internal-authz', 'internal-authn']:
            rc, out = self.info_cli.run('context', extension_name=extension)
            logger.info('Extension context : %s', out)

            self.assertTrue(rc, 'Failed to run info context')
            self.assertTrue(
                extension in out,
                'Extension "%s" was not found in context' % extension
            )
