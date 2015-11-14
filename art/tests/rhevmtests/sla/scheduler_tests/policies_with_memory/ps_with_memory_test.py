"""
Test power saving scheduler policy under different cpu and memory conditions
"""
import logging
import config as conf
import base_class as base_c
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger(__name__)


class BaseTestPSWithMemory(base_c.StartVmsClass):
    """
    Base class for scheduler tests with memory load
    """
    cluster_policy = {
        conf.CLUSTER_POLICY_NAME: conf.CLUSTER_POLICY_PS,
        conf.CLUSTER_POLICY_PARAMS: conf.DEFAULT_PS_PARAMS
    }


class TestPSBalanceModuleUnderMemoryAndCPULoad1(BaseTestPSWithMemory):
    """
    Host_1 CPU and memory under utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True
    load_memory_d = {
        conf.HOSTS_WITH_DUMMY[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
    }

    @polarion("RHEVM3-11388")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(
            ll_vms.is_vm_run_on_host(
                vm_name=conf.VM_NAME[0],
                host_name=conf.HOSTS[1],
                timeout=conf.MIGRATION_TIMEOUT
            ),
            "VM %s still run on host %s" % (conf.VM_NAME[0], conf.HOSTS[1])
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad2(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory over utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True
    load_memory_d = {
        conf.HOSTS_WITH_DUMMY[0]: conf.LOAD_OVERUTILIZED_VMS[0],
        conf.HOSTS_WITH_DUMMY[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
    }

    @polarion("RHEVM3-11390")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(
            ll_vms.is_vm_run_on_host(
                vm_name=conf.VM_NAME[0],
                host_name=conf.HOSTS[1],
                timeout=conf.MIGRATION_TIMEOUT
            ),
            "VM %s still run on host %s" % (conf.VM_NAME[0], conf.HOSTS[1])
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad3(BaseTestPSWithMemory):
    """
    Host_1 CPU normal utilized and memory under utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_2 must migrate on Host_1
    """
    __test__ = True
    load_cpu_d = {
        conf.CPU_LOAD_50: {
            conf.RESOURCE: [conf.VDS_HOSTS_WITH_DUMMY[0]],
            conf.HOST: [conf.HOSTS_WITH_DUMMY[0]]
        }
    }
    load_memory_d = {
        conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
    }

    @polarion("RHEVM3-11391")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(
            ll_vms.is_vm_run_on_host(
                vm_name=conf.VM_NAME[1],
                host_name=conf.HOSTS[0],
                timeout=conf.MIGRATION_TIMEOUT
            ),
            "VM %s still run on host %s" % (conf.VM_NAME[1], conf.HOSTS[0])
        )
