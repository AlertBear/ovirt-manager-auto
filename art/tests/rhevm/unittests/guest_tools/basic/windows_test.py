"""
Base class for all Windows basic sanity tests
"""
import json
from concurrent.futures import ThreadPoolExecutor
import logging
from nose.tools import istest
from unittest import TestCase
from unittest2 import skipIf
import os

import art.rhevm_api.utils.test_utils as utils
import art.test_handler.exceptions as exceptions
import config
import art.rhevm_api.tests_lib.low_level.vms as vms
import art.rhevm_api.tests_lib.low_level.templates as template

LOGGER = logging.getLogger(__name__)
SKIP_INSTALL = False
SKIP_UNINSTALL = False

def setup_module():
    "setup module"
    SKIP_INSTALL = bool(config.SKIP_INSTALL)
    SKIP_UNINSTALL = bool(config.SKIP_UNINSTALL)

def teardown_module():
    "teardown module"


class Windows(TestCase):
    """
    Base class for all Windows basic sanity tests
    """

    __test__ = False
    mac = None
    ip = None
    machine = None
    vmName = None
    template = None
    platf = None
    toolsDict = None

    @classmethod
    def setup_class(cls):
        "setup class"
        LOGGER.info("Setting up class %s",
                    cls.__name__)
        template.importTemplate(True, template=cls.templateNameStorage,
                        export_storagedomain=config.EXPORT_STORAGE_DOMAIN,
                        import_storagedomain=config.STORAGE_DOMAIN,
                        cluster=config.CLUSTER_NAME,
                        name=cls.template)
        vms.createVm(True, vmName=cls.vmName,
                     vmDescription="VM for %s class" % cls.__name__,
                     cluster=config.CLUSTER_NAME,
                     template=cls.template)
        vms.runVmOnce(
            True, cls.vmName, cdrom_image=config.CD_WITH_TOOLS)
        vms.waitForVMState(vm=cls.vmName, state='up')
        cls.mac = vms.getVmMacAddress(
            True, vm=cls.vmName,
            nic='nic2')[1].get('macAddress', None)
        LOGGER.info("Mac adress is %s", cls.mac)
        cls.ip = utils.convertMacToIpAddress(
            True, cls.mac, subnetClassB=config.SUBNET_CLASS)[1].get('ip', None)
        # os.environ['STAFCONVDIR'] = '/usr/local/staf/codepage'
        cls.machine = utils.createMachine(
            True, host=config.VDS, ip=cls.ip, os='windows', platf=cls.platf)

    @classmethod
    def teardown_class(cls, Vm):
        "tear down class"
        vms.removeVm(
            True, vm=cls.vmName, stopVM='true')

    @istest
    @skipIf(SKIP_INSTALL, "skiping installation")
    def installationUsingAPT(self):
        """
        This tests function that returns parameters a
        """
        if not utils.isGtMachineReady(True, self.machine):
            return False
        if not utils.installAPT(
                True, self.machine,
                json.loads(self.toolsDict), timeout=1000):
            LOGGER.error("Installation using APT failed")
            return False
        else:
            if not utils.areToolsAreCorrectlyInstalled(True, self.machine):
                LOGGER.error("Tools was not installed correctly")
                return False
        LOGGER.info("Installation using APT was successful")
        return True

    @istest
    @skipIf(SKIP_UNINSTALL, "skiping uninstallation")
    def unistallGuestTools(self):
        """
        This tests function that returns parameters a
        """
        if not utils.isGtMachineReady(True, self.machine):
            return False
        if not utils.removeTools(True, self.machine, timeout=1000):
            LOGGER.error("Uninstallation failed")
            return False
        LOGGER.info("uninstallation was successful")
        return True


class Windows7_64bit(Windows):
    """
    This is positive test case with several actions
    """
    __test__ = True
    vmName = config.WIN7_VM_NAME
    templateNameStorage = config.WIN7_TEMPLATE_NAME
    template = config.WIN7_IMPORTED_TEMPLATE_NAME
    platf = '64'
    toolsDict = config.WIN7_TOOLS_DICT

class WindowsXP(Windows):
    """
    This is positive test case with several actions
    """
    __test__ = True
    templateNameStorage = config.WINXP_TEMPLATE_NAME
    vmName = config.WINXP_VM_NAME
    template = config.WINXP_IMPORTED_TEMPLATE_NAME
    platf = '32'
    toolsDict = config.WINXP_TOOLS_DICT

class Windows7_32(Windows):
    """
    This is positive test case with several actions
    """
    __test__ = True
    templateNameStorage = config.WIN7_32_TEMPLATE_NAME
    vmName = config.WIN7_32_VM_NAME
    template = config.WIN7_32_IMPORTED_TEMPLATE_NAME
    platf = '32'
    toolsDict = config.WIN7_TOOLS_DICT