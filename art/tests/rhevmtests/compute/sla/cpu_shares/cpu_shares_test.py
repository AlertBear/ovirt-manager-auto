"""
CPU Share Test
Test CPU share low, medium, high and custom and their combinations
"""

import pytest
import rhevmtests.compute.sla.config as conf

import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import helpers
from art.test_handler.tools import polarion, bz
from art.unittest_lib import tier1, tier2, SlaTest
from fixtures import update_vms_cpu_share
from rhevmtests.compute.sla.fixtures import (
    migrate_he_vm,
    start_vms
)

he_src_host = 0


@pytest.fixture(scope="module", autouse=True)
def pin_vms_cpu(request):
    """
    1) Pin VM CPU to specific host CPU for four VM's
    """
    def fin():
        """
        1) Update VM's to default parameters
        """
        for vm_name in conf.VM_NAME[:4]:
            ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                **conf.DEFAULT_VM_PARAMETERS
            )
    request.addfinalizer(fin)

    host_online_cpu = str(
        ll_sla.get_list_of_online_cpus_on_resource(
            resource=conf.VDS_HOSTS[0]
        )[0]
    )
    for vm_name in conf.VM_NAME[:4]:
        assert ll_vms.updateVm(
            positive=True,
            vm=vm_name,
            placement_affinity=conf.VM_PINNED,
            placement_host=conf.HOSTS[0],
            vcpu_pinning=([{"0": host_online_cpu}])
        )


@pytest.mark.usefixtures(
    migrate_he_vm.__name__,
    update_vms_cpu_share.__name__,
    start_vms.__name__
)
class BaseCpuShare(SlaTest):
    """
    Base CPU share class
    """
    vms_to_start = conf.VM_NAME[:2]
    expected_dict = dict((vm, 50) for vm in vms_to_start)


class TestLowShare(BaseCpuShare):
    """
    Check that two VM's that have the same low CPU share
    are competing evenly on the same core
    """
    vms_cpu_shares = dict(
        (vm_name, conf.CPU_SHARE_LOW) for vm_name in BaseCpuShare.vms_to_start
    )

    @tier2
    @polarion("RHEVM3-4980")
    def test_low_share(self):
        """
        1) Load VM's CPU
        2) Test low share CPU
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )


class TestMediumShare(BaseCpuShare):
    """
    Check that two vms that have the same medium CPU share
    are competing evenly on the same core
    """
    vms_cpu_shares = dict(
        (
            vm_name, conf.CPU_SHARE_MEDIUM
        ) for vm_name in BaseCpuShare.vms_to_start
    )

    @tier2
    @polarion("RHEVM3-4981")
    def test_medium_share(self):
        """
        1) Load VM's CPU
        2) Test medium share CPU
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )


class TestHighShare(BaseCpuShare):
    """
    Check that two vms that have the same high CPU share
    are competing evenly on the same core
    """
    vms_cpu_shares = dict(
        (
            vm_name, conf.CPU_SHARE_HIGH
        ) for vm_name in BaseCpuShare.vms_to_start
    )

    @tier2
    @polarion("RHEVM3-4982")
    def test_high_share(self):
        """
        1) Load VM's CPU
        2) Test high share CPU
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )


class TestCustomShare(BaseCpuShare):
    """
    Check that two vms that have the same custom CPU share
    are competing evenly on the same core
    """
    vms_cpu_shares = dict(
        (vm_name, 300) for vm_name in BaseCpuShare.vms_to_start
    )

    @tier2
    @polarion("RHEVM3-4983")
    def test_custom_share(self):
        """
        1) Load VM's CPU
        2) Test custom share CPU
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )


class TestPredefinedValues(BaseCpuShare):
    """
    Check that 4 vms that have the different CPU share values
    are taking a different percent of core
    """
    vms_to_start = conf.VM_NAME[:4]
    vms_cpu_shares = {
        conf.VM_NAME[0]: conf.CPU_SHARE_LOW,
        conf.VM_NAME[1]: conf.CPU_SHARE_LOW,
        conf.VM_NAME[2]: conf.CPU_SHARE_MEDIUM,
        conf.VM_NAME[3]: conf.CPU_SHARE_HIGH,
    }
    expected_dict = dict(zip(vms_to_start, (13, 13, 25, 50)))

    @bz({"1304300": {"ppc": conf.PPC_ARCH}})
    @tier1
    @polarion("RHEVM3-4984")
    def test_predefined_values(self):
        """
        1) Load VM's CPU
        2) Test CPU share with Predefined Values
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )


class TestCustomValuesOfShare(BaseCpuShare):
    """
    Check that 4 vms that have the different custom CPU share values
    are taking a different percent of core
    """
    vms_to_start = conf.VM_NAME[:4]
    vms_cpu_shares = {
        conf.VM_NAME[0]: 100,
        conf.VM_NAME[1]: 100,
        conf.VM_NAME[2]: 200,
        conf.VM_NAME[3]: 400,
    }
    expected_dict = dict(zip(vms_to_start, (13, 13, 25, 50)))

    @tier2
    @polarion("RHEVM3-4985")
    def test_custom_values_of_share(self):
        """
        1) Load VM's CPU
        2) Test custom values of share
        """
        assert helpers.load_vms_cpu(vms=self.vms_to_start)
        assert helpers.check_cpu_share(
            vms=self.vms_to_start, expected_dict=self.expected_dict
        )
