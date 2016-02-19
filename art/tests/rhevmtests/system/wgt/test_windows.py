"""
Test installation of guest tools on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import copy
import inspect
import logging
import sys

from art.rhevm_api.tests_lib.high_level import vms as hl_vms
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_storagedomains,
)
from art.unittest_lib import attr, CoreSystemTest as TestCase
from rhevmtests.system.wgt import config

from functools import wraps


logger = logging.getLogger(__name__)
WIN_IMAGES = []
GLANCE_IMAGE = None
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
    return glance_image


def setup_module():
    global WIN_IMAGES, GLANCE_IMAGE
    WIN_IMAGES = [
        x[1].disk_name for x in sorted(
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
    disk_name = None
    glance_image = None
    polarion_map = {}  # Store polarion id of specific windows cases

    def __init__(self, *args, **kwargs):
        """ create a copy of method with relevant polarion_id """
        super(Windows, self).__init__(*args, **kwargs)
        pid = self.polarion_map.get(self._testMethodName, None)
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
            assert GLANCE_IMAGE._is_import_success(timeout=1200)
        try:
            GLANCE_IMAGE = import_image(WIN_IMAGES.pop())
        except IndexError:
            GLANCE_IMAGE = None

    @classmethod
    def setup_class(cls):
        cls.vm_name = cls.disk_name
        cls.__prepare_image()
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
            nicType=config.NIC_TYPE_E1000,
            cpu_cores=4,
            memory=4*config.GB,
            ballooning=True,
            serial_number=cls.serial_number,
        ),
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


class Windows7_64bit(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    __test__ = True
    disk_name = 'Windows7_CI_64b_Disk1'
    serial_number = '0fcf2a60-243d-2s1o-1o5k-3c970e16e256'
    architecture = 'x86_64'
    codename = 'Win 7'
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14437',
        'test_guest_info': 'RHEVM3-14438',
        'test_guest_timezone': 'RHEVM3-14439',
        'test_guest_os': 'RHEVM3-14440',
    }
