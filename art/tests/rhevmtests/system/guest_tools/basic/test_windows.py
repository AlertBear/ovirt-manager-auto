"""
Test installation of guest tools on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import copy
import inspect
import logging
import sys
import pytest

from unittest2 import SkipTest
from art.rhevm_api.tests_lib.low_level import vms, disks, storagedomains
from art.rhevm_api.utils import test_utils as utils
from art.test_handler.tools import bz
from art.unittest_lib import attr, CoreSystemTest as TestCase
from art.unittest_lib.windows import WindowsGuest
from functools import wraps
from rhevmtests.system.guest_tools import config

logger = logging.getLogger(__name__)
VM_API = utils.get_api('vm', 'vms')
WIN_IMAGES = []
GLANCE_IMAGE = None
GUEST_FAMILY = 'Windows'


def import_image(diskName):
    glance_image = storagedomains.GlanceImage(
        image_name=diskName,
        glance_repository_name=config.GLANCE_NAME,
        timeout=1800
    )
    assert glance_image.import_image(
        destination_storage_domain=config.STORAGE_NAME[0],
        cluster_name=None,
        new_disk_alias=diskName
    )
    return glance_image


def checkIfSupported(method):
    @wraps(method)
    def f(self, *args, **kwargs):
        if method.__name__ in self.UNSUPPORTED:
            raise SkipTest('Not supported on this windows version. Skipping.')
        return method(self, *args, **kwargs)
    return f


def setup_module():
    global WIN_IMAGES, GLANCE_IMAGE
    WIN_IMAGES = sorted(
        set([
            x[1].diskName for x in inspect.getmembers(
                sys.modules[__name__],
                inspect.isclass
            ) if getattr(x[1], '__test__', False)
        ]),
        reverse=True,
    )
    assert len(WIN_IMAGES) > 0, "There are no test cases to run"


@attr(tier=2, extra_reqs={'deprecated': True})
class Windows(TestCase):
    """
    Class that implements testing of windows guest tools.
    Every child(win version) of this class needs to specify relevant
    drivers/services/products to tests.
    """
    __test__ = False
    # List with method names which should not be tested for relevant windows
    # version and thus be skipped. By default empty.
    UNSUPPORTED = []
    machine = None
    diskName = None
    glance_image = None
    products = []
    services = []
    bz_map = {}  # Store bz's of specific windows
    polarion_map = {}  # Store polarion id of specific windows cases

    def __init__(self, *args, **kwargs):
        """ create a copy of method with relevant polarion_id """
        super(Windows, self).__init__(*args, **kwargs)
        pid = self.polarion_map.get(self._testMethodName, None)
        bz = self.bz_map.get(self._testMethodName, None)
        if pid or bz:
            m = getattr(self, self._testMethodName)

            @wraps(m)
            def wrapper(*args, **kwargs):
                return m(*args, **kwargs)
            wrapper.__dict__ = copy.copy(m.__dict__)
            if pid:
                wrapper.__dict__['polarion_id'] = pid
            if bz:
                wrapper.__dict__['bz'] = bz
            setattr(self, self._testMethodName, wrapper)

    @staticmethod
    def __prepare_image():
        global GLANCE_IMAGE
        if GLANCE_IMAGE:
            assert GLANCE_IMAGE._is_import_success()
        try:
            GLANCE_IMAGE = import_image(WIN_IMAGES.pop())
        except IndexError:
            GLANCE_IMAGE = None

    @pytest.fixture(scope='class', autouse=True)
    def setup_vm(self, request):
        cls = request.cls

        def fin():
            vms.removeVm(positive=True, vm=cls.diskName, stopVM='true')
        request.addfinalizer(fin)

        cls.__prepare_image()
        assert vms.createVm(
            positive=True,
            vmName=cls.diskName,
            vmDescription=cls.diskName,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE,
            nic=config.NIC_NAME,
            nicType=config.NIC_TYPE_E1000,
            cpu_cores=4,
            memory=4 * config.GB,
            ballooning=True,  # Need for test driver balloon
        )
        assert vms.addNic(  # Need for test_driver_network
            positive=True,
            vm=cls.diskName,
            name='virtioNIC',
            network=config.MGMT_BRIDGE,
            interface=config.NIC_TYPE_VIRTIO,
        )
        assert disks.attachDisk(True, cls.diskName, cls.diskName)
        assert vms.runVmOnce(
            True, cls.diskName, cdrom_image=config.CD_WITH_TOOLS
        )
        vms.waitForVMState(vm=cls.diskName, state=config.VM_UP)
        mac = vms.getVmMacAddress(
            True, vm=cls.diskName, nic=config.NIC_NAME
        )[1].get('macAddress', None)
        logger.info("Mac address is %s", mac)

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
        return '64' if self.machine.platf == '64-bit' else ''

    @property
    def architecture(self):
        return 'x86_64' if self.machine.platf == '64-bit' else 'x86'

    def test_a00_install_guest_tools(self):
        """ Install all supported apps of Windows version """
        assert self.machine.install_guest_tools(), (
            'Installation of guest tools failed.'
        )

    def _checkProduct(self, product):
        if not self.products:
            self.products = self.machine.get_all_products()
        assert product in self.products, '%s was not installed' % product
        logger.info('%s is installed', product)

    @checkIfSupported
    def test_checkProductQemuAgent(self):
        """ Check product qemu agent """
        self._checkProduct('QEMU guest agent')

    @checkIfSupported
    def test_checkProductSpice(self):
        """ Check product spice """
        self._checkProduct('RHEV-Spice%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductSpiceAgent(self):
        """ Check product spice agent """
        self._checkProduct('RHEV-Spice-Agent%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductSerial(self):
        """ Check product serial """
        self._checkProduct('RHEV-Serial%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductNetwork(self):
        """ Check product network """
        self._checkProduct('RHEV-Network%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductAgent(self):
        """ Check product agent """
        self._checkProduct('RHEV-Agent%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductUSB(self):
        """ Check product USB """
        self._checkProduct('RHEV-USB')

    @checkIfSupported
    def test_checkProductSSO(self):
        """ Check product SSO """
        self._checkProduct('RHEV-SSO%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductBlock(self):
        """ Check product block """
        self._checkProduct('RHEV-Block%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductBalloon(self):
        """ Check product balloon """
        self._checkProduct('RHEV-Balloon%s' % self.platfPrefix)

    @checkIfSupported
    def test_checkProductSCSI(self):
        """ Check product SCSI """
        self._checkProduct('RHEV-SCSI%s' % self.platfPrefix)

    def _checkService(self, service):
        if not self.services:
            self.services = self.machine.get_all_services()
        assert self.services[service]['State'] == 'Running', (
            '%s is not running' % service
        )
        assert self.services[service]['StartMode'] == 'Auto', (
            '%s is not enabled' % service
        )
        logger.info('Service %s is running/enabled', service)

    @checkIfSupported
    def test_checkServiceQemuGA(self):
        """ Check service qqmu GA """
        self._checkService('QEMU-GA')

    @checkIfSupported
    @bz({'1218937': {}})
    def test_checkServiceQemuGAVssProvider(self):
        """ Check service qqmu GA Vss provider """
        self._checkService('QEMU Guest Agent VSS Provider')

    @checkIfSupported
    def test_checkServiceUSBRedirector(self):
        """ Check service USB redirector """
        self._checkService('spiceusbredirector')

    @checkIfSupported
    def test_checkServiceAgent(self):
        """ Check service agent """
        self._checkService('RHEV-Agent')

    @checkIfSupported
    def test_checkServiceSpiceAgent(self):
        """ Check service spice agent """
        self._checkService('vdservice')

    def test_guest_applications(self):
        """ Check guest applications are reported """
        vm = VM_API.find(self.diskName)
        apps = vms.get_vm_applications(vm.get_name())
        logger.info("Windows '%s' apps are: %s", self.diskName, apps)
        assert len(apps) > 0, "Applications are empty"

    def test_guest_os(self):
        """ Check guest OS info is reported """
        # TODO: distribution, kernel
        vm = VM_API.find(self.diskName)
        guest_os = vm.get_guest_operating_system()
        logger.info("Guest '%s' os info:", self.diskName)
        logger.info("Architecture: '%s'", guest_os.get_architecture())
        logger.info("Codename: '%s'", guest_os.get_codename())
        logger.info("Family: '%s'", guest_os.get_family())
        assert self.architecture == guest_os.get_architecture(), (
            "Windows has wrong arch '%s', should be '%s'" %
            (guest_os.get_architecture(), self.architecture)
        )
        assert GUEST_FAMILY == guest_os.get_family(), (
            "Guest os family is windows: '%s'" % guest_os.get_family()
        )
        assert self.codename == guest_os.get_codename(), (
            "Guest codename '%s' should be '%s'" %
            (guest_os.get_codename(), self.codename)
        )

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        vm = VM_API.find(self.diskName)
        guest_timezone = vm.get_guest_time_zone()
        logger.info(
            "Guest timezone name is '%s', offset: '%s'",
            guest_timezone.get_name(),
            guest_timezone.get_utc_offset()
        )
        # TODO: obtain this info for windows machine via pywin and check
        # for correct versions
        assert len(guest_timezone.get_name()) > 0, 'Timezone name is empty'
        assert len(guest_timezone.get_utc_offset()) > 0, "UTC offset is empty"

    def _checkDeviceManager(self, deviceName):
        """
        Check correct status of device in device manager.
        :param deviceName: name of device to check
        :type deviceName: str
        """
        device = self.machine.get_device_info(deviceName)
        assert device, "Device driver '%s' was not found" % deviceName
        assert device['Status'].upper() == 'OK', '%s' % device
        assert device['ConfigManagerErrorCode'] == '0', '%s' % device

    @checkIfSupported
    def test_driver_balloon(self):
        """ Check driver balloon """
        self._checkDeviceManager('VirtIO Balloon Driver')

    @checkIfSupported
    def test_driver_network(self):
        """ Check driver Network """
        self._checkDeviceManager('Red Hat VirtIO Ethernet Adapter')

    @checkIfSupported
    def test_driver_qxl_gpu(self):
        """ Check driver qxl """
        self._checkDeviceManager('Red Hat QXL GPU')

    @checkIfSupported
    def test_driver_usb_bus(self):
        """ Check driver usb bus """
        self._checkDeviceManager('Red Hat USB Bus Driver')

    @checkIfSupported
    def test_driver_usb_host_controller(self):
        """ Check driver usb host controller """
        self._checkDeviceManager('Red Hat Virtual USB Host Controller Driver')

    @checkIfSupported
    def test_driver_vioscsi_pass_through(self):
        """ Check driver SCSI pass-through """
        self._checkDeviceManager('Red Hat VirtIO SCSI pass-through controller')

    @checkIfSupported
    def test_driver_vioscsi_disk(self):
        """ Check driver SCSI disk device """
        self._checkDeviceManager('Red Hat VirtIO SCSI Disk Device')

    @checkIfSupported
    def test_driver_vioserial(self):
        """ Check driver serial """
        self._checkDeviceManager('VirtIO-Serial Driver')

    @checkIfSupported
    def test_driver_viostor(self):
        """ Check driver viostor """
        self._checkDeviceManager('Red Hat VirtIO SCSI controller')

    def test_z_unistallGuestTools(self):
        """
        This tests uninstallation of GT
        """
        assert self.machine.wait_for_machine_ready(), (
            'Windows machine is not ready, timeout expired.'
        )
        assert self.machine.uninstall_guest_tools(), (
            "GT failed to uninstall"
        )


class Windows10_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 10 64bit.
    """
    __test__ = True
    diskName = config.WIN10_DISK_64b
    codename = 'Win 10'
    polarion_map = {
        'test_checkProductNetwork': 'RHEVM3-13203',
        'test_checkProductSpice': 'RHEVM3-13204',
        'test_checkProductSerial': 'RHEVM3-13205',
        'test_checkProductBlock': 'RHEVM3-13206',
        'test_checkProductBalloon': 'RHEVM3-13207',
        'test_checkProductUSB': 'RHEVM3-13208',
        'test_checkProductQemuAgent': 'RHEVM3-13209',
        'test_checkProductSSO': 'RHEVM3-13210',
        'test_checkProductSpiceAgent': 'RHEVM3-13211',
        'test_checkProductAgent': 'RHEVM3-13212',
        'test_checkProductSCSI': 'RHEVM3-13213',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13214',
        'test_driver_vioscsi_disk': 'RHEVM3-13215',
        'test_driver_vioserial': 'RHEVM3-13216',
        'test_driver_network': 'RHEVM3-13217',
        'test_driver_usb_bus': 'RHEVM3-13218',
        'test_driver_usb_host_controller': 'RHEVM3-13219',
        'test_driver_viostor': 'RHEVM3-13220',
        'test_driver_qxl_gpu': 'RHEVM3-13221',
        'test_driver_balloon': 'RHEVM3-13222',
        'test_checkServiceAgent': 'RHEVM3-13223',
        'test_checkServiceQemuGA': 'RHEVM3-13224',
        'test_checkServiceUSBRedirector': 'RHEVM3-13225',
        'test_checkServiceSpiceAgent': 'RHEVM3-13226',
        'test_checkServiceQemuGAVssProvider': 'RHEVM3-13227',
        'test_guest_applications': 'RHEVM3-14413',
        'test_guest_timezone': 'RHEVM3-14415',
        'test_guest_os': 'RHEVM3-14416',
    }
    UNSUPPORTED = Windows.UNSUPPORTED + [
        'test_driver_qxl_gpu',
    ]
