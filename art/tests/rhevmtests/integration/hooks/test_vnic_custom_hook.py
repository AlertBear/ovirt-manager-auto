"""
Testing vnic profile hooks: after_update_device_fail,  after_update_device
before_update_device, after_nic_hotunplug, before_nic_hotunplug,
after_nic_hotplug, before_nic_hotplug
"""

import logging
import pytest
from shlex import split
from os import path
from time import sleep

from art.rhevm_api.resources import VDS
from art.rhevm_api.tests_lib.low_level import hooks, vms, networks, hosts
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier3,
    CoreSystemTest as TestCase,
    testflow,
)

from . import config, get_property_value, set_property_value

SPEED = "1000"
CUSTOM_PROPERTIES_A = "speed={0};port_mirroring=True;bandwidth=10000".format(
    SPEED
)
CUSTOM_PROPERTIES_B = "port_mirroring=True;bandwidth=10000"
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

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True, scope="module")
def setup_module(request):
    def finalize():
        testflow.teardown("Removing all hooks from %s.", config.HOSTS_IP[0])
        assert config.VDS_HOSTS[0].run_command(split(REMOVE_HOOKS))[0] == 0

        testflow.teardown("Removing VM %s.", config.HOOKS_VM_NAME)
        assert vms.stopVm(positive=True, vm=config.HOOKS_VM_NAME)
        assert vms.removeVm(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            wait=True
        )

        testflow.teardown("Removing VNIC profile %s.", PROFILE_A)
        assert networks.remove_vnic_profile(
            positive=True,
            vnic_profile_name=PROFILE_A,
            network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.teardown("Removing VNIC profile %s.", PROFILE_A)
        assert networks.remove_vnic_profile(
            positive=True,
            vnic_profile_name=PROFILE_B,
            network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        )

        testflow.teardown("Drop custom property to default value")
        assert set_property_value(
            config.VNIC_PROPERTY_KEY,
            config.custom_property_vnic_default
        )

    request.addfinalizer(finalize)

    testflow.setup("Configuring custom properties for this module needs.")
    config.custom_property_vnic_default = "\"{}\"".format(
        get_property_value(
            config.VNIC_PROPERTY_KEY
        )
    )
    assert set_property_value(
        config.VNIC_PROPERTY_KEY,
        config.CUSTOM_PROPERTY_VNIC_HOOKS
    )

    testflow.setup("Creating a %s VM.", config.HOOKS_VM_NAME)
    assert vms.createVm(
        positive=True,
        vmName=config.HOOKS_VM_NAME,
        cluster=config.CLUSTER_NAME[0],
        display_type=config.display_type_vnc,
        template=config.TEMPLATE_NAME[0]
    )

    testflow.setup("Starting %s VM.", config.HOOKS_VM_NAME)
    assert vms.startVm(
        positive=True,
        vm=config.HOOKS_VM_NAME,
        wait_for_status=config.VM_UP,
        wait_for_ip=True,
        placement_host=config.HOSTS[0]
    )

    testflow.setup(
        "Adding a %s VNIC profile to %s network in %s cluster with custom "
        "properties %s.",
        PROFILE_A,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        CUSTOM_PROPERTIES_A
    )
    assert networks.add_vnic_profile(
        positive=True,
        name=PROFILE_A,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties=CUSTOM_PROPERTIES_A
    )

    testflow.setup(
        "Adding a %s VNIC profile to %s network in %s cluster with custom "
        "properties %s.",
        PROFILE_B,
        config.MGMT_BRIDGE,
        config.CLUSTER_NAME[0],
        CUSTOM_PROPERTIES_B
    )
    assert networks.add_vnic_profile(
        positive=True,
        name=PROFILE_B,
        cluster=config.CLUSTER_NAME[0],
        network=config.MGMT_BRIDGE,
        custom_properties=CUSTOM_PROPERTIES_B
    )

    testflow.setup(
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

    testflow.setup(
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

    testflow.setup(
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

    testflow.setup(
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


@tier3
class CaseVnic(TestCase):
    CUSTOM_HOOK = "speed"
    hooks_names = None

    @classmethod
    def _create_python_script_to_verify_custom_hook(cls, name):
        my_hook = "{0}.hook".format(name)
        script_name = "{0}.{1}".format(name, SCRIPT_TYPES["python"])

        hooks.create_python_script_to_verify_custom_hook(
            host=config.VDS_HOSTS[0],
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
            host=config.VDS_HOSTS[0],
            script_name=script_name,
            command="touch",
            arguments=path.join(TMP, my_hook),
            target=path.join(HOOK_PATH, name)
        )

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """ remove created script """
            testflow.teardown("Removing all hooks.")
            for _hook_name, _hook_type in cls.hooks_names.iteritems():
                _hook_name = "{0}/{1}.{2}".format(
                    _hook_name,
                    _hook_name,
                    _hook_type
                )
                assert config.VDS_HOSTS[0].fs.remove(
                    path.join(HOOK_PATH, _hook_name)
                )

        request.addfinalizer(finalize)

        """ create python script """

        testflow.setup("Creating scripts for test hooks.")
        for hook_name, hook_type in cls.hooks_names.iteritems():
            if hook_type == SCRIPT_TYPES["python"]:
                cls._create_python_script_to_verify_custom_hook(hook_name)
            elif hook_type == SCRIPT_TYPES["shell"]:
                cls._create_one_line_shell_script(hook_name)
            else:
                logger.error("Unsupported script type.")

    @classmethod
    def check_for_files(cls):
        """ Check for file created by hook """
        for hook_name, hook_type in cls.hooks_names.iteritems():
            my_hook = "{0}.hook".format(hook_name)
            logger.info("Checking existence of %s/%s", TMP, my_hook)

            assert hooks.check_for_file_existence_and_content(
                positive=True,
                host=config.VDS_HOSTS[0],
                filename=path.join(TMP, my_hook),
                content=(
                    SPEED if hook_type == SCRIPT_TYPES["python"] else None
                )
            )


class TestCaseAfterBeforeNicHotplug(CaseVnic):
    """ after_before_nic_hotplug hook """
    NIC_NAME = "hot_plugged_nic"
    hooks_names = {
        "after_nic_hotplug": SCRIPT_TYPES["shell"],
        "before_nic_hotplug": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """ remove created nic """
            testflow.teardown("Stopping %s VM.", config.HOOKS_VM_NAME)
            assert vms.stopVm(True, config.HOOKS_VM_NAME)

            testflow.teardown(
                "Removing %s nic from %s VM.",
                cls.NIC_NAME,
                config.HOOKS_VM_NAME
            )
            assert vms.removeNic(True, config.HOOKS_VM_NAME, cls.NIC_NAME)

            testflow.teardown("Starting %s VM.", config.HOOKS_VM_NAME)
            assert vms.startVm(
                positive=True,
                vm=config.HOOKS_VM_NAME,
                wait_for_status=config.VM_UP,
                wait_for_ip=True,
                placement_host=config.HOSTS[0]
            )

        request.addfinalizer(finalize)

        """ hot plug nic """
        super(TestCaseAfterBeforeNicHotplug, cls).setup_class(request)

        testflow.setup(
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


class TestCaseAfterBeforeNicHotunplug(CaseVnic):
    """ before_after_nic_hotunplug hook """
    hooks_names = {
        "before_nic_hotunplug": SCRIPT_TYPES["shell"],
        "after_nic_hotunplug": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        def finalize():
            """ plug nic back """
            testflow.teardown(
                "Making hot plug of %s nic to %s VM.",
                HOTUNPLUG_NIC,
                config.HOOKS_VM_NAME
            )
            assert vms.updateNic(
                positive=True,
                vm=config.HOOKS_VM_NAME,
                nic=HOTUNPLUG_NIC,
                plugged=True
            )

        request.addfinalizer(finalize)

        """ hot unplug nic """
        super(TestCaseAfterBeforeNicHotunplug, cls).setup_class(request)

        testflow.setup(
            "Making hot unplug of a %s nic from %s VM.",
            HOTUNPLUG_NIC,
            config.HOOKS_VM_NAME
        )
        assert vms.updateNic(
            positive=True,
            vm=config.HOOKS_VM_NAME,
            nic=HOTUNPLUG_NIC,
            plugged=False
        )

    @polarion("RHEVM3-12338")
    def test_after_before_nic_hotunplug(self):
        """ test_after_before_nic_hotunplug """
        testflow.step("Checking for files.")
        self.check_for_files()


class TestCaseAfterBeforeUpdateDevice(CaseVnic):
    """ before_after_update_device hook """
    hooks_names = {
        "before_update_device": SCRIPT_TYPES["python"],
        "after_update_device": SCRIPT_TYPES["python"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ update nic """
        super(TestCaseAfterBeforeUpdateDevice, cls).setup_class(request)

        testflow.setup("Updating %s nic to make it not linked.", UPDATE_NIC)
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


class TestCaseAfterUpdateDeviceFail(CaseVnic):
    """ after_update_device_fail hook """
    NONEXISTENT = "xxxyxxx"

    hooks_names = {
        "after_update_device_fail": SCRIPT_TYPES["shell"]
    }

    @classmethod
    @pytest.fixture(autouse=True, scope="class")
    def setup_class(cls, request):
        """ update fail nic """
        super(TestCaseAfterUpdateDeviceFail, cls).setup_class(request)

        testflow.setup("Defining a command to determine failed nic.")
        cmd_nic = (
            'virsh -r dumpxml {0} | '
            'awk \"/<interface type=\'bridge\'>/,/<\/interface>/\" | '
            'grep alias | grep -oP "(?<=<alias name=\').*?(?=\'/>)"'
        )

        testflow.setup("Running a command on %s host.", config.HOSTS_IP[0])
        fail_nic = config.VDS_HOSTS[0].run_command(
            split(cmd_nic.format(config.HOOKS_VM_NAME))
        )[1][:-2].split()[0]

        testflow.setup("Getting ID of the %s VM.", config.HOOKS_VM_NAME)
        vm_id = vms.VM_API.find(config.HOOKS_VM_NAME).get_id()

        testflow.setup("Defining a command for updating a nic to fail.")
        cmd = {
            "vmID": vm_id,
            "params":
                {
                    "alias": fail_nic,
                    "network": cls.NONEXISTENT,
                    "deviceType": "interface"
                }
        }

        testflow.setup("Get host VM is running on.")
        host = VDS(
            hosts.get_host_vm_run_on(config.HOOKS_VM_NAME),
            config.VDC_ROOT_PASSWORD
        )

        testflow.setup("Checking if the command above failed.")
        rc = host.vds_client("VM.updateDevice", cmd)
        assert not rc or rc[0] != 0

    @polarion("RHEVM3-12346")
    def test_after_update_device_fail(self):
        """ test_afpter_update_device_fail """
        testflow.step("Checking for files.")
        self.check_for_files()
