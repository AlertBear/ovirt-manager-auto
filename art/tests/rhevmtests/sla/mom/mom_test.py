"""
Testing memory overcomitment manager consisting of KSM and ballooning
Prerequisites: 1 DC, 1 hosts, 1 SD
Tests covers:
    KSM
        progressive startup of VMs
        1 moment startup of multiple VMs
        KSM with migration of VMs
        and stopping KSM by migrating VM
    Balloon
        testing inflation and deflation of ballooning on
        1 VM, 2 VMs with different memories options, different OS,
        VM with memory set to max guaranteed memory, VM without guest
        agent, multiple VMs on one host with ballooning enabled
"""
import pytest

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config as conf
import helpers
from art.test_handler import find_test_file
from art.test_handler.tools import polarion, bz
from art.unittest_lib import testflow, tier2, SlaTest
from fixtures import (
    prepare_env_for_ballooning_test,
    stop_memory_allocation,
    update_vms_for_ksm_test
)
from rhevmtests.sla.fixtures import (  # noqa: F401
    migrate_he_vm,
    start_vms,
    stop_guest_agent_service,
    stop_vms,
    update_cluster,
    update_cluster_to_default_parameters,
    update_vms,
    update_vms_to_default_parameters
)

find_test_file.__test__ = False
he_src_host = 0


@pytest.fixture(scope="module", autouse=True)
def prepare_env_for_mom_test(request):
    """
    1) Create VM's for MOM test
    2) Disable swap on the host
    """
    def fin():
        """
        1) Remove MOM test VM's
        2) Enable swap on the host
        """
        ll_vms.safely_remove_vms(vms=conf.MOM_VMS)
        helpers.change_swapping(
            resource=conf.VDS_HOSTS[0], enable=True
        )
    request.addfinalizer(fin)

    vms_params = dict(
        (
            vm_name, {
                conf.VM_CLUSTER: conf.CLUSTER_NAME[0],
                conf.VM_TEMPLATE: conf.TEMPLATE_NAME[0]
            }
        ) for vm_name in conf.MOM_VMS
    )
    assert ll_vms.create_vms(
        vms_params=vms_params, max_workers=len(vms_params)
    )
    assert helpers.change_swapping(
        resource=conf.VDS_HOSTS[0], enable=False
    )


@pytest.mark.incremental
@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    update_vms_for_ksm_test.__name__,
    update_vms_to_default_parameters.__name__,
    update_cluster.__name__,
    stop_vms.__name__
)
class TestKSM(SlaTest):
    """
    KSM tests
    """
    update_to_default_params = conf.MOM_VMS
    threshold_list = []
    vms_to_stop = conf.MOM_VMS
    cluster_to_update_params = {
        conf.CLUSTER_KSM: True,
        conf.CLUSTER_BALLOONING: False,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_DESKTOP
    }

    @tier2
    @polarion("RHEVM3-4969")
    def test_a_ksm_progressive(self):
        """
        Finds the threshold where KSM starts

        1) Start VM's one by one
        2) Check when KSM starts working - this is the threshold
        3) Stop VM's safely
        """
        ksm_running = False
        for vm_name in conf.MOM_VMS:
            testflow.step("Start VM %s", vm_name)
            assert ll_vms.startVm(
                positive=True,
                vm=vm_name,
                wait_for_status=conf.VM_UP,
                wait_for_ip=True
            )
            self.threshold_list.append(vm_name)
            testflow.step(
                "Check if KSM triggered after VM %s start",
                vm_name
            )
            ksm_running = helpers.is_ksm_running(resource=conf.VDS_HOSTS[0])
            if ksm_running:
                # Add additional VM to the threshold list to be sure that KSM
                # will be triggered in next test cases
                if vm_name != conf.MOM_VMS[-1]:
                    self.threshold_list.append(conf.MOM_VMS[-1])
                break
        assert ll_vms.stop_vms_safely(vms_list=self.threshold_list)
        assert ksm_running

    @tier2
    @polarion("RHEVM3-4977")
    def test_b_ksm_kicking(self):
        """
        Run VM's in one moment to trigger KSM

        1) Start simultaneously VM's in threshold_list to trigger KSM
        2) Check if KSM is running
        """
        testflow.step(
            "Running VM's %s that should trigger KSM",
            self.threshold_list
        )
        ll_vms.start_vms(
            vm_list=self.threshold_list, max_workers=len(self.threshold_list)
        )
        testflow.step(
            "Check if KSM triggered on host %s", conf.HOSTS[0]
        )
        assert helpers.wait_for_ksm_state(resource=conf.VDS_HOSTS[0])

    @tier2
    @polarion("RHEVM3-4976")
    def test_c_ksm_migration(self):
        """
        Migrate VMs with KSM enabled

        1) Migrate VM with KSM enabled
        2) Check if KSM is running on source host
        """
        for vm_name in self.threshold_list:
            testflow.step("Migrate VM %s", vm_name)
            assert ll_vms.migrateVm(positive=True, vm=vm_name, force=True)
        testflow.step(
            "Check that KSM disabled on the host %s after VM's migration",
            conf.HOSTS[0]
        )
        assert not helpers.is_ksm_running(resource=conf.VDS_HOSTS[0])

    @tier2
    @polarion("RHEVM3-4975")
    def test_d_ksm_stop(self):
        """
        1) Check that KSM does not triggered,
        when half om VM's from threshold_list migrated on the host
        """
        for vm_name in self.threshold_list[:len(self.threshold_list) / 2]:
            testflow.step("Migrate VM %s", vm_name)
            assert ll_vms.migrateVm(positive=True, vm=vm_name, force=True)

        testflow.step(
            "Check that KSM disabled on the host %s after VM's migration",
            conf.HOSTS[0]
        )
        assert not helpers.is_ksm_running(resource=conf.VDS_HOSTS[0])


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    update_vms.__name__,
    prepare_env_for_ballooning_test.__name__,
    start_vms.__name__,
    stop_memory_allocation.__name__
)
class Balloon(SlaTest):
    """
    Balloon tests
    """

    @staticmethod
    def check_balloon_deflation(
        vm_list, negative=False, timeout=conf.BALLOON_TIMEOUT
    ):
        """
        Check VM's balloon deflation

        Args:
            vm_list (list): VM's names
            negative (bool): Negative or positive behaviour
            timeout (int): Sampler timeout
        """
        testflow.step("Allocate host %s memory", conf.HOSTS[0])
        pid = helpers.allocate_host_memory()
        assert pid

        testflow.step("Testing deflation of balloon")
        balloon_deflates = helpers.wait_for_vms_balloon_state(
            vm_list=vm_list, timeout=timeout
        )
        if negative:
            balloon_deflates = not balloon_deflates
        assert balloon_deflates

        testflow.step(
            "Cancel memory allocation on host %s", conf.HOSTS[0]
        )
        helpers.cancel_host_allocation(pid=pid)

    def check_balloon_usage(self, vm_list, timeout=conf.SAMPLER_TIMEOUT):
        """
        Check VM's balloon inflation and deflation

        Args:
            vm_list (list): VM's names
            timeout (int): Sampler timeout
        """
        self.check_balloon_deflation(vm_list=vm_list, timeout=timeout)

        testflow.step("Testing inflation of balloon")
        assert helpers.wait_for_vms_balloon_state(
            vm_list=vm_list, deflation=False, timeout=timeout
        )


class TestBalloonUsage(Balloon):
    """
    Test Balloon usage on one VM
    """
    vms_to_params = {
        conf.MOM_VMS[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_MEMORY: 2 * conf.GB,
            conf.VM_MEMORY_GUARANTEED: conf.GB,
            conf.VM_BALLOONING: True
        }
    }
    vms_to_start = conf.MOM_VMS[:1]

    @tier2
    @bz({"1497517": {}})
    @polarion("RHEVM3-4974")
    def test_balloon_usage(self):
        """
        1) Tests inflation and deflation of the balloon
        """
        self.check_balloon_usage(vm_list=self.vms_to_start)


class TestBalloonUsageDifferentMemory(Balloon):
    """
    Test balloon inflation and deflation on 2 VM's with different memories
    """
    vms_to_params = dict(
        (
            vm_name, {
                conf.VM_PLACEMENT_HOSTS: [0],
                conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
                conf.VM_MEMORY: conf.DIFFERENT_MEMORY,
                conf.VM_MEMORY_GUARANTEED: (
                    conf.DIFFERENT_MEMORY - 128 * conf.MB * i
                ),
                conf.VM_MAX_MEMORY: conf.DIFFERENT_MEMORY + conf.GB,
                conf.VM_BALLOONING: True
            }
        ) for i, vm_name in enumerate(conf.MOM_VMS[:2])
    )
    vms_to_start = conf.MOM_VMS[:2]

    @tier2
    @bz({"1497517": {}})
    @polarion("RHEVM3-4973")
    def test_balloon_multi_memory(self):
        """
        1) Tests inflation and deflation of the balloon
        """
        self.check_balloon_usage(vm_list=self.vms_to_start)


@pytest.mark.usefixtures(stop_guest_agent_service.__name__)
class TestBalloonWithoutAgent(Balloon):
    """
    Negative: Test ballooning of the VM without guest agent
    """
    vms_to_params = {
        conf.MOM_VMS[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_MEMORY: 2 * conf.GB,
            conf.VM_MEMORY_GUARANTEED: conf.GB,
            conf.VM_BALLOONING: True
        }
    }
    vms_to_start = conf.MOM_VMS[:1]
    stop_guest_agent_vm = conf.MOM_VMS[0]

    @tier2
    @bz({"1497517": {}})
    @polarion("RHEVM3-4971")
    def test_negative_balloon_no_agent(self):
        """
        1) Tests deflation of the balloon
        """
        self.check_balloon_deflation(vm_list=self.vms_to_start, negative=True)


class TestBalloonMax(Balloon):
    """
    Negative: Test ballooning on the VM
    which has memory equal to guaranteed memory
    """
    vms_to_params = {
        conf.MOM_VMS[0]: {
            conf.VM_PLACEMENT_HOSTS: [0],
            conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
            conf.VM_MEMORY: 2 * conf.GB,
            conf.VM_MEMORY_GUARANTEED: 2 * conf.GB,
            conf.VM_BALLOONING: True
        }
    }
    vms_to_start = conf.MOM_VMS[:1]

    @tier2
    @bz({"1497517": {}})
    @polarion("RHEVM3-4978")
    def test_negative_balloon_max(self):
        """
        1) Tests deflation of the balloon
        """
        self.check_balloon_deflation(vm_list=self.vms_to_start, negative=True)


class TestBalloonMultipleVms(Balloon):
    """
    Test ballooning with multiple VM's
    """
    vms_to_params = dict(
        (
            vm_name, {
                conf.VM_PLACEMENT_HOSTS: [0],
                conf.VM_PLACEMENT_AFFINITY: conf.VM_PINNED,
                conf.VM_MEMORY: conf.MULTIPLY_VMS_MEMORY,
                conf.VM_MEMORY_GUARANTEED: conf.MULTIPLY_VMS_MEMORY_GUARANTEED,
                conf.VM_BALLOONING: True
            }
        ) for vm_name in conf.MOM_VMS
    )
    vms_to_start = conf.MOM_VMS

    @tier2
    @bz({"1497517": {}})
    @polarion("RHEVM3-4970")
    def test_f_balloon_multiple_vms(self):
        """
        1) Tests inflation and deflation of the balloon
        """
        self.check_balloon_usage(
            vm_list=self.vms_to_start, timeout=conf.BALLOON_TIMEOUT
        )
