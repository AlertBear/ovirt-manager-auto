"""
-----------------
test_vms
-----------------

@author: Nelly Credi
"""

import logging

from nose.tools import istest
from art.test_handler.tools import bz  # pylint: disable=E0611
from art.test_handler.settings import opts
from art.unittest_lib import attr

from art.unittest_lib import BaseTestCase as TestCase
from art.rhevm_api.tests_lib.low_level import vms, templates
from art.test_handler.exceptions import SkipTest

from rhevmtests.infra.regression_infra import config
from rhevmtests.infra.regression_infra import help_functions

logger = logging.getLogger(__name__)
ENUMS = config.ENUMS
NFS = opts['elements_conf']['RHEVM Enums']['storage_type_nfs']


def setup_module():
    """
    Setup prerequisites for testing scenario:
    create data center, cluster, host & storage domain
    """
    if NFS not in opts['storages']:
        logger.info("Storage type is not NFS, skipping tests")
        raise SkipTest
    help_functions.utils.reverse_env_list = []
    help_functions.utils.add_dc()
    help_functions.utils.add_cluster()
    help_functions.utils.add_host()
    help_functions.utils.create_sd()
    help_functions.utils.attach_sd()


def teardown_module():
    """
    Tear down prerequisites for testing host functionality:
    remove data center, cluster, host & storage domain
    """
    help_functions.utils.clean_environment()


@attr(team='automationInfra', tier=0)
class TestCaseVM(TestCase):
    """
    vm tests
    """
    __test__ = (NFS in opts['storages'])

    storages = set([NFS])

    @istest
    def t01_create_vm(self):
        """
        test verifies vm functionality
        the test adds a vm
        """
        logger.info('Create vm')
        status = vms.addVm(positive=True, name=config.VM_NAME,
                           cluster=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Create vm')

    @istest
    def t02_add_disk_to_vm_wrong_format(self):
        """
        test verifies vm functionality
        the test adds disk to vm with wrong format & verifies it fails
        """
        logger.info('Add disk to vm - wrong format')
        status = vms.addDisk(positive=False, vm=config.VM_NAME,
                             size=2147483648,
                             storagedomain=config.STORAGE_DOMAIN_NAME,
                             type=ENUMS['disk_type_system'],
                             format='bad_config',
                             interface=ENUMS['interface_ide'])
        self.assertTrue(status, 'Add disk to vm - wrong format')

    @istest
    def t03_add_disk_to_vm_wrong_interface(self):
        """
        test verifies vm functionality
        the test adds disk to vm with wrong interface & verifies it fails
        """
        logger.info('Add disk to vm - wrong interface')
        status = vms.addDisk(positive=False, vm=config.VM_NAME,
                             size=2147483648,
                             storagedomain=config.STORAGE_DOMAIN_NAME,
                             type=ENUMS['disk_type_system'],
                             format=ENUMS['format_cow'],
                             interface='bad_config')
        self.assertTrue(status, 'Add disk to vm - wrong interface')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']}})
    def t04_add_disk_to_vm(self):
        """
        test verifies vm functionality
        the test adds disk to vm
        """
        logger.info('Add disk to vm')
        status = vms.addDisk(positive=True, vm=config.VM_NAME,
                             size=2147483648,
                             storagedomain=config.STORAGE_DOMAIN_NAME,
                             type=ENUMS['disk_type_system'],
                             format=ENUMS['format_cow'],
                             interface=ENUMS['interface_ide'])
        self.assertTrue(status, 'Add disk to vm')

    @istest
    def t05_create_template(self):
        """
        test verifies template functionality
        the test creates a template
        """
        logger.info('Create template')
        status = templates.createTemplate(positive=True,
                                          vm=config.VM_NAME,
                                          name=config.TEMPLATE_NAME,
                                          cluster=config.CLUSTER_1_NAME)
        self.assertTrue(status, 'Create template')

    @istest
    @bz({'1193848': {'engine': ['sdk'], 'version': ['3.5']}})
    def t06_remove_disk_from_vm(self):
        """
        test verifies vm functionality
        the test removes disk to vm
        """
        logger.info('Remove disk from vm')
        status = vms.removeDisk(positive=True, vm=config.VM_NAME,
                                disk=config.VM_NAME + '_Disk1')
        self.assertTrue(status, 'Remove disk from vm')

    @istest
    def t07_remove_vm(self):
        """
        test verifies vm functionality
        the test removes a vm
        """
        logger.info('Remove vm')
        status = vms.removeVm(positive=True, vm=config.VM_NAME)
        self.assertTrue(status, 'Remove vm')

    @istest
    def t08_remove_template(self):
        """
        test verifies template functionality
        the test removes a template
        """
        logger.info('Remove template')
        status = templates.removeTemplate(positive=True,
                                          template=config.TEMPLATE_NAME)
        self.assertTrue(status, 'Remove template')
