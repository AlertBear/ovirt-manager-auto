"""
multiple_queue_nics
"""
import logging

import pytest

import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.config as conf
import rhevmtests.networking.helper as network_helper
from art.test_handler.tools import polarion, bz
from art.unittest_lib import NetworkTest, testflow, attr
from fixtures import update_vnic_profile, run_vm, create_vm

logger = logging.getLogger("Multiple_Queues_Nics_Cases")


@attr(tier=2)
@pytest.mark.usefixtures(update_vnic_profile.__name__, run_vm.__name__)
class TestMultipleQueueNics01(NetworkTest):
    """
    1) Verify that number of queues is not updated on running VM and check
        that number of queues is updated on new VM boot.
    2) Check that queue survive VM hibernate
    3) Check that queues survive VM migration
    """
    __test__ = True
    vm_name = conf.VM_0
    num_queues_0 = conf.NUM_QUEUES[0]
    num_queues_1 = conf.NUM_QUEUES[1]
    prop_queues = conf.PROP_QUEUES[1]

    @polarion("RHEVM3-4310")
    def test_multiple_queue_nics_update(self):
        """
        Update queues while VM is running.
        Make sure that number of queues does not change on running VM.
        stop VM.
        start VM.
        make sure number of queues changed on new boot.
        """
        testflow.step(
            "Update custom properties on %s to %s", conf.MGMT_BRIDGE,
            self.prop_queues
        )

        assert ll_networks.update_vnic_profile(
            name=conf.MGMT_BRIDGE, network=conf.MGMT_BRIDGE,
            data_center=conf.DC_0, custom_properties=self.prop_queues
        )

        testflow.step(
            "Check that qemu still has %s queues after properties update",
            self.num_queues_0
        )

        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, host_obj=conf.VDS_0_HOST,
            num_queues=self.num_queues_0
        )
        testflow.step("Restart VM %s", self.vm_name)
        assert ll_vms.restartVm(
            vm=self.vm_name, placement_host=conf.HOST_0_NAME
        )

        testflow.step("Check that qemu has %s queues", self.num_queues_1)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, host_obj=conf.VDS_0_HOST,
            num_queues=self.num_queues_1
        )

    @polarion("RHEVM3-4312")
    def test_multiple_queue_nics(self):
        """
        hibernate the VM and check the queue still confured on qemu
        """
        testflow.step("Suspend %s", self.vm_name)
        assert ll_vms.suspendVm(positive=True, vm=self.vm_name)

        testflow.step("Start %s", self.vm_name)
        assert ll_vms.startVm(
            positive=True, vm=self.vm_name, placement_host=conf.HOST_0_NAME
        )

        testflow.step("Check that qemu has %s queues", self.num_queues_0)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, host_obj=conf.VDS_0_HOST,
            num_queues=self.num_queues_0
        )

    @bz({"1349461": {}})
    @polarion("RHEVM3-4311")
    def test_multiple_queue_nics_vm_migration(self):
        """
        Check number of queues after VM migration
        """
        testflow.step(
            "Migrate Vm %s from host %s to destination host %s",
            self.vm_name, conf.HOST_0_NAME, conf.HOST_1_NAME
        )
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_name, host=conf.HOST_1_NAME
        )
        testflow.step(
            "Check that qemu has %s queues after VM migration",
            self.num_queues_0
        )
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, host_obj=conf.VDS_1_HOST,
            num_queues=self.num_queues_0
        )


@attr(tier=2)
@pytest.mark.usefixtures(
    update_vnic_profile.__name__, create_vm.__name__, run_vm.__name__
)
class TestMultipleQueueNics02(NetworkTest):
    """
    Check queue exists for VM from template
    """
    __test__ = True
    vm_name = conf.VM_FROM_TEMPLATE
    num_queues_0 = conf.NUM_QUEUES[0]

    @polarion("RHEVM3-4313")
    def test_multiple_queue_nics(self):
        """
        Check that queue exist on VM from template
        """

        testflow.step("Check that qemu has %s queues", self.num_queues_0)
        assert network_helper.check_queues_from_qemu(
            vm=self.vm_name, host_obj=conf.VDS_0_HOST,
            num_queues=self.num_queues_0
        )
