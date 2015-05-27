"""
Test installation via APT on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import inspect
import logging
import sys

from art.rhevm_api.tests_lib.low_level import vms, disks, storagedomains
from art.rhevm_api.utils import test_utils as utils
from art.test_handler.exceptions import SkipTest
from art.test_handler.tools import bz  # pylint: disable=E0611
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.unittest_lib.windows import WindowsGuest
from functools import wraps
from nose.tools import istest
from rhevmtests.system.guest_tools import config


LOGGER = logging.getLogger(__name__)
VM_API = utils.get_api('vm', 'vms')
WIN_IMAGES = []
GLANCE_IMAGE = None


def import_image(diskName):
    glance_image = storagedomains.GlanceImage(
        image_name=diskName,
        glance_repository_name=config.GLANCE_NAME,
    )
    glance_image.import_image(
        destination_storage_domain=config.STORAGE_NAME[0],
        cluster_name=None,
        new_disk_alias=diskName,
        async=True
    )
    return glance_image


def skipIfUnsupported(method):
    @wraps(method)
    def f(self, *args, **kwargs):
        if method.__name__ in self.SKIP_METHODS:
            raise SkipTest('Not supported on this windows version. Skipping.')
        return method(self, *args, **kwargs)
    return f


def setup_module():
    global WIN_IMAGES, GLANCE_IMAGE
    WIN_IMAGES = [
        x[1].diskName for x in sorted(
            inspect.getmembers(sys.modules[__name__], inspect.isclass),
            reverse=True
        ) if getattr(x[1], '__test__', False)
    ]
    assert len(WIN_IMAGES) > 0, "There are no test cases to run"
    assert vms.createVm(
        positive=True,
        vmName=config.WINDOWS_VM,
        vmDescription=config.WINDOWS_VM,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        nic=config.NIC_NAME,
        nicType=config.NIC_TYPE_E1000,
    )
    GLANCE_IMAGE = import_image(WIN_IMAGES.pop())


def teardown_module():
    assert vms.removeVm(positive=True, vm=config.WINDOWS_VM, stopVM='true')


@attr(tier=1)
class Windows(TestCase):
    """ Base class for all Windows basic sanity tests """
    __test__ = False
    machine = None
    diskName = None
    glance_image = None

    @classmethod
    def __prepare_image(self):
        global GLANCE_IMAGE
        if GLANCE_IMAGE:
            assert GLANCE_IMAGE._is_import_success()
        try:
            GLANCE_IMAGE = import_image(WIN_IMAGES.pop())
        except IndexError:
            GLANCE_IMAGE = None

    @classmethod
    def setup_class(cls):
        cls.__prepare_image()
        assert disks.attachDisk(True, cls.diskName, config.WINDOWS_VM)
        assert vms.runVmOnce(
            True, config.WINDOWS_VM, cdrom_image=config.CD_WITH_TOOLS
        )
        vms.waitForVMState(vm=config.WINDOWS_VM, state=config.VM_UP)
        mac = vms.getVmMacAddress(
            True, vm=config.WINDOWS_VM, nic=config.NIC_NAME
        )[1].get('macAddress', None)
        LOGGER.info("Mac address is %s", mac)

        ip = utils.convertMacToIpAddress(
            True, mac, subnetClassB=config.SUBNET_CLASS
        )[1].get('ip', None)
        cls.machine = WindowsGuest(ip)
        assert cls.machine.wait_for_machine_ready()

    @property
    def platfPrefix(self):
        """
        Description: 32bit services don't use, prefix 64bit service use '64'
        :returns: 64 or empty string based on machine platform
        :rtype: str
        """
        return '64' if self.machine.platf == '64' else ''

    @classmethod
    def teardown_class(cls):
        assert vms.stopVm(True, config.WINDOWS_VM)
        assert disks.detachDisk(True, cls.diskName, config.WINDOWS_VM)
        assert disks.deleteDisk(True, cls.diskName)

    @istest
    def a00_install_guest_tools(self):
        """ Install all supported apps of Windows version """
        self.assertTrue(
            self.machine.install_guest_tools(),
            'Installation of guest tools failed.'
        )

    def _checkProduct(self, product):
        self.assertTrue(
            self.machine.is_product_installed(product),
            '%s was not installed' % product
        )
        LOGGER.info('%s is installed', product)

    @istest
    @skipIfUnsupported
    def checkProductQemuAgent(self):
        """ Check product qemu agent """
        self._checkProduct('QEMU guest agent')

    @istest
    @skipIfUnsupported
    def checkProductSpice(self):
        """ Check product spice """
        self._checkProduct('RHEV-Spice%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductSpiceAgent(self):
        """ Check product spice agent """
        self._checkProduct('RHEV-Spice-Agent%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductSerial(self):
        """ Check product serial """
        self._checkProduct('RHEV-Serial%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductNetwork(self):
        """ Check product network """
        self._checkProduct('RHEV-Network%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductAgent(self):
        """ Check product agent """
        self._checkProduct('RHEV-Agent%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductUSB(self):
        """ Check product USB """
        self._checkProduct('RHEV-USB')

    @istest
    @skipIfUnsupported
    def checkProductSSO(self):
        """ Check product SSO """
        self._checkProduct('RHEV-SSO%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductBlock(self):
        """ Check product block """
        self._checkProduct('RHEV-Block%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductBalloon(self):
        """ Check product balloon """
        self._checkProduct('RHEV-Balloon%s' % self.platfPrefix)

    @istest
    @skipIfUnsupported
    def checkProductSCSI(self):
        """ Check product SCSI """
        self._checkProduct('RHEV-SCSI%s' % self.platfPrefix)

    def _checkService(self, service):
        self.assertTrue(
            self.machine.is_service_running(service),
            '%s is not running' % service
        )
        self.assertTrue(
            self.machine.is_service_enabled(service),
            '%s is not enabled' % service
        )
        LOGGER.info('Service %s is running/enabled', service)

    @istest
    @skipIfUnsupported
    def checkServiceQemuGA(self):
        """ Check service qqmu GA """
        self._checkService('QEMU-GA')

    @istest
    @skipIfUnsupported
    @bz({'1218937': {'engine': None, 'version': ['3.5', '3.6']}})
    def checkServiceQemuGAVssProvider(self):
        """ Check service qqmu GA Vss provider """
        self._checkService('QEMU Guest Agent VSS Provider')

    @istest
    @skipIfUnsupported
    def checkServiceUSBRedirector(self):
        """ Check service USB redirector """
        self._checkService('spiceusbredirector')

    @istest
    @skipIfUnsupported
    def checkServiceAgent(self):
        """ Check service agent """
        self._checkService('RHEV-Agent')

    @istest
    @skipIfUnsupported
    def checkServiceSpiceAgent(self):
        """ Check service spice agent """
        self._checkService('vdservice')

    @istest
    @skipIfUnsupported
    def checkGuestInfo(self):
        """ Check agent data are reported """
        guest_info = VM_API.find(config.WINDOWS_VM).get_guest_info()
        self.assertTrue(
            self.machine.ip in [
                ip.get_address() for ip in guest_info.get_ips().get_ip() if ip
            ],
            "Ip %s not found in guest info" % self.machine.ip
        )
        self.assertTrue(
            guest_info.get_fqdn() and len(guest_info.get_fqdn()) > 0
        )

    @istest
    def z_unistallGuestTools(self):
        """
        This tests uninstallation of GT
        """
        self.assertTrue(
            self.machine.wait_for_machine_ready(),
            'Windows machine is not ready, timeout expired.'
        )
        self.assertTrue(
            self.machine.uninstall_guest_tools(),
            "GT failed to uninstall"
        )


class WindowsDesktop(Windows):
    __test__ = False
    SKIP_METHODS = []


class WindowsServer(Windows):
    __test__ = False
    SKIP_METHODS = [
        'checkProductSpice',
        'checkProductUSB',
        'checkProductSSO',
        'checkServiceUSBRedirector',
    ]


class Windows7_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    # TODO: name disk in glance as these clasess and get rid of diskName var
    diskName = config.WIN7_DISK_64b


class Windows7_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    diskName = config.WIN7_DISK_32b


class Windows8_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    diskName = config.WIN8_DISK_64b
    SKIP_METHODS = [
        'checkProductSpice',
        'checkProductUSB',
    ]


class Windows8_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    diskName = config.WIN8_DISK_32b
    SKIP_METHODS = [
        'checkProductSpice',
        'checkProductUSB',
    ]


class Windows8_1_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    diskName = config.WIN8_1_DISK_64b
    SKIP_METHODS = [
        'checkProductSpice',
        'checkProductUSB',
    ]


class Windows8_1_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    diskName = config.WIN8_1_DISK_32b
    SKIP_METHODS = [
        'checkProductSpice',
        'checkProductUSB',
    ]


class Windows2008_32b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 32bit.
    """
    __test__ = False
    diskName = config.WIN2008_DISK_32b


class Windows2008_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 64bit.
    """
    __test__ = False
    diskName = config.WIN2008_DISK_64b


class Windows2008R2_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 64bit.
    """
    __test__ = True
    diskName = config.WIN2008R2_DISK_64b


class Windows2012_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 64bit.
    """
    __test__ = True
    diskName = config.WIN2012_DISK_64b


class Windows2012R2_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 64bit.
    """
    __test__ = True
    diskName = config.WIN2012R2_DISK_64b
