"""
Virt test - run once
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helper
from _pytest_art.testlogger import TestFlowInterface
from art.test_handler.tools import polarion
from art.unittest_lib import (
    tier1,
    tier2,
    common,
)
from fixtures import (
    base_setup_fixture, image_provider_fixture, remove_vm_disk_fixture,
    remove_vm_nic_fixture
)
from rhevmtests.compute.virt import config

testflow = TestFlowInterface


########################################################################
#                            classes                                   #
########################################################################


class TestRunVmOnce(common.VirtTest):
    """
    Run once
    """
    __test__ = True

    @tier2
    @polarion("RHEVM3-9809")
    @pytest.mark.usefixtures(
        base_setup_fixture.__name__, image_provider_fixture.__name__
    )
    @pytest.mark.images_marker(config.CDROM_IMAGE_1)
    def test_boot_from_cd(self):
        """
        Run once VM boot from CD
        """
        testflow.step("Run once vm - boot from cdrom")
        assert helper.run_once_with_boot_dev(
            config.ENUMS['boot_sequence_cdrom'], config.CDROM_IMAGE_1
        )

    @tier1
    @polarion("RHEVM3-9808")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_boot_from_network(self):
        """
        Run once VM boot from Network
        """
        testflow.step("Run once vm - boot from network")
        assert helper.run_once_with_boot_dev(
            config.ENUMS['boot_sequence_network']
        )

    @tier2
    @polarion("RHEVM3-9803")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_start_in_pause_mode(self):
        """
        Run once VM in paused mode
        """
        testflow.step("Run once vm %s in pause mode", config.VM_RUN_ONCE)
        assert ll_vms.runVmOnce(True, config.VM_RUN_ONCE, pause=True)
        testflow.step("Check that vm started in pause mode")
        assert ll_vms.get_vm_state(config.VM_RUN_ONCE) == config.VM_PAUSED

    @tier2
    @polarion("RHEVM3-12353")
    @pytest.mark.usefixtures(
        base_setup_fixture.__name__, image_provider_fixture.__name__
    )
    @pytest.mark.images_marker(config.CDROM_IMAGE_1, config.CDROM_IMAGE_2)
    def test_run_once_vm_with_pause_and_change_cd(self):
        """
        Run once VM with "Start in paused" enables, and when VM in pause mode,
        change VM cd
        """
        testflow.step(
            "Run once vm %s in pause mode with attached cd", config.VM_RUN_ONCE
        )
        assert ll_vms.runVmOnce(
            True, config.VM_RUN_ONCE,
            cdrom_image=config.CDROM_IMAGE_1,
            pause=True
        )
        testflow.step("Check if vm state is paused")
        assert ll_vms.waitForVMState(
            config.VM_RUN_ONCE,
            state=config.ENUMS['vm_state_paused']
        )
        testflow.step("Change vm %s cd", config.VM_RUN_ONCE)
        assert ll_vms.changeCDWhileRunning(
            config.VM_RUN_ONCE,
            config.CDROM_IMAGE_2
        )

    @tier2
    @pytest.mark.skipif(config.PPC_ARCH, reason=config.PPC_SKIP_MESSAGE)
    @polarion("RHEVM3-9794")
    @pytest.mark.usefixtures(
        base_setup_fixture.__name__, image_provider_fixture.__name__
    )
    @pytest.mark.images_marker(config.FLOPPY_IMAGE)
    def test_run_once_vm_with_attached_floppy(self):  # add validation
        """
        Run once VM with attached floppy
        """
        testflow.step(
            "Run once vm %s with attached floppy %s",
            config.VM_RUN_ONCE, config.FLOPPY_IMAGE
        )
        assert ll_vms.runVmOnce(
            True, config.VM_RUN_ONCE,
            floppy_image=config.FLOPPY_IMAGE,
            pause=True
        )

    @tier1
    @polarion("RHEVM3-9800")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    def test_run_once_with_specific_host(self):  # add validation
        """
        Run once VM on specific host
        """
        testflow.step(
            "Run once vm %s on specific host %s",
            config.VM_RUN_ONCE, config.HOSTS[0]
        )
        assert ll_vms.runVmOnce(True, config.VM_RUN_ONCE, host=config.HOSTS[0])

    @tier1
    @polarion("RHEVM3-9781")
    @pytest.mark.usefixtures(
        image_provider_fixture.__name__, remove_vm_disk_fixture.__name__,
        base_setup_fixture.__name__
    )
    @pytest.mark.images_marker(config.CDROM_IMAGE_1)
    def test_run_once_stateless_no_disk(self):
        """
        Negative - run once VM without disk in stateless mode
        """
        testflow.step("run once VM %s without disk", config.VM_RUN_ONCE)
        assert not ll_vms.runVmOnce(True, config.VM_RUN_ONCE, stateless=True)

    @tier1
    @polarion("RHEVM3-9805")
    @pytest.mark.usefixtures(
        remove_vm_nic_fixture.__name__, base_setup_fixture.__name__
    )
    def test_negative_boot_from_network(self):
        """
        negative test - run once VM without nic to boot from network
        """
        testflow.step(
            "run once VM %s without nic, boot from network", config.VM_RUN_ONCE
        )
        assert not helper.run_once_with_boot_dev(
            config.ENUMS['boot_sequence_network']
        )

    @tier2
    @polarion("RHEVM3-9783")
    @pytest.mark.usefixtures(base_setup_fixture.__name__)
    @pytest.mark.args_marker(highly_available=True)
    def test_negative_HA_and_stateless(self):
        """
        Nagtive test - run once HA VM in stateless mode
        """
        testflow.step("run once HA VM %s as stateless vm", config.VM_RUN_ONCE)
        assert not ll_vms.runVmOnce(True, config.VM_RUN_ONCE, stateless=True)

    @tier2
    @polarion("RHEVM3-9796")
    @pytest.mark.usefixtures(
        base_setup_fixture.__name__, image_provider_fixture.__name__
    )
    @pytest.mark.images_marker(config.CDROM_IMAGE_1, config.CDROM_IMAGE_2)
    def test_run_once_vm_with_cd_and_change_cd(self):
        """
        Run once VM with a certain cd and when VM is up change VM cd
        """
        testflow.step(
            "Run once vm %s with attached cd", config.VM_RUN_ONCE
        )
        assert ll_vms.runVmOnce(
            True, config.VM_RUN_ONCE,
            cdrom_image=config.CDROM_IMAGE_1,
        )
        testflow.step("Change vm %s cd", config.VM_RUN_ONCE)
        assert ll_vms.changeCDWhileRunning(
            config.VM_RUN_ONCE,
            config.CDROM_IMAGE_2
        )
