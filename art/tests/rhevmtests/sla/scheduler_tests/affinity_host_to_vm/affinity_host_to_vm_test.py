"""
Host To VM affinity tests
"""
import pytest

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.scheduling_policies as ll_sch_policies
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.unittest_lib as u_libs
import config as conf
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion, bz
from rhevmtests.sla.fixtures import (
    choose_specific_host_as_spm,
    run_once_vms,
    stop_vms
)
from rhevmtests.sla.scheduler_tests.fixtures import create_affinity_groups

host_as_spm = 2


@pytest.fixture(scope="module", autouse=True)
def init_affinity_test(request):
    """
    1) Create 'affinity' scheduling policy
    2) Update cluster scheduling policy to 'affinity' policy
    """
    def fin():
        """
        1) Update cluster scheduling policy to 'none' policy
        2) Remove 'affinity' scheduling policy
        """
        result_list = []
        u_libs.testflow.teardown(
            "Update cluster %s scheduling policy", conf.CLUSTER_NAME[0]
        )
        result_list.append(
            ll_clusters.updateCluster(
                positive=True,
                cluster=conf.CLUSTER_NAME[0],
                scheduling_policy=conf.POLICY_NONE
            )
        )
        u_libs.testflow.teardown(
            "Remove %s scheduling policy", conf.AFFINITY_POLICY_NAME
        )
        result_list.append(
            ll_sch_policies.remove_scheduling_policy(
                policy_name=conf.AFFINITY_POLICY_NAME
            )
        )
        assert all(result_list)
    request.addfinalizer(fin)

    u_libs.testflow.setup(
        "Add %s scheduling policy", conf.AFFINITY_POLICY_NAME
    )
    sch_helpers.add_affinity_scheduler_policy()

    u_libs.testflow.setup(
        "Update cluster %s scheduling policy", conf.CLUSTER_NAME[0]
    )
    assert ll_clusters.updateCluster(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        scheduling_policy=conf.AFFINITY_POLICY_NAME
    )


@u_libs.attr(tier=2)
@pytest.mark.usefixtures(choose_specific_host_as_spm.__name__)
class BaseHostAffinity(u_libs.SlaTest):
    """
    Base class for all affinity tests
    """

    @staticmethod
    def check_vm_host(vm_name, host_name):
        """
        Check if the VM started on the correct host

        Args:
            vm_name (str): VM name
            host_name (str): Host name

        Returns:
            bool: True, if the VM started on correct host, otherwise False
        """
        u_libs.testflow.step(
            "Check if the VM %s started on the host %s", vm_name, host_name
        )
        return ll_vms.get_vm_host(vm_name=vm_name) == host_name

    @staticmethod
    def start_vm(vm_name):
        """
        Start the VM

        Args:
            vm_name (str): VM name

        Returns:
            bool: True, if the VM started, otherwise False
        """
        u_libs.testflow.step("Start the VM %s", vm_name)
        return ll_vms.startVm(positive=True, vm=vm_name)


@pytest.mark.usefixtures(create_affinity_groups.__name__)
class BaseHostAffinityStartVm(BaseHostAffinity):
    """
    Base class for all tests that start VM
    """
    affinity_groups = None


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity01(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard positive affinity group with the host
    """
    affinity_groups = {
        "{0}_01".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-17586")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity02(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    """
    affinity_groups = {
        "{0}_02".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-17587")
    def test_vm_start(self):
        """
        Check that the engine does not start VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(run_once_vms.__name__)
class TestStartVmUnderHostAffinity03(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard positive affinity group with the host
    and to another hard positive affinity group with a VM
    """
    affinity_groups = {
        "{0}_03_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_1,
        "{0}_03_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_run = {conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}}

    @polarion("RHEVM-17588")
    def test_vm_start(self):
        """
        Check that the VM fails to start
        """
        assert not self.start_vm(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(run_once_vms.__name__)
class TestStartVmUnderHostAffinity04(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    and to another hard negative affinity group with VM's
    """
    affinity_groups = {
        "{0}_04_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_2,
        "{0}_04_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_run = conf.VMS_TO_RUN_0

    @polarion("RHEVM-17589")
    def test_vm_start(self):
        """
        Check that the VM fails to start
        """
        assert not self.start_vm(vm_name=conf.VM_NAME[0])


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity05(BaseHostAffinityStartVm):
    """
    Start the VM that placed into soft positive affinity group with the host
    and to another hard positive affinity group with a VM
    """
    affinity_groups = {
        "{0}_05_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_3,
        "{0}_05_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_1
    }
    vms_to_run = {conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1}}
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-17590")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-1
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[1]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity06(BaseHostAffinityStartVm):
    """
    Start the VM that placed into soft negative affinity group with the host
    and to another hard negative affinity group with VM's
    """
    affinity_groups = {
        "{0}_06_1".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.HOST_TO_VM_AFFINITY_GROUP_4,
        "{0}_06_2".format(
            conf.AFFINITY_START_VM_TEST
        ): conf.VM_TO_VM_AFFINITY_GROUP_2
    }
    vms_to_run = conf.VMS_TO_RUN_0
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-17591")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@pytest.mark.usefixtures(
    run_once_vms.__name__,
    stop_vms.__name__
)
class TestStartVmUnderHostAffinity07(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group with the host
    and other VM's, when VM to VM affinity disabled
    """
    affinity_groups = {
        "{0}_07".format(conf.AFFINITY_START_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_VMS_RULES: {
                conf.AFFINITY_GROUP_ENFORCING: True,
                conf.AFFINITY_GROUPS_ENABLED: False
            },
            conf.AFFINITY_GROUP_HOSTS: [0],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:3]
        }
    }
    vms_to_run = conf.VMS_TO_RUN_0
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-18192")
    def test_vm_start(self):
        """
        Check that the engine does not start VM-0 on the host-0
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert not self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[0]
        )


@u_libs.attr(tier=1)
@bz({"1304300": {"ppc": conf.PPC_ARCH}})
@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmUnderHostAffinity08(BaseHostAffinityStartVm):
    """
    Start the VM that placed into hard negative affinity group
    with the multiple hosts
    """
    affinity_groups = {
        "{0}_08".format(conf.AFFINITY_START_VM_TEST): {
            conf.AFFINITY_GROUP_HOSTS_RULES: {
                conf.AFFINITY_GROUP_POSITIVE: False,
                conf.AFFINITY_GROUP_ENFORCING: True
            },
            conf.AFFINITY_GROUP_HOSTS: [0, 1],
            conf.AFFINITY_GROUP_VMS: conf.VM_NAME[:1]
        }
    }
    vms_to_stop = conf.VM_NAME[:1]

    @polarion("RHEVM-19279")
    def test_vm_start(self):
        """
        Check that the engine starts VM-0 on the host-2
        """
        assert self.start_vm(vm_name=conf.VM_NAME[0])
        assert self.check_vm_host(
            vm_name=conf.VM_NAME[0], host_name=conf.HOSTS[2]
        )
