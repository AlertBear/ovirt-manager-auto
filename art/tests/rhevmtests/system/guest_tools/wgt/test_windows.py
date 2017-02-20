"""
Test installation of guest tools on all windows machines. Then check if all
product/services/drivers relevant to windows machine are installed/running.
"""
import logging
import pytest
import re
import subprocess

from art.core_api.apis_utils import TimeoutingSampler
from art.rhevm_api.utils.name2ip import LookUpVMIpByName
from art.test_handler.tools import polarion
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    storagedomains as ll_sds,
    disks as ll_disks
)
from art.rhevm_api.tests_lib.high_level import (
    vms as hl_vms,
    storagedomains as hl_sds
)
from art.unittest_lib import attr, CoreSystemTest as TestCase, testflow
from rhevmtests.system.guest_tools.wgt import config

logger = logging.getLogger(__name__)
GUEST_FAMILY = 'Windows'
cd_with_tools = 'RHEV-toolsSetup_{}.iso'


def get_latest_gt_iso_version_from_latest_repo_and_change_variable():
    global cd_with_tools
    cd_with_tools = cd_with_tools.format(
        re.search(
            "guest-tools-iso-(\d+\.\d+-\d+)",
            subprocess.check_output(["curl", config.REPO]).decode("utf-8")
        ).group(1).replace('-', '_')
    )


def import_image(disk_name):
    glance_image = ll_sds.GlanceImage(
        image_name=disk_name,
        glance_repository_name=config.GLANCE_DOMAIN,
        timeout=3600
    )
    assert glance_image.import_image(
        destination_storage_domain=config.STORAGE_NAME[0],
        cluster_name=None,
        new_disk_alias=disk_name
    )
    return glance_image


@pytest.fixture(scope='module', autouse=True)
def module_setup(request):
    def fin_vms():
        testflow.teardown("Remove remaining Windows VMs")
        for vm in ll_vms.get_vms_from_cluster(config.CLUSTER_NAME[0]):
            if vm.startswith("Win"):
                ll_vms.removeVm(positive=True, vm=vm, stopVM=True)

        testflow.teardown("Remove remaining Windows disks")
        for disk in ll_disks.get_all_disks():
            if disk.get_alias().startswith("Win"):
                ll_disks.deleteDisk(True, disk.get_alias())
    request.addfinalizer(fin_vms)

    get_latest_gt_iso_version_from_latest_repo_and_change_variable()
    if not ll_sds.is_storage_domain_active(
            config.DC_NAME[0], config.ISO_DOMAIN_NAME
    ):
        def fin_sd():
            testflow.teardown("Detach and deactivate ISO storage domain")
            hl_sds.detach_and_deactivate_domain(
                datacenter=config.DC_NAME[0],
                domain=config.ISO_DOMAIN_NAME,
                engine=config.ENGINE
            )
        request.addfinalizer(fin_sd)

        testflow.setup("Attach ISO storage domain")
        assert ll_sds.attachStorageDomain(
            True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
        )
        testflow.setup("Activate ISO storage domain")
        assert ll_sds.activateStorageDomain(
            True, config.DC_NAME[0], config.ISO_DOMAIN_NAME
        )


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

    @pytest.fixture(scope='class', autouse=True)
    def setup_vm(self, request):
        # Windows VMs have a naming limitation of 15 characters
        cls = request.cls

        def fin():
            testflow.teardown("Remove VM %s", cls.vm_name)
            ll_vms.removeVm(positive=True, vm=cls.vm_name, stopVM='true')
        request.addfinalizer(fin)

        cls.vm_name = '%s' % ((cls.disk_name[:9] + cls.disk_name[-6:]) if
                              len(cls.disk_name) > 15 else cls.disk_name
                              )
        testflow.setup("Import image %s", cls.disk_name)
        import_image(cls.disk_name)
        testflow.setup("Create windows VM %s", cls.vm_name)
        ret = hl_vms.create_windows_vm(
            disk_name=cls.disk_name,
            iso_name=cd_with_tools,
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
        ll_vms.wait_for_vm_ip(cls.vm_name, timeout=60)

    def check_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        vm = ll_vms.get_vm(self.vm_name)
        testflow.step("Check if guest agent is reporting IP address")
        assert len(
            LookUpVMIpByName('', '').get_ip(self.vm_name)
        ) > 0, "No ip found in guest info"
        testflow.step("Check if guest agent is reporting FQDN")
        assert vm.get_fqdn() and len(vm.get_fqdn()) > 0

    def check_guest_applications(self):
        """ Check guest applications are reported """
        vm = ll_vms.get_vm(self.vm_name)
        apps = ll_vms.get_vm_applications(vm.get_name())
        logger.info("Windows '%s' apps are: %s", self.disk_name, apps)
        testflow.step("Check if guest agent is reporting applications")
        assert len(apps) > 0, "Applications are empty"
        for app in apps:
            testflow.step("Check if app %s is reporting version", app)
            try:
                re.search("[ -]\d+.*", app).group(0)[1:]
            except AttributeError:
                logger.error("App %s is not reporting version", app)

    def check_guest_os(self):
        """ Check guest OS info is reported """
        vm = ll_vms.get_vm(self.vm_name)
        TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            lambda: vm.get_guest_operating_system() is not None
        )
        guest_os = vm.get_guest_operating_system()
        logger.info("Guest '%s' os info:", self.vm_name)
        logger.info("Architecture: '%s'", guest_os.get_architecture())
        logger.info("Codename: '%s'", guest_os.get_codename())
        logger.info("Family: '%s'", guest_os.get_family())
        testflow.step("Check if guest agent reports correct architecture")
        assert self.architecture == guest_os.get_architecture(), (
            "Windows has wrong arch '%s', should be '%s'" %
            (guest_os.get_architecture(), self.architecture)
        )
        testflow.step("Check if guest agent reports correct OS family")
        assert GUEST_FAMILY == guest_os.get_family(), (
            "Guest os family is windows: '%s'" % guest_os.get_family()
        )
        testflow.step("Check if guest agent reports correct OS codename")
        assert self.codename == guest_os.get_codename(), (
            "Guest codename '%s' should be '%s'" %
            (guest_os.get_codename(), self.codename)
        )

    def check_guest_timezone(self):
        """ Check guest timezone reported """
        vm = ll_vms.get_vm(self.vm_name)
        TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            lambda: vm.get_guest_time_zone() is not None
        )
        guest_timezone = vm.get_guest_time_zone()
        logger.info(
            "Guest timezone name is '%s', offset: '%s'",
            guest_timezone.get_name(),
            guest_timezone.get_utc_offset()
        )
        testflow.step("Check if guest agent reports timezone name")
        assert len(guest_timezone.get_name()) > 0, 'Timezone name is empty'
        testflow.step("Check if guest agent reports UTC offset")
        assert len(guest_timezone.get_utc_offset()) > 0, "UTC offset is empty"

# **IMPORTANT**
# py.test testclass execution order is same as order of classes in file
# we import images alphabetically so please keep order of classes same
# If in doubt run $grep '^class ' test_windows.py | sort


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14430',
        'test_guest_timezone': 'RHEVM3-14431',
        'test_guest_os': 'RHEVM3-14432',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM-14781',
        'test_guest_timezone': 'RHEVM-14782',
        'test_guest_os': 'RHEVM-14783',
    }

    # Windows2008 Core needs restart after GT installation to work properly
    @classmethod
    @pytest.fixture(scope='class', autouse=True)
    def setup_w2008r2_core(cls):
        ll_vms.restartVm(cls.vm_name, wait_for_ip=True)

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=2)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14406',
        'test_guest_timezone': 'RHEVM3-14407',
        'test_guest_os': 'RHEVM3-14408',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14770',
        'test_guest_timezone': 'RHEVM3-14771',
        'test_guest_os': 'RHEVM3-14772',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14434',
        'test_guest_timezone': 'RHEVM3-14435',
        'test_guest_os': 'RHEVM3-14436',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM-14785',
        'test_guest_timezone': 'RHEVM-14786',
        'test_guest_os': 'RHEVM-14787',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14426',
        'test_guest_timezone': 'RHEVM3-14427',
        'test_guest_os': 'RHEVM3-14428',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=2)
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
        'test_vm_ip_fqdn_info': 'RHEVM3-14438',
        'test_guest_timezone': 'RHEVM3-14439',
        'test_guest_os': 'RHEVM3-14440',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
class Win8_1_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 32bit.
    """
    __test__ = True
    disk_name = 'Win8_1_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN8_1_32B['serial_number']
    architecture = config.WIN8_1_32B['architecture']
    codename = config.WIN8_1_32B['codename']
    os_type = config.ENUMS['windows8']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14409',
        'test_vm_ip_fqdn_info': 'RHEVM3-14410',
        'test_guest_timezone': 'RHEVM3-14411',
        'test_guest_os': 'RHEVM3-14412',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=2)
class Win8_1_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 64bit.
    """
    __test__ = True
    disk_name = 'Win8_1_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN8_1_64B['serial_number']
    architecture = config.WIN8_1_64B['architecture']
    codename = config.WIN8_1_64B['codename']
    os_type = config.ENUMS['windows8x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14417',
        'test_vm_ip_fqdn_info': 'RHEVM3-14418',
        'test_guest_timezone': 'RHEVM3-14419',
        'test_guest_os': 'RHEVM3-14420',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM-14793',
        'test_guest_timezone': 'RHEVM-14794',
        'test_guest_os': 'RHEVM-14795',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=3)
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
        'test_vm_ip_fqdn_info': 'RHEVM-14789',
        'test_guest_timezone': 'RHEVM-14790',
        'test_guest_os': 'RHEVM-14791',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()


@attr(tier=2)
class Windows10_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 10 64bit.
    """
    __test__ = True
    disk_name = 'Win10_CI_rhevm_64b'
    serial_number = config.WIN10_64B['serial_number']
    architecture = config.WIN10_64B['architecture']
    codename = config.WIN10_64B['codename']
    os_type = config.ENUMS['windows10x64']
    polarion_map = {
        'test_guest_applications': 'RHEVM3-14413',
        'test_vm_ip_fqdn_info': 'RHEVM3-14414',
        'test_guest_timezone': 'RHEVM3-14415',
        'test_guest_os': 'RHEVM3-14416',
    }

    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()
