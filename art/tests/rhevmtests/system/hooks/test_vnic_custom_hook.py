"""
Testing vnic profile hooks: after_update_device_fail,  after_update_device
before_update_device, after_nic_hotunplug, before_nic_hotunplug,
after_nic_hotplug, before_nic_hotplug
"""

import logging
from time import sleep

import pytest
from os import path

from art.rhevm_api.tests_lib.low_level import hooks, vms, networks
from art.rhevm_api.utils import test_utils
from art.rhevm_api.utils.resource_utils import runMachineCommand
from art.test_handler.tools import polarion
from art.unittest_lib import CoreSystemTest as TestCase, testflow, attr
from rhevmtests.system.hooks import config

SPEED = "1000"
CUSTOM_PROPERTIES = "speed={0};port_mirroring=True;bandwidth=10000".format(
    SPEED
)
CUSTOM_PROPERTIES2 = "port_mirroring=True;bandwidth=10000"
REMOVE_HOOKS = "rm -f /var/tmp/*.hook"
HOOK_PATH = "/usr/libexec/vdsm/hooks"
TMP = "/var/tmp"
PROFILE_A = "profile_a"
PROFILE_B = "profile_b"
PROFILE_BAD_A = "profile_bad_a"
PROFILE_BAD_B = "profile_bad_b"
SCRIPT_TYPES = {"python": "py", "shell": "sh"}
SLEEP_TIME = 15
UPDATE_NIC = "update_nic"
HOTUNPLUG_NIC = "hotunplug_nic"

__test__ = True

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    testflow.setup("Setting up module %s.", __name__)

    testflow.step("Creating a %s VM.", config.HOOKS_VM_NAME)
    assert vms.createVm(
        positive=True,
        vmName=config.HOOKS_VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        display_type=config.DISPLAY_TYPE,
        template=config.TEMPLATE_NAME[0]
    )

    testflow.step("Starting %s VM.", config.HOOKS_VM_NAME)
    assert vms.startVm(
        positive=True,
        vm=config.HOOKS_VM_NAME,
        wait_for_status=config.VM_UP,
        wait_for_ip=True,
        placement_host=config.HOSTS[0] if config.GOLDEN_ENV else None,
    )

    testflow.step(
        "Adding a %s VNIC profile to %s network in %s cluster with custom "
        "properties %s.",
        PROFILE_A,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        CUSTOM_PROPERTIES
    )
    assert networks.add_vnic_profile(
        positive=True,
        name=PROFILE_A,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties=CUSTOM_PROPERTIES
    )

    testflow.step(
        "Adding a %s VNIC profile to %s network in %s cluster with custom "
        "properties %s.",
        PROFILE_B,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        CUSTOM_PROPERTIES2
    )
    assert networks.add_vnic_profile(
        positive=True,
        name=PROFILE_B,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties=CUSTOM_PROPERTIES2
    )

    testflow.step(
        "Checking if it's not possible to add a %s VNIC profile to %s network "
        "in %s cluster with custom properties %s.",
        PROFILE_BAD_A,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        "test=250"
    )
    assert networks.add_vnic_profile(
        positive=False,
        name=PROFILE_BAD_A,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties="test=250"
    )

    testflow.step(
        "Checking if it's not possible to add a %s VNIC profile to %s network "
        "in %s cluster with custom properties %s.",
        PROFILE_BAD_B,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        "speed=abc"
    )
    assert networks.add_vnic_profile(
        positive=False,
        name=PROFILE_BAD_B,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties="speed=abc"
    )

    testflow.step(
        "Adding linked %s nic to %s vm.",
        PROFILE_A,
        config.HOOKS_VM_NAME
    )
    assert vms.addNic(
        positive=True,
        vm=config.HOOKS_VM_NAME,
        name=UPDATE_NIC,
        network=config.MGMT_BRIDGE,
        vnic_profile=PROFILE_A,
        linked=True
    )

    testflow.step(
        "Adding %s nic with profile %s to %s vm.",
        HOTUNPLUG_NIC,
        PROFILE_A,
        config.HOOKS_VM_NAME
    )
    assert vms.addNic(
        positive=True,
        vm=config.HOOKS_VM_NAME,
        name=HOTUNPLUG_NIC,
        network=config.MGMT_BRIDGE,
        vnic_profile=PROFILE_A
    )

    def finalize():
        testflow.teardown("Tearing down %s module.", __name__)

        testflow.step("Removing all hooks from %s.", config.HOSTS_IP[0])
        assert runMachineCommand(
            positive=True,
            ip=config.HOSTS_IP[0],
            user=config.HOSTS_USER,
            password=config.HOSTS_PW,
            cmd=REMOVE_HOOKS
        )[0]

        testflow.step("Removing VM %s.", config.HOOKS_VM_NAME)
        assert vms.removeVm(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            stopVM="true"
        )

        testflow.step("Removing VNIC profile %s.", PROFILE_A)
        networks.remove_vnic_profile(
            positive=True,
            vnic_profile_name=PROFILE_A,
            network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.step("Removing VNIC profile %s.", PROFILE_A)
        networks.remove_vnic_profile(
            positive=True,
            vnic_profile_name=PROFILE_B,
            network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        )

    request.addfinalizer(finalize)


class TestCaseVnic(TestCase):
    __test__ = False

    CUSTOM_HOOK = "speed"
    HOOK_NAMES = None

    @classmethod
    def _create_python_script_to_verify_custom_hook(cls, name):
        my_hook = "{0}.hook".format(name)
        script_name = "{0}.{1}".format(name, SCRIPT_TYPES["python"])

        hooks.create_python_script_to_verify_custom_hook(
            ip=config.HOSTS_IP[0],
            password=config.HOSTS_PW,
            script_name=script_name,
            custom_hook=cls.CUSTOM_HOOK,
            target=path.join(HOOK_PATH, name),
            output_file=path.join(TMP, my_hook)
        )

    @classmethod
    def _create_one_line_shell_script(cls, name):
        my_hook = "{0}.hook".format(name)
        script_name = "{0}.{1}".format(name, SCRIPT_TYPES["shell"])

        hooks.create_one_line_shell_script(
            ip=config.HOSTS_IP[0],
            password=config.HOSTS_PW,
            script_name=script_name,
            command="touch",
            arguments=path.join(TMP, my_hook),
            target=path.join(HOOK_PATH, name)
        )

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ create python script """

        testflow.setup("Setting up %s class.", cls.__name__)

        testflow.step("Creating scripts for test hooks.")
        for hook_name, hook_type in cls.HOOK_NAMES.iteritems():
            if hook_type == SCRIPT_TYPES["python"]:
                cls._create_python_script_to_verify_custom_hook(hook_name)
            elif hook_type == SCRIPT_TYPES["shell"]:
                cls._create_one_line_shell_script(hook_name)
            else:
                logger.error("Unsupported script type.")

        def finalize():
            """ remove created script """
            testflow.teardown("Tearing down %s class.", cls.__name__)

            testflow.step("Removing all hooks.")
            for hook_name, hook_type in cls.HOOK_NAMES.iteritems():
                hook_name = "{0}/{1}.{2}".format(
                    hook_name,
                    hook_name,
                    hook_type
                )
                test_utils.removeFileOnHost(
                    positive=True,
                    ip=config.HOSTS_IP[0],
                    password=config.HOSTS_PW,
                    filename=path.join(HOOK_PATH, hook_name)
                )

        request.addfinalizer(finalize)

    @classmethod
    def check_for_files(cls):
        """ Check for file created by hook """
        for hook_name, hook_type in cls.HOOK_NAMES.iteritems():
            my_hook = "{0}.hook".format(hook_name)
            logger.info("Checking existence of %s/%s", TMP, my_hook)

            assert hooks.check_for_file_existence_and_content(
                positive=True,
                ip=config.HOSTS_IP[0],
                password=config.HOSTS_PW,
                filename=path.join(TMP, my_hook),
                content=(
                    SPEED if hook_type == SCRIPT_TYPES["python"] else None
                )
            )


@attr(tier=2)
class TestCaseAfterBeforeNicHotplug(TestCaseVnic):
    """ after_before_nic_hotplug hook """
    __test__ = True

    NIC_NAME = "hot_plugged_nic"
    HOOK_NAMES = {
        "after_nic_hotplug": SCRIPT_TYPES["shell"],
        "before_nic_hotplug": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ hot plug nic """
        super(TestCaseAfterBeforeNicHotplug, cls).setup_class(request)

        testflow.step(
            "Adding %s nic with profile %s to %s VM.",
            cls.NIC_NAME,
            PROFILE_A,
            config.HOOKS_VM_NAME
        )
        assert vms.addNic(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            name=cls.NIC_NAME,
            network=config.MGMT_BRIDGE,
            vnic_profile=PROFILE_A
        )

        def finalize():
            """ remove created nic """
            testflow.teardown("Tearing down %s class", cls.__name__)

            testflow.step("Stopping %s VM.", config.HOOKS_VM_NAME)
            assert vms.stopVm(True, config.HOOKS_VM_NAME)

            testflow.step(
                "Removing %s nic from %s VM.",
                cls.NIC_NAME,
                config.HOOKS_VM_NAME
            )
            assert vms.removeNic(True, config.HOOKS_VM_NAME, cls.NIC_NAME)

            testflow.step("Starting %s VM.", config.HOOKS_VM_NAME)
            assert vms.startVm(
                positive=True,
                vm=config.HOOKS_VM_NAME,
                wait_for_status=config.VM_UP,
                wait_for_ip=True
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-12335")
    def test_after_before_nic_hotplug(self):
        """ test_after_before_nic_hotplug """
        testflow.step("Checking for files.")
        self.check_for_files()

        testflow.step(
            "Sleeping for a %s to let nic receive network stats.",
            SLEEP_TIME
        )
        sleep(SLEEP_TIME)


@attr(tier=2)
class TestCaseAfterBeforeNicHotunplug(TestCaseVnic):
    """ before_after_nic_hotunplug hook """
    __test__ = True

    HOOK_NAMES = {
        "before_nic_hotunplug": SCRIPT_TYPES["shell"],
        "after_nic_hotunplug": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ hot unplug nic """
        super(TestCaseAfterBeforeNicHotunplug, cls).setup_class(request)

        testflow.step(
            "Making hot unplug of a %s nic from %s VM.",
            HOTUNPLUG_NIC,
            config.HOOKS_VM_NAME
        )
        assert vms.hotUnplugNic(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            nic=HOTUNPLUG_NIC
        )

        def finalize():
            """ plug nic back """
            testflow.teardown("Tearing down %s class.", cls.__name__)

            testflow.step(
                "Making hot plug of %s nic to %s VM.",
                HOTUNPLUG_NIC,
                config.HOOKS_VM_NAME
            )
            assert vms.hotPlugNic(
                positive=True,
                vm=config.HOOKS_VM_NAME,
                nic=HOTUNPLUG_NIC
            )

        request.addfinalizer(finalize)

    @polarion("RHEVM3-12338")
    def test_after_before_nic_hotunplug(self):
        """ test_after_before_nic_hotunplug """
        testflow.step("Checking for files.")
        self.check_for_files()


@attr(tier=2)
class TestCaseAfterBeforeUpdateDevice(TestCaseVnic):
    """ before_after_update_device hook """
    __test__ = True

    HOOK_NAMES = {
        "before_update_device": SCRIPT_TYPES["python"],
        "after_update_device": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ update nic """
        super(TestCaseAfterBeforeUpdateDevice, cls).setup_class(request)

        testflow.step("Updating %s nic to make it not linked.", UPDATE_NIC)
        assert vms.updateNic(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            nic=UPDATE_NIC,
            linked=False,
            network=config.MGMT_BRIDGE,
            vnic_profile=PROFILE_A
        )

    @polarion("RHEVM3-12345")
    def test_after_before_update_device(self):
        """ test_after_before_update_device """
        testflow.step("Checking for files.")
        self.check_for_files()


@attr(tier=2)
class TestCaseAfterUpdateDeviceFail(TestCaseVnic):
    """ after_update_device_fail hook """
    __test__ = True

    NONEXISTENT = "xxxyxxx"
    UPDATE_FAIL = (
        "vdsClient -s 0 vmUpdateDevice {0} deviceType=interface "
        "alias={1} network={2}"
    )

    HOOK_NAMES = {
        "after_update_device_fail": SCRIPT_TYPES["shell"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ update fail nic """
        super(TestCaseAfterUpdateDeviceFail, cls).setup_class(request)

        testflow.step("Defining a command to determine failed nic.")
        cmd_nic = (
            'virsh -r dumpxml {0} | '
            'awk \"/<interface type=\'bridge\'>/,/<\/interface>/\" | '
            'grep alias | grep -oP "(?<=<alias name=\').*?(?=\'/>)"'
        )

        testflow.step("Running a command on %s host.", config.HOSTS_IP[0])
        fail_nic = runMachineCommand(
            positive=True,
            ip=config.HOSTS_IP[0],
            user=config.HOSTS_USER,
            password=config.HOSTS_PW,
            cmd=cmd_nic.format(config.HOOKS_VM_NAME)
        )[1]["out"][:-2].split()[0]

        testflow.step("Getting ID of the %s VM.", config.HOOKS_VM_NAME)
        vm_id = vms.VM_API.find(config.HOOKS_VM_NAME).get_id()

        testflow.step("Defining a command for updating a nic to fail.")
        cmd = cls.UPDATE_FAIL.format(vm_id, fail_nic, cls.NONEXISTENT)

        testflow.step("Checking if the command above failed.")
        assert runMachineCommand(
            positive=False,
            ip=config.HOSTS_IP[0],
            user=config.HOSTS_USER,
            password=config.HOSTS_PW,
            cmd=cmd
        )[0]

    @polarion("RHEVM3-12346")
    def test_after_update_device_fail(self):
        """ test_after_update_device_fail """
        testflow.step("Checking for files.")
        self.check_for_files()
