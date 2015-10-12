"""
Test installation of guest tools on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import copy
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


def checkIfSupported(method):
    @wraps(method)
    def f(self, *args, **kwargs):
        if method.__name__ in self.UNSUPPORTED:
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
    GLANCE_IMAGE = import_image(WIN_IMAGES.pop())


@attr(tier=2)
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

    def __init__(self, *args, **kwargs):
        """ create a copy of method with relevant polarion_id """
        super(Windows, self).__init__(*args, **kwargs)
        pid = self.polarion_map.get(self._testMethodName)
        if pid:
            m = getattr(self, self._testMethodName)

            @wraps(m)
            def wrapper(*args, **kwargs):
                return m(*args, **kwargs)
            wrapper.__dict__ = copy.copy(m.__dict__)
            wrapper.__dict__['polarion_id'] = pid
            setattr(self, self._testMethodName, wrapper)

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
        assert vms.createVm(
            positive=True,
            vmName=cls.diskName,
            vmDescription=cls.diskName,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE,
            nic=config.NIC_NAME,
            nicType=config.NIC_TYPE_E1000,
            cpu_cores=4,
            memory=4*config.GB,
            balloon=True,  # Need for test driver balloon
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
        return '64' if self.machine.platf == '64-bit' else ''

    @classmethod
    def teardown_class(cls):
        assert vms.removeVm(positive=True, vm=cls.diskName, stopVM='true')

    @istest
    def a00_install_guest_tools(self):
        """ Install all supported apps of Windows version """
        self.assertTrue(
            self.machine.install_guest_tools(),
            'Installation of guest tools failed.'
        )

    def _checkProduct(self, product):
        if not self.products:
            self.products = self.machine.get_all_products()
        self.assertTrue(
            product in self.products,
            '%s was not installed' % product
        )
        LOGGER.info('%s is installed', product)

    @istest
    @checkIfSupported
    def checkProductQemuAgent(self):
        """ Check product qemu agent """
        self._checkProduct('QEMU guest agent')

    @istest
    @checkIfSupported
    def checkProductSpice(self):
        """ Check product spice """
        self._checkProduct('RHEV-Spice%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductSpiceAgent(self):
        """ Check product spice agent """
        self._checkProduct('RHEV-Spice-Agent%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductSerial(self):
        """ Check product serial """
        self._checkProduct('RHEV-Serial%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductNetwork(self):
        """ Check product network """
        self._checkProduct('RHEV-Network%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductAgent(self):
        """ Check product agent """
        self._checkProduct('RHEV-Agent%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductUSB(self):
        """ Check product USB """
        self._checkProduct('RHEV-USB')

    @istest
    @checkIfSupported
    def checkProductSSO(self):
        """ Check product SSO """
        self._checkProduct('RHEV-SSO%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductBlock(self):
        """ Check product block """
        self._checkProduct('RHEV-Block%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductBalloon(self):
        """ Check product balloon """
        self._checkProduct('RHEV-Balloon%s' % self.platfPrefix)

    @istest
    @checkIfSupported
    def checkProductSCSI(self):
        """ Check product SCSI """
        self._checkProduct('RHEV-SCSI%s' % self.platfPrefix)

    def _checkService(self, service):
        if not self.services:
            self.services = self.machine.get_all_services()
        self.assertTrue(
            self.services[service]['State'] == 'Running',
            '%s is not running' % service
        )
        self.assertTrue(
            self.services[service]['StartMode'] == 'Auto',
            '%s is not enabled' % service
        )
        LOGGER.info('Service %s is running/enabled', service)

    @istest
    @checkIfSupported
    def checkServiceQemuGA(self):
        """ Check service qqmu GA """
        self._checkService('QEMU-GA')

    @istest
    @checkIfSupported
    @bz({'1218937': {'engine': None, 'version': ['7.1']}})
    def checkServiceQemuGAVssProvider(self):
        """ Check service qqmu GA Vss provider """
        self._checkService('QEMU Guest Agent VSS Provider')

    @istest
    @checkIfSupported
    def checkServiceUSBRedirector(self):
        """ Check service USB redirector """
        self._checkService('spiceusbredirector')

    @istest
    @checkIfSupported
    def checkServiceAgent(self):
        """ Check service agent """
        self._checkService('RHEV-Agent')

    @istest
    @checkIfSupported
    def checkServiceSpiceAgent(self):
        """ Check service spice agent """
        self._checkService('vdservice')

    @istest
    @checkIfSupported
    def checkGuestInfo(self):
        """ Check agent data are reported """
        guest_info = VM_API.find(self.diskName).get_guest_info()
        self.assertTrue(
            self.machine.ip in [
                ip.get_address() for ip in guest_info.get_ips().get_ip() if ip
            ],
            "Ip %s not found in guest info" % self.machine.ip
        )
        self.assertTrue(
            guest_info.get_fqdn() and len(guest_info.get_fqdn()) > 0
        )

    def _checkDeviceManager(self, deviceName):
        """
        Check correct status of device in device manager.
        :param deviceName: name of device to check
        :type deviceName: str
        """
        device = self.machine.get_device_info(deviceName)
        assert device, "Device driver '%s' was not found" % deviceName
        self.assertTrue(device['Status'].upper() == 'OK', '%s' % device)
        self.assertTrue(device['ConfigManagerErrorCode'] == '0', '%s' % device)

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


class WindowsServer(Windows):
    __test__ = False
    UNSUPPORTED = Windows.UNSUPPORTED + [
        'checkProductSpice',
        'checkProductUSB',
        'checkProductSSO',
        'checkServiceUSBRedirector',
        'test_driver_usb_bus',
        'test_driver_usb_host_controller',
    ]


class Windows7_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    # TODO: name disk in glance as these clasess and get rid of diskName var
    diskName = config.WIN7_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13354',
        'checkProductSpice': 'RHEVM3-13355',
        'checkProductSerial': 'RHEVM3-13356',
        'checkProductBlock': 'RHEVM3-13357',
        'checkProductBalloon': 'RHEVM3-13358',
        'checkProductUSB': 'RHEVM3-13359',
        'checkProductQemuAgent': 'RHEVM3-13360',
        'checkProductSSO': 'RHEVM3-13361',
        'checkProductSpiceAgent': 'RHEVM3-13362',
        'checkProductAgent': 'RHEVM3-13363',
        'checkProductSCSI': 'RHEVM3-13364',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13365',
        'test_driver_vioscsi_disk': 'RHEVM3-13366',
        'test_driver_vioserial': 'RHEVM3-13367',
        'test_driver_network': 'RHEVM3-13368',
        'test_driver_usb_bus': 'RHEVM3-13369',
        'test_driver_usb_host_controller': 'RHEVM3-13370',
        'test_driver_viostor': 'RHEVM3-13371',
        'test_driver_qxl_gpu': 'RHEVM3-13372',
        'test_driver_balloon': 'RHEVM3-13373',
        'checkServiceAgent': 'RHEVM3-13374',
        'checkServiceQemuGA': 'RHEVM3-13375',
        'checkServiceUSBRedirector': 'RHEVM3-13376',
        'checkServiceSpiceAgent': 'RHEVM3-13377',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13378',

    }
    SUPPORTED = ['test_driver_qxl_gpu']


class Windows7_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    diskName = config.WIN7_DISK_32b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13278',
        'checkProductSpice': 'RHEVM3-13279',
        'checkProductSerial': 'RHEVM3-13280',
        'checkProductBlock': 'RHEVM3-13281',
        'checkProductBalloon': 'RHEVM3-13282',
        'checkProductUSB': 'RHEVM3-13283',
        'checkProductQemuAgent': 'RHEVM3-13284',
        'checkProductSSO': 'RHEVM3-13285',
        'checkProductSpiceAgent': 'RHEVM3-13286',
        'checkProductAgent': 'RHEVM3-13287',
        'checkProductSCSI': 'RHEVM3-13288',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13289',
        'test_driver_vioscsi_disk': 'RHEVM3-13290',
        'test_driver_vioserial': 'RHEVM3-13291',
        'test_driver_network': 'RHEVM3-13292',
        'test_driver_usb_bus': 'RHEVM3-13293',
        'test_driver_usb_host_controller': 'RHEVM3-13294',
        'test_driver_viostor': 'RHEVM3-13295',
        'test_driver_qxl_gpu': 'RHEVM3-13296',
        'test_driver_balloon': 'RHEVM3-13297',
        'checkServiceAgent': 'RHEVM3-13298',
        'checkServiceQemuGA': 'RHEVM3-13299',
        'checkServiceUSBRedirector': 'RHEVM3-13300',
        'checkServiceSpiceAgent': 'RHEVM3-13301',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13302',
    }
    SUPPORTED = ['test_driver_qxl_gpu']


class Windows8_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = False
    diskName = config.WIN8_DISK_64b
    UNSUPPORTED = WindowsDesktop.UNSUPPORTED + [
        'checkProductSpice',
        'checkProductUSB',
        'test_driver_qxl_gpu',
    ]


class Windows8_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = False
    diskName = config.WIN8_DISK_32b
    UNSUPPORTED = WindowsDesktop.UNSUPPORTED + [
        'checkProductSpice',
        'checkProductUSB',
        'test_driver_qxl_gpu',
    ]


class Windows8_1_64bit(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    diskName = config.WIN8_1_DISK_64b
    UNSUPPORTED = WindowsDesktop.UNSUPPORTED + [
        'checkProductSpice',
        'checkProductUSB',
        'test_driver_qxl_gpu',
    ]
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13228',
        'checkProductSpice': 'RHEVM3-13229',
        'checkProductSerial': 'RHEVM3-13230',
        'checkProductBlock': 'RHEVM3-13231',
        'checkProductBalloon': 'RHEVM3-13232',
        'checkProductUSB': 'RHEVM3-13233',
        'checkProductQemuAgent': 'RHEVM3-13234',
        'checkProductSSO': 'RHEVM3-13235',
        'checkProductSpiceAgent': 'RHEVM3-13236',
        'checkProductAgent': 'RHEVM3-13237',
        'checkProductSCSI': 'RHEVM3-13238',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13239',
        'test_driver_vioscsi_disk': 'RHEVM3-13240',
        'test_driver_vioserial': 'RHEVM3-13241',
        'test_driver_network': 'RHEVM3-13242',
        'test_driver_usb_bus': 'RHEVM3-13243',
        'test_driver_usb_host_controller': 'RHEVM3-13244',
        'test_driver_viostor': 'RHEVM3-13245',
        'test_driver_qxl_gpu': 'RHEVM3-13246',
        'test_driver_balloon': 'RHEVM3-13247',
        'checkServiceAgent': 'RHEVM3-13248',
        'checkServiceQemuGA': 'RHEVM3-13249',
        'checkServiceUSBRedirector': 'RHEVM3-13250',
        'checkServiceSpiceAgent': 'RHEVM3-13251',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13252',
    }


class Windows8_1_32b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    diskName = config.WIN8_1_DISK_32b
    UNSUPPORTED = WindowsDesktop.UNSUPPORTED + [
        'checkProductSpice',
        'checkProductUSB',
        'test_driver_qxl_gpu',
    ]
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13178',
        'checkProductSpice': 'RHEVM3-13179',
        'checkProductSerial': 'RHEVM3-13180',
        'checkProductBlock': 'RHEVM3-13181',
        'checkProductBalloon': 'RHEVM3-13182',
        'checkProductUSB': 'RHEVM3-13183',
        'checkProductQemuAgent': 'RHEVM3-13184',
        'checkProductSSO': 'RHEVM3-13185',
        'checkProductSpiceAgent': 'RHEVM3-13186',
        'checkProductAgent': 'RHEVM3-13187',
        'checkProductSCSI': 'RHEVM3-13188',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13189',
        'test_driver_vioscsi_disk': 'RHEVM3-13190',
        'test_driver_vioserial': 'RHEVM3-13191',
        'test_driver_network': 'RHEVM3-13192',
        'test_driver_usb_bus': 'RHEVM3-13193',
        'test_driver_usb_host_controller': 'RHEVM3-13194',
        'test_driver_viostor': 'RHEVM3-13195',
        'test_driver_qxl_gpu': 'RHEVM3-13196',
        'test_driver_balloon': 'RHEVM3-13197',
        'checkServiceAgent': 'RHEVM3-13198',
        'checkServiceQemuGA': 'RHEVM3-13199',
        'checkServiceUSBRedirector': 'RHEVM3-13200',
        'checkServiceSpiceAgent': 'RHEVM3-13201',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13202',
    }


class Windows2008_32b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 32bit.
    """
    __test__ = False
    diskName = config.WIN2008_DISK_32b
    UNSUPPORTED = WindowsServer.UNSUPPORTED + ['test_driver_qxl_gpu']


class Windows2008_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008 64bit.
    """
    __test__ = False
    diskName = config.WIN2008_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13253',
        'checkProductSpice': 'RHEVM3-13254',
        'checkProductSerial': 'RHEVM3-13255',
        'checkProductBlock': 'RHEVM3-13256',
        'checkProductBalloon': 'RHEVM3-13257',
        'checkProductUSB': 'RHEVM3-13258',
        'checkProductQemuAgent': 'RHEVM3-13259',
        'checkProductSSO': 'RHEVM3-13260',
        'checkProductSpiceAgent': 'RHEVM3-13261',
        'checkProductAgent': 'RHEVM3-13262',
        'checkProductSCSI': 'RHEVM3-13263',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13264',
        'test_driver_vioscsi_disk': 'RHEVM3-13265',
        'test_driver_vioserial': 'RHEVM3-13266',
        'test_driver_network': 'RHEVM3-13267',
        'test_driver_usb_bus': 'RHEVM3-13268',
        'test_driver_usb_host_controller': 'RHEVM3-13269',
        'test_driver_viostor': 'RHEVM3-13270',
        'test_driver_qxl_gpu': 'RHEVM3-13271',
        'test_driver_balloon': 'RHEVM3-13272',
        'checkServiceAgent': 'RHEVM3-13273',
        'checkServiceQemuGA': 'RHEVM3-13274',
        'checkServiceUSBRedirector': 'RHEVM3-13275',
        'checkServiceSpiceAgent': 'RHEVM3-13276',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13277',
    }
    UNSUPPORTED = WindowsServer.UNSUPPORTED + ['test_driver_qxl_gpu']


class Windows2008R2_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 64bit.
    """
    __test__ = True
    diskName = config.WIN2008R2_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13303',
        'checkProductSpice': 'RHEVM3-13304',
        'checkProductSerial': 'RHEVM3-13305',
        'checkProductBlock': 'RHEVM3-13306',
        'checkProductBalloon': 'RHEVM3-13307',
        'checkProductUSB': 'RHEVM3-13308',
        'checkProductQemuAgent': 'RHEVM3-13309',
        'checkProductSSO': 'RHEVM3-13310',
        'checkProductSpiceAgent': 'RHEVM3-13311',
        'checkProductAgent': 'RHEVM3-13312',
        'checkProductSCSI': 'RHEVM3-13313',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13314',
        'test_driver_vioscsi_disk': 'RHEVM3-13315',
        'test_driver_vioserial': 'RHEVM3-13316',
        'test_driver_network': 'RHEVM3-13317',
        'test_driver_usb_bus': 'RHEVM3-13318',
        'test_driver_usb_host_controller': 'RHEVM3-13319',
        'test_driver_viostor': 'RHEVM3-13320',
        'test_driver_qxl_gpu': 'RHEVM3-13321',
        'test_driver_balloon': 'RHEVM3-13322',
        'checkServiceAgent': 'RHEVM3-13323',
        'checkServiceQemuGA': 'RHEVM3-13324',
        'checkServiceUSBRedirector': 'RHEVM3-13325',
        'checkServiceSpiceAgent': 'RHEVM3-13326',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13327',
    }
    UNSUPPORTED = WindowsServer.UNSUPPORTED


class Windows2012_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 64bit.
    """
    __test__ = True
    diskName = config.WIN2012_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13328',
        'checkProductSpice': 'RHEVM3-13329',
        'checkProductSerial': 'RHEVM3-13330',
        'checkProductBlock': 'RHEVM3-13331',
        'checkProductBalloon': 'RHEVM3-13332',
        'checkProductUSB': 'RHEVM3-13333',
        'checkProductQemuAgent': 'RHEVM3-13334',
        'checkProductSSO': 'RHEVM3-13335',
        'checkProductSpiceAgent': 'RHEVM3-13336',
        'checkProductAgent': 'RHEVM3-13337',
        'checkProductSCSI': 'RHEVM3-13338',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13339',
        'test_driver_vioscsi_disk': 'RHEVM3-13340',
        'test_driver_vioserial': 'RHEVM3-13341',
        'test_driver_network': 'RHEVM3-13342',
        'test_driver_usb_bus': 'RHEVM3-13344',
        'test_driver_usb_host_controller': 'RHEVM3-13345',
        'test_driver_viostor': 'RHEVM3-13346',
        'test_driver_qxl_gpu': 'RHEVM3-13347',
        'test_driver_balloon': 'RHEVM3-13348',
        'checkServiceAgent': 'RHEVM3-13349',
        'checkServiceQemuGA': 'RHEVM3-13350',
        'checkServiceUSBRedirector': 'RHEVM3-13351',
        'checkServiceSpiceAgent': 'RHEVM3-13352',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13353',
    }
    UNSUPPORTED = WindowsServer.UNSUPPORTED + ['test_driver_qxl_gpu']


class Windows2012R2_64b(WindowsServer):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 64bit.
    """
    __test__ = True
    diskName = config.WIN2012R2_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13153',
        'checkProductSpice': 'RHEVM3-13154',
        'checkProductSerial': 'RHEVM3-13155',
        'checkProductBlock': 'RHEVM3-13156',
        'checkProductBalloon': 'RHEVM3-13157',
        'checkProductUSB': 'RHEVM3-13158',
        'checkProductQemuAgent': 'RHEVM3-13159',
        'checkProductSSO': 'RHEVM3-13160',
        'checkProductSpiceAgent': 'RHEVM3-13161',
        'checkProductAgent': 'RHEVM3-13162',
        'checkProductSCSI': 'RHEVM3-13163',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13164',
        'test_driver_vioscsi_disk': 'RHEVM3-13165',
        'test_driver_vioserial': 'RHEVM3-13166',
        'test_driver_network': 'RHEVM3-13167',
        'test_driver_usb_bus': 'RHEVM3-13168',
        'test_driver_usb_host_controller': 'RHEVM3-13169',
        'test_driver_viostor': 'RHEVM3-13170',
        'test_driver_qxl_gpu': 'RHEVM3-13171',
        'test_driver_balloon': 'RHEVM3-13172',
        'checkServiceAgent': 'RHEVM3-13173',
        'checkServiceQemuGA': 'RHEVM3-13174',
        'checkServiceUSBRedirector': 'RHEVM3-13175',
        'checkServiceSpiceAgent': 'RHEVM3-13176',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13177',
    }
    UNSUPPORTED = WindowsServer.UNSUPPORTED + ['test_driver_qxl_gpu']


class Windows10_64b(WindowsDesktop):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 10 64bit.
    """
    __test__ = True
    diskName = config.WIN10_DISK_64b
    polarion_map = {
        'checkProductNetwork': 'RHEVM3-13203',
        'checkProductSpice': 'RHEVM3-13204',
        'checkProductSerial': 'RHEVM3-13205',
        'checkProductBlock': 'RHEVM3-13206',
        'checkProductBalloon': 'RHEVM3-13207',
        'checkProductUSB': 'RHEVM3-13208',
        'checkProductQemuAgent': 'RHEVM3-13209',
        'checkProductSSO': 'RHEVM3-13210',
        'checkProductSpiceAgent': 'RHEVM3-13211',
        'checkProductAgent': 'RHEVM3-13212',
        'checkProductSCSI': 'RHEVM3-13213',
        'test_driver_vioscsi_pass_through': 'RHEVM3-13214',
        'test_driver_vioscsi_disk': 'RHEVM3-13215',
        'test_driver_vioserial': 'RHEVM3-13216',
        'test_driver_network': 'RHEVM3-13217',
        'test_driver_usb_bus': 'RHEVM3-13218',
        'test_driver_usb_host_controller': 'RHEVM3-13219',
        'test_driver_viostor': 'RHEVM3-13220',
        'test_driver_qxl_gpu': 'RHEVM3-13221',
        'test_driver_balloon': 'RHEVM3-13222',
        'checkServiceAgent': 'RHEVM3-13223',
        'checkServiceQemuGA': 'RHEVM3-13224',
        'checkServiceUSBRedirector': 'RHEVM3-13225',
        'checkServiceSpiceAgent': 'RHEVM3-13226',
        'checkServiceQemuGAVssProvider': 'RHEVM3-13227',
    }
    UNSUPPORTED = WindowsDesktop.UNSUPPORTED + [
        'test_driver_qxl_gpu',
    ]
