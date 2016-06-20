"""
Test installation of guest tools on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import inspect
import logging
import sys

from art.core_api.apis_utils import TimeoutingSampler
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_storagedomains,
)
from art.unittest_lib import attr, CoreSystemTest as TestCase
from rhevmtests.system.wgt import config

logger = logging.getLogger(__name__)
GUEST_FAMILY = 'Windows'


def import_image(disk_name):
    glance_image = ll_storagedomains.GlanceImage(
        image_name=disk_name,
        glance_repository_name=config.GLANCE_DOMAIN,
    )
    glance_image.import_image(
        destination_storage_domain=config.STORAGE_NAME[0],
        cluster_name=None,
        new_disk_alias=disk_name,
        async=True
    )
    assert glance_image._is_import_success(timeout=1200)
    return glance_image


def setup_module():
    WIN_IMAGES = sorted(
        set([
            x[1].disk_name for x in inspect.getmembers(
                sys.modules[__name__],
                inspect.isclass
            ) if getattr(x[1], '__test__', False)
        ]),
        reverse=True,
    )
    assert len(WIN_IMAGES) > 0, "There are no test cases to run"
    logger.info("Windows images to test: %s", WIN_IMAGES)


@attr(tier=2)
class Windows(TestCase):
    """
    Class that implements testing of windows guest tools.
    Every child(win version) of this class needs to specify relevant
    drivers/services/products to tests.
    """
    __test__ = False
    disk_name = None
    polarion_map = {}  # Store polarion id of specific windows cases

    def __init__(self, *args, **kwargs):
        """ create a copy of method with relevant polarion_id """
        super(Windows, self).__init__(*args, **kwargs)
        pid = self.polarion_map.get(self._testMethodName, None)
        if pid:
            m = getattr(self, self._testMethodName)
            polarion(pid)(m.__func__)

    @classmethod
    def setup_class(cls):
        # Windows VMs have a naming limitation of 15 characters
        cls.vm_name = '%s%s' % (cls.disk_name[:9], cls.disk_name[-6:])
        import_image(cls.disk_name)
        ret = hl_vms.create_windows_vm(
            disk_name=cls.disk_name,
            iso_name=config.CD_WITH_TOOLS,
            agent_url=config.AGENT_URL,
            positive=True,
            vmName=cls.vm_name,
            vmDescription=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            network=config.MGMT_BRIDGE,
            nic=config.NIC_NAME,
            nicType=config.NIC_TYPE_VIRTIO,
            cpu_cores=4,
            memory=4*config.GB,
            ballooning=True,
            serial_number=cls.serial_number,
            os_type=cls.os_type,
        )
        assert ret[0], "Failed to create vm with windows: '%s'" % ret[1]

    @classmethod
    def teardown_class(cls):
        assert ll_vms.removeVm(positive=True, vm=cls.vm_name, stopVM='true')

    def test_guest_info(self):
        """ Check guest info (ip/fqdn) are reported """
        vm = ll_vms.get_vm(self.vm_name)
        guest_info = vm.get_guest_info()
        self.assertTrue(
            len(guest_info.get_ips().get_ip()) > 0,
            "No ip found in guest info"
        )
        self.assertTrue(
            guest_info.get_fqdn() and len(guest_info.get_fqdn()) > 0
        )

    def test_guest_applications(self):
        """ Check guest applications are reported """
        vm = ll_vms.get_vm(self.vm_name)
        apps = ll_vms.get_vm_applications(vm.get_name())
        logger.info("Windows '%s' apps are: %s", self.disk_name, apps)
        self.assertTrue(len(apps) > 0, "Applications are empty")

    def test_guest_os(self):
        """ Check guest OS info is reported """
        vm = ll_vms.get_vm(self.vm_name)
        TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            lambda: True if vm.get_guest_operating_system() is not None
            else False)
        guest_os = vm.get_guest_operating_system()
        logger.info("Guest '%s' os info:", self.vm_name)
        logger.info("Architecture: '%s'", guest_os.get_architecture())
        logger.info("Codename: '%s'", guest_os.get_codename())
        logger.info("Family: '%s'", guest_os.get_family())
        self.assertTrue(
            self.architecture == guest_os.get_architecture(),
            "Windows has wrong arch '%s', should be '%s'" % (
                guest_os.get_architecture(),
                self.architecture
            )
        )
        self.assertTrue(
            GUEST_FAMILY == guest_os.get_family(),
            "Guest os family is windows: '%s'" % guest_os.get_family()
        )
        self.assertTrue(
            self.codename == guest_os.get_codename(),
            "Guest codename '%s' should be '%s'" % (
                guest_os.get_codename(),
                self.codename
            )
        )

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        vm = ll_vms.get_vm(self.vm_name)
        TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            lambda: True if vm.get_guest_time_zone() is not None else False)
        guest_timezone = vm.get_guest_time_zone()
        logger.info(
            "Guest timezone name is '%s', offset: '%s'",
            guest_timezone.get_name(),
            guest_timezone.get_utc_offset()
        )
        self.assertTrue(
            len(guest_timezone.get_name()) > 0, 'Timezone name is empty'
        )
        self.assertTrue(
            len(guest_timezone.get_utc_offset()) > 0, "UTC offset is empty"
        )

# **IMPORTANT**
# py.test testclass execution order is same as order of classes in file
# we import images alphabetically so please keep order of classes same
# If in doubt run $grep '^class ' test_windows.py | sort


class Win2008R2_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 64bit.
    """
    __test__ = True
    disk_name = 'Win2008R2_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2008R2_64B['serial_number']
    architecture = config.WIN2008R2_64B['architecture']
    codename = config.WIN2008R2_64B['codename']
    os_type = config.ENUMS['windows2008r2x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14429',
        'test_guest_info': 'RHEVM3-14430',
        'test_guest_timezone': 'RHEVM3-14431',
        'test_guest_os': 'RHEVM3-14432',
    }


class Win2008R2_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 core 64bit.
    """
    __test__ = True
    disk_name = 'Win2008R2_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2008R2_64B['serial_number']
    architecture = config.WIN2008R2_64B['architecture']
    codename = config.WIN2008R2_64B['codename']
    os_type = config.ENUMS['windows2008r2x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM-14780',
        'test_guest_info': 'RHEVM-14781',
        'test_guest_timezone': 'RHEVM-14782',
        'test_guest_os': 'RHEVM-14783',
    }

    # Windows2008 Core needs restart after GT installation to work properly
    @classmethod
    def setup_class(cls):
        super(Win2008R2_CI_core_64b, cls).setup_class()
        ll_vms.restartVm(cls.vm_name, wait_for_ip=True)


class Win2012R2_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 64bit.
    """
    __test__ = True
    disk_name = 'Win2012R2_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2012R2_64B['serial_number']
    architecture = config.WIN2012R2_64B['architecture']
    codename = config.WIN2012R2_64B['codename']
    os_type = config.ENUMS['windows2012r2x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14405',
        'test_guest_info': 'RHEVM3-14406',
        'test_guest_timezone': 'RHEVM3-14407',
        'test_guest_os': 'RHEVM3-14408',
    }


class Win2012R2_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 core 64bit.
    """
    __test__ = True
    disk_name = 'Win2012R2_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2012R2_64B['serial_number']
    architecture = config.WIN2012R2_64B['architecture']
    codename = config.WIN2012R2_64B['codename']
    os_type = config.ENUMS['windows2012r2x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14769',
        'test_guest_info': 'RHEVM3-14770',
        'test_guest_timezone': 'RHEVM3-14771',
        'test_guest_os': 'RHEVM3-14772',
    }


class Win2012_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 64bit.
    """
    __test__ = True
    disk_name = 'Win2012_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2012_64B['serial_number']
    architecture = config.WIN2012_64B['architecture']
    codename = config.WIN2012_64B['codename']
    os_type = config.ENUMS['windows2012x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14433',
        'test_guest_info': 'RHEVM3-14434',
        'test_guest_timezone': 'RHEVM3-14435',
        'test_guest_os': 'RHEVM3-14436',
    }


class Win2012_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 core 64bit.
    """
    __test__ = True
    disk_name = 'Win2012_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2012_64B['serial_number']
    architecture = config.WIN2012_64B['architecture']
    codename = config.WIN2012_64B['codename']
    os_type = config.ENUMS['windows2012x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM-14784',
        'test_guest_info': 'RHEVM-14785',
        'test_guest_timezone': 'RHEVM-14786',
        'test_guest_os': 'RHEVM-14787',
    }


class Win7_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    __test__ = True
    disk_name = 'Win7_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN7_32B['serial_number']
    architecture = config.WIN7_32B['architecture']
    codename = config.WIN7_32B['codename']
    os_type = config.ENUMS['windows7']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14425',
        'test_guest_info': 'RHEVM3-14426',
        'test_guest_timezone': 'RHEVM3-14427',
        'test_guest_os': 'RHEVM3-14428',
    }


class Win7_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    disk_name = 'Win7_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN7_64B['serial_number']
    architecture = config.WIN7_64B['architecture']
    codename = config.WIN7_64B['codename']
    os_type = config.ENUMS['windows7x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14437',
        'test_guest_info': 'RHEVM3-14438',
        'test_guest_timezone': 'RHEVM3-14439',
        'test_guest_os': 'RHEVM3-14440',
    }


class Win8_1_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 32bit.
    """
    # https://bugzilla.redhat.com/show_bug.cgi?id=1318623
    __test__ = False  # Enable when there is support for Win8.1
    disk_name = 'Win8_1_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN8_1_32B['serial_number']
    architecture = config.WIN8_1_32B['architecture']
    codename = config.WIN8_1_32B['codename']
    os_type = config.ENUMS['windows8']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14409',
        'test_guest_info': 'RHEVM3-14410',
        'test_guest_timezone': 'RHEVM3-14411',
        'test_guest_os': 'RHEVM3-14412',
    }


class Win8_1_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 64bit.
    """
    # https://bugzilla.redhat.com/show_bug.cgi?id=1318623
    __test__ = False  # Enable when there is support for Win8.1
    disk_name = 'Win8_1_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN8_1_64B['serial_number']
    architecture = config.WIN8_1_64B['architecture']
    codename = config.WIN8_1_64B['codename']
    os_type = config.ENUMS['windows8x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14417',
        'test_guest_info': 'RHEVM3-14418',
        'test_guest_timezone': 'RHEVM3-14419',
        'test_guest_os': 'RHEVM3-14420',
    }


class Win8_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8 32bit.
    """
    __test__ = True
    disk_name = 'Win8_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN8_32B['serial_number']
    architecture = config.WIN8_32B['architecture']
    codename = config.WIN8_32B['codename']
    os_type = config.ENUMS['windows8']
    polarion_map = {
        'test_guest_applications': 'RHEVM-14792',
        'test_guest_info': 'RHEVM-14793',
        'test_guest_timezone': 'RHEVM-14794',
        'test_guest_os': 'RHEVM-14795',
    }


class Win8_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8 64bit.
    """
    __test__ = True
    disk_name = 'Win8_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN8_64B['serial_number']
    architecture = config.WIN8_64B['architecture']
    codename = config.WIN8_64B['codename']
    os_type = config.ENUMS['windows8x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM-14788',
        'test_guest_info': 'RHEVM-14789',
        'test_guest_timezone': 'RHEVM-14790',
        'test_guest_os': 'RHEVM-14791',
    }
