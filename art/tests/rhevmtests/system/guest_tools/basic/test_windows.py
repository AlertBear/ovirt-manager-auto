"""
Base class for all Windows basic sanity tests
"""
import logging

from art.rhevm_api.utils import test_utils as utils
from art.rhevm_api.tests_lib.low_level import vms, templates
from art.unittest_lib import attr, CoreSystemTest as TestCase
from rhevmtests.system.guest_tools import config
from nose.tools import istest
from unittest2 import skipIf


LOGGER = logging.getLogger(__name__)
SKIP_CASE = False


@attr(tier=1, extra_reqs={'pywinrm': True})
class Windows(TestCase):
    """
    Base class for all Windows basic sanity tests
    """

    __test__ = False
    machine = None
    vmName = None
    platf = None

    @classmethod
    def setup_class(cls):
        global SKIP_CASE
        cls.platf = '64' if '64' in cls.vmName else ''
        SKIP_CASE = '2008' in cls.vmName or '2012' in cls.vmName

        templates.importTemplate(
            True,
            template=cls.vmName,
            export_storagedomain=config.EXPORT_STORAGE_DOMAIN,
            import_storagedomain=config.STORAGE_DOMAIN,
            cluster=config.CLUSTER_NAME[0],
            name=cls.vmName,
        )
        vms.createVm(
            True,
            vmName=cls.vmName,
            vmDescription="VM for %s class" % cls.__name__,
            cluster=config.CLUSTER_NAME[0],
            template=cls.vmName,
            network=config.MGMT_BRIDGE,
        )
        vms.runVmOnce(True, cls.vmName, cdrom_image=config.CD_WITH_TOOLS)
        vms.waitForVMState(vm=cls.vmName, state='up')
        mac = vms.getVmMacAddress(
            True, vm=cls.vmName,
            nic='nic1'
        )[1].get('macAddress', None)
        LOGGER.info("Mac adress is %s", mac)

        ip = utils.convertMacToIpAddress(
            True, mac, subnetClassB=config.SUBNET_CLASS
        )[1].get('ip', None)
        cls.machine = utils.createMachine(
            True,
            host=config.HOSTS[0],
            ip=ip,
            os='windows',
            platf=cls.platf
        )

    @classmethod
    def teardown_class(cls):
        vms.removeVm(True, vm=cls.vmName, stopVM='true')

    @istest
    def a_installationUsingAPT(self):
        """
        This function test installation of GT using APT
        """
        self.assertTrue(
            utils.isGtMachineReady(True, self.machine),
            'Windows machine is not ready, timeout expired.',
        )
        self.assertTrue(
            utils.installAPT(
                True,
                self.machine,
                {},
                timeout=1000,
            ),
            'Installation using APT failed',
        )
        self.assertTrue(
            utils.areToolsAreCorrectlyInstalled(True, self.machine),
            'Tools was not installed correctly',
        )
        LOGGER.info("Installation using APT was successful")

    def _checkProduct(self, product):
        self.assertTrue(
            self.machine.isProductInstalled(product),
            '%s was not installed' % product
        )
        LOGGER.info('%s is installed', product)

    @istest
    def checkProductQemuAgent(self):
        """ Check product qemu agent """
        self._checkProduct('QEMU guest agent')

    @istest
    @skipIf(SKIP_CASE, 'Spice is not supported. Skipping.')
    def checkProductSpice(self):
        """ Check product spice """
        self._checkProduct('RHEV-Spice%s' % self.platf)

    @istest
    def checkProductSpiceAgent(self):
        """ Check product spice agent """
        self._checkProduct('RHEV-Spice-Agent%s' % self.platf)

    @istest
    def checkProductSerial(self):
        """ Check product serial """
        self._checkProduct('RHEV-Serial%s' % self.platf)

    @istest
    def checkProductNetwork(self):
        """ Check product network """
        self._checkProduct('RHEV-Network%s' % self.platf)

    @istest
    def checkProductAgent(self):
        """ Check product agent """
        self._checkProduct('RHEV-Agent%s' % self.platf)

    @istest
    @skipIf(SKIP_CASE, 'USB is not supported. Skipping.')
    def checkProductUSB(self):
        """ Check product USB """
        self._checkProduct('RHEV-USB')

    @istest
    @skipIf(SKIP_CASE, 'SSO is not supported. Skipping.')
    def checkProductSSO(self):
        """ Check product SSO """
        self._checkProduct('RHEV-SSO%s' % self.platf)

    @istest
    def checkProductBlock(self):
        """ Check product block """
        self._checkProduct('RHEV-Block%s' % self.platf)

    @istest
    def checkProductBalloon(self):
        """ Check product balloon """
        self._checkProduct('RHEV-Balloon%s' % self.platf)

    @istest
    def checkProductSCSI(self):
        """ Check product SCSI """
        self._checkProduct('RHEV-SCSI%s' % self.platf)

    def _checkService(self, service):
        self.assertTrue(
            self.machine.isServiceRunningAndEnabled(service),
            '%s is not running/enabled' % service
        )
        LOGGER.info('Service %s is running/enabled', service)

    @istest
    def checkServiceQemuGA(self):
        self._checkService('QEMU-GA')

    # TODO add skip foro non win7 & win8
    @istest
    def checkServiceQemuGAVssProvider(self):
        self._checkService('QEMU Guest Agent VSS Provider')

    @istest
    def checkServiceUSBRedirector(self):
        self._checkService('spiceusbredirector')

    @istest
    def checkServiceAgent(self):
        self._checkService('RHEV-Agent')

    @istest
    def checkServiceSpiceAgent(self):
        self._checkService('vdservice')

    @istest
    def z_unistallGuestTools(self):
        """
        This tests uninstallation of GT
        """
        self.assertTrue(
            utils.isGtMachineReady(True, self.machine),
            'Windows machine is not ready, timeout expired.',
        )
        if utils.removeTools(True, self.machine, timeout=1000):
            LOGGER.info('GT was uninstalled')
        else:
            LOGGER.error('GT failed to uninstall')


class Windows7_64bit(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    vmName = config.WIN7_TEMPLATE_NAME


@attr(tier=1)
class Windows7_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2008_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 32bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2008R2_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 32bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2008_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 64bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2008R2_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 64bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2012_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 32bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2012R2_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 32bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2012_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 64bit.
    """
    __test__ = False


@attr(tier=1)
class Windows2012R2_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 64bit.
    """
    __test__ = False
