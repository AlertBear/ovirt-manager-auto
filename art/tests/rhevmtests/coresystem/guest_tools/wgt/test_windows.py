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
    disks as ll_disks,
    clusters as ll_clusters
)
from art.rhevm_api.tests_lib.high_level import storagedomains as hl_sds
from art.unittest_lib import (
    tier2,
    tier3,
)
from art.unittest_lib import CoreSystemTest as TestCase, testflow
from rhevmtests.coresystem.guest_tools.wgt import config
from rhevmtests.fixtures import (  # noqa: F401
    register_windows_templates,
)

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


@pytest.fixture(scope='module', autouse=True)  # noqa: F811
def module_setup(request, register_windows_templates):
    def fin_cluster():
        testflow.teardown(
            "Set %s cluster CPU level on cluster %s",
            old_cpu_level, config.CLUSTER_NAME[0]
        )
        ll_clusters.set_cluster_cpu_level(
            cluster_name=config.CLUSTER_NAME[0],
            cluster_cpu_level=old_cpu_level
        )
    request.addfinalizer(fin_cluster)

    testflow.setup(
        "Set %s cluster CPU level on cluster %s",
        config.WESTMERE_CL_CPU_LVL, config.CLUSTER_NAME[0]
    )
    old_cpu_level = ll_clusters.get_cluster_cpu_level(config.CLUSTER_NAME[0])
    if not ll_clusters.set_cluster_cpu_level(
        cluster_name=config.CLUSTER_NAME[0],
        cluster_cpu_level=config.WESTMERE_CL_CPU_LVL
    ):
        pytest.skip("Unsupported cluster CPU level")

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
    disk_name = None
    disk_interface = config.ENUMS['interface_virtio_scsi']

    @pytest.fixture(scope='class', autouse=True)
    def setup_vm(self, request):
        # Windows VMs have a naming limitation of 15 characters
        cls = request.cls

        def fin():
            testflow.teardown("Remove VM %s", cls.vm_name)
            ll_vms.removeVm(positive=True, vm=cls.vm_name, stopVM=True)
        request.addfinalizer(fin)

        cls.vm_name = '%s' % (
            (cls.disk_name[:9] + cls.disk_name[-6:])
            if len(cls.disk_name) > 15
            else cls.disk_name
        )
        testflow.setup("Create VM %s", cls.vm_name)
        template_name = cls.disk_name + "_template"
        ll_vms.createVm(
            positive=True,
            template=template_name,
            vmName=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            cpu_cores=4,
            memory=4*config.GB,
            ballooning=True,
            serial_number=cls.serial_number
        )
        testflow.setup("Update VM %s", cls.vm_name)
        ll_vms.updateVm(
            positive=True,
            vm=cls.vm_name,
            os_type=cls.os_type,
            time_zone=config.TIMEZONE
        )
        testflow.setup("Add nic to VM %s", cls.vm_name)
        ll_vms.addNic(
            positive=True,
            vm=cls.vm_name,
            name=config.NIC_NAME,
            network=config.MGMT_BRIDGE
        )
        testflow.setup("Update disk %s of VM %s", cls.disk_name, cls.vm_name)
        ll_disks.updateDisk(
            positive=True,
            vmName=cls.vm_name,
            alias=cls.disk_name,
            bootable=True,
            interface=self.disk_interface
        )
        testflow.setup("Run once VM %s", cls.vm_name)
        ll_vms.runVmOnce(
            positive=True,
            vm=cls.vm_name,
            use_sysprep=True,
            wait_for_state=config.VM_UP
        )
        ll_vms.changeCDWhileRunning(cls.vm_name, cd_with_tools)
        for sample in TimeoutingSampler(
            config.GUEST_TOOLS_INSTALLED_TIMEOUT, config.SAMPLER_SLEEP,
            LookUpVMIpByName('', '').get_ip, cls.vm_name, check_mac=False
        ):
            if sample:
                break

    def check_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        testflow.step("Check if guest agent is reporting IP address")
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            LookUpVMIpByName('', '').get_ip, self.vm_name, check_mac=False
        ):
            if len(sample) > 0:
                break
        testflow.step("Check if guest agent is reporting FQDN")
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            ll_vms.get_vm, self.vm_name
        ):
            if sample.get_fqdn() and len(sample.get_fqdn()) > 0:
                break

    def check_guest_applications(self):
        """ Check guest's applications are reported """
        apps = None
        testflow.step("Check if guest agent is reporting applications")
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            ll_vms.get_vm, self.vm_name
        ):
            apps = ll_vms.get_vm_applications(sample.get_name())
            if len(apps) > 0:
                break
        logger.info("Windows '%s' apps are: %s", self.disk_name, apps)
        for app in apps:
            testflow.step("Check if app %s is reporting version", app)
            try:
                re.search("[ -]\d+.*", app).group(0)[1:]
            except AttributeError:
                logger.error("App %s is not reporting version", app)

    def check_guest_os(self):
        """ Check guest OS info is reported """
        guest_os = None
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            ll_vms.get_vm_obj, self.vm_name, all_content=True
        ):
            guest_os = sample.get_guest_operating_system()
            if guest_os:
                break
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
        """ Check guest timezone is reported """
        guest_timezone = None
        for sample in TimeoutingSampler(
            config.SAMPLER_TIMEOUT, config.SAMPLER_SLEEP,
            ll_vms.get_vm_obj, self.vm_name, all_content=True
        ):
            guest_timezone = sample.get_guest_time_zone()
            if guest_timezone:
                break
        logger.info(
            "Guest timezone name is '%s', offset: '%s'",
            guest_timezone.get_name(),
            guest_timezone.get_utc_offset()
        )
        testflow.step("Check if guest agent reports timezone name")
        assert len(guest_timezone.get_name()) > 0, 'Timezone name is empty'
        testflow.step("Check if guest agent reports UTC offset")
        assert len(guest_timezone.get_utc_offset()) > 0, "UTC offset is empty"

    def check_function_continuity(self):
        """ Check that GA works after migration """
        testflow.step("Migrate VM %s", self.vm_name)
        assert ll_vms.migrateVm(True, self.vm_name)
        self.check_vm_ip_fqdn_info()


@tier3
class TestWin2008R2_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 64bit.
    """
    disk_name = 'Win2008R2_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2008R2_64B['serial_number']
    architecture = config.WIN2008R2_64B['architecture']
    codename = config.WIN2008R2_64B['codename']
    os_type = config.ENUMS['windows2008r2x64']

    @polarion("RHEVM3-14429")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14430")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14432")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14431")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22236")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin2008R2_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2008R2 core 64bit.
    """
    disk_name = 'Win2008R2_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2008R2_64B['serial_number']
    architecture = config.WIN2008R2_64B['architecture']
    codename = config.WIN2008R2_64B['codename']
    os_type = config.ENUMS['windows2008r2x64']

    @polarion("RHEVM-14780")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-14781")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-14783")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-14782")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22238")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier2
class TestWin2012R2_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 64bit.
    """
    disk_name = 'Win2012R2_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2012R2_64B['serial_number']
    architecture = config.WIN2012R2_64B['architecture']
    codename = config.WIN2012R2_64B['codename']
    os_type = config.ENUMS['windows2012r2x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14405")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14406")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14408")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14407")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22245")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin2012R2_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012R2 core 64bit.
    """
    disk_name = 'Win2012R2_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2012R2_64B['serial_number']
    architecture = config.WIN2012R2_64B['architecture']
    codename = config.WIN2012R2_64B['codename']
    os_type = config.ENUMS['windows2012r2x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14769")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14770")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14772")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14771")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22244")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin2012_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 64bit.
    """
    disk_name = 'Win2012_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN2012_64B['serial_number']
    architecture = config.WIN2012_64B['architecture']
    codename = config.WIN2012_64B['codename']
    os_type = config.ENUMS['windows2012x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14433")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14434")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14436")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14435")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22239")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin2012_CI_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2012 core 64bit.
    """
    disk_name = 'Win2012_CI_%s_core_64b' % config.PRODUCT
    serial_number = config.WIN2012_64B['serial_number']
    architecture = config.WIN2012_64B['architecture']
    codename = config.WIN2012_64B['codename']
    os_type = config.ENUMS['windows2012x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM-14784")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-14785")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-14787")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-14786")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22240")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin7_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 32bit.
    """
    disk_name = 'Win7_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN7_32B['serial_number']
    architecture = config.WIN7_32B['architecture']
    codename = config.WIN7_32B['codename']
    os_type = config.ENUMS['windows7']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14425")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14426")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14428")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14427")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22235")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier2
class TestWin7_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 7 64bit.
    """
    disk_name = 'Win7_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN7_64B['serial_number']
    architecture = config.WIN7_64B['architecture']
    codename = config.WIN7_64B['codename']
    os_type = config.ENUMS['windows7x64']

    @polarion("RHEVM3-14437")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14438")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14440")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14439")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22241")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin8_1_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 32bit.
    """
    disk_name = 'Win8_1_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN8_1_32B['serial_number']
    architecture = config.WIN8_1_32B['architecture']
    codename = config.WIN8_1_32B['codename']
    os_type = config.ENUMS['windows8']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14409")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14410")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14412")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14411")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22243")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier2
class TestWin8_1_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8.1 64bit.
    """
    disk_name = 'Win8_1_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN8_1_64B['serial_number']
    architecture = config.WIN8_1_64B['architecture']
    codename = config.WIN8_1_64B['codename']
    os_type = config.ENUMS['windows8x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM3-14417")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14418")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14420")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14419")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22237")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin8_CI_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8 32bit.
    """
    disk_name = 'Win8_CI_%s_32b' % config.PRODUCT
    serial_number = config.WIN8_32B['serial_number']
    architecture = config.WIN8_32B['architecture']
    codename = config.WIN8_32B['codename']
    os_type = config.ENUMS['windows8']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM-14792")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-14793")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-14795")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-14794")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22242")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWin8_CI_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 8 64bit.
    """
    disk_name = 'Win8_CI_%s_64b' % config.PRODUCT
    serial_number = config.WIN8_64B['serial_number']
    architecture = config.WIN8_64B['architecture']
    codename = config.WIN8_64B['codename']
    os_type = config.ENUMS['windows8x64']
    disk_interface = config.ENUMS['interface_virtio']

    @polarion("RHEVM-14788")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-14789")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-14791")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-14790")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22234")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWindows10_32b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 10 32bit.
    """
    disk_name = 'Win10_CI_rhevm_32b'
    serial_number = config.WIN10_32B['serial_number']
    architecture = config.WIN10_32B['architecture']
    codename = config.WIN10_32B['codename']
    os_type = config.ENUMS['windows10']

    @polarion("RHEVM-19563")
    def test_guest_applications(self):
        """ Check guest applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-19564")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-19566")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-19565")
    def test_guest_timezone(self):
        """ Check guest timezone reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22248")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier2
class TestWindows10_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 10 64bit.
    """
    disk_name = 'Win10_CI_rhevm_64b'
    serial_number = config.WIN10_64B['serial_number']
    architecture = config.WIN10_64B['architecture']
    codename = config.WIN10_64B['codename']
    os_type = config.ENUMS['windows10x64']

    @polarion("RHEVM3-14413")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM3-14414")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM3-14416")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM3-14415")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22249")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier3
class TestWindows2016_core_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2016 core 64bit.
    """
    disk_name = 'Win2016_CI_rhevm_core_64b'
    serial_number = config.WIN2016_64B['serial_number']
    architecture = config.WIN2016_64B['architecture']
    codename = config.WIN2016_64B['codename']
    os_type = config.ENUMS['windows2016x64']

    @polarion("RHEVM-19384")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-19385")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-19387")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-19386")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22246")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()


@tier2
class TestWindows2016_64b(Windows):
    """
    Test that all product and services exist on windows machine after
    GuestTools installation for windows 2016 64bit.
    """
    disk_name = 'Win2016_CI_rhevm_64b'
    serial_number = config.WIN2016_64B['serial_number']
    architecture = config.WIN2016_64B['architecture']
    codename = config.WIN2016_64B['codename']
    os_type = config.ENUMS['windows2016x64']

    @polarion("RHEVM-19380")
    def test_guest_applications(self):
        """ Check guest's applications are reported """
        self.check_guest_applications()

    @polarion("RHEVM-19381")
    def test_vm_ip_fqdn_info(self):
        """ Check vm ip/fqdn are reported """
        self.check_vm_ip_fqdn_info()

    @polarion("RHEVM-19383")
    def test_guest_os(self):
        """ Check guest OS info is reported """
        self.check_guest_os()

    @polarion("RHEVM-19382")
    def test_guest_timezone(self):
        """ Check guest timezone is reported """
        self.check_guest_timezone()

    @polarion("RHEVM-22247")
    def test_function_continuity(self):
        """ Check if GA data is reported after migration """
        self.check_function_continuity()
