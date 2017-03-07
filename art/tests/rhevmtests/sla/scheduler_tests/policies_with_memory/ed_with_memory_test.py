"""
Test EvenDistribution scheduler policy
under different cpu and memory conditions
"""
from art.test_handler.tools import polarion
from base_class import *  # flake8: noqa
from rhevmtests.sla.fixtures import stop_vms


class BaseEDWithMemory(BaseStartVmsUnderPolicyWithMemory):
    """
    Base class for ED scheduler tests with the memory load
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }


class TestEDBalanceModuleUnderMemoryAndCPULoad1(BaseEDWithMemory):
    """
    Host_0 CPU and memory normal utilized
    Host_1 CPU and memory normal utilized
    All VM's must stay on old hosts
    """
    __test__ = True
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_0

    @polarion("RHEVM3-11632")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad2(BaseEDWithMemory):
    """
    Host_0 CPU normal utilized and memory over utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    __test__ = True
    hosts_cpu_load = {conf.CPU_LOAD_100: [2]}
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11633")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad3(BaseEDWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    __test__ = True
    hosts_cpu_load = conf.HOST_CPU_LOAD_7
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_0

    @polarion("RHEVM3-11634")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad4(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    __test__ = True
    hosts_cpu_load = conf.HOST_CPU_LOAD_7
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11635")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad5(BaseEDWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    __test__ = True
    hosts_cpu_load = conf.HOST_CPU_LOAD_7
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_5

    @polarion("RHEVM3-11636")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad6(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    __test__ = True
    hosts_cpu_load = conf.HOST_CPU_LOAD_7
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_4

    @polarion("RHEVM3-11637")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[3:5]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad7(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU over utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    __test__ = True
    hosts_cpu_load = {conf.CPU_LOAD_100: xrange(3)}
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11639")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[3:5]
        )


class BaseUpdateAndStartVmED(BaseUpdateAndStartVmsUnderPolicyWithMemory):
    """
    Base class for VM start and migration under ED scheduler policy
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_MEMORY: 256 * conf.MB,
            conf.VM_MEMORY_GUARANTEED: 256 * conf.MB
        }
    }
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_1


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmED(BaseUpdateAndStartVmED):
    """
    Host_0, Host_1 and Host_2 CPU normal utilized
    Host_0 has more scheduling memory to start VM's than Host_1
    Start additional VM, VM must start on the Host_0
    """
    __test__ = True
    vms_to_stop = [conf.VM_NAME[3]]

    @polarion("RHEVM3-11643")
    def test_start_vm(self):
        """
        1) Start VM
        2) Check that VM started on the correct host
        """
        u_libs.testflow.step("Start the VM %s", conf.VM_NAME[3])
        assert ll_vms.startVm(positive=True, vm=conf.VM_NAME[3])

        vm_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[3])
        u_libs.testflow.step(
            "Check that VM %s started on the host %s",
            conf.VM_NAME[3], conf.HOSTS[0]
        )
        assert vm_host == conf.HOSTS[0]


class TestMigrateVmED(BaseUpdateAndStartVmED):
    """
    Host_0, Host_1 and Host_2 CPU normal utilized
    Load additional one GB of memory on the Host_0
    Migrate VM from the Host_2, VM must migrate on the Host_0
    """
    __test__ = True

    @polarion("RHEVM3-11644")
    def test_migrate_vm(self):
        """
        1) Migrate the VM
        2) Check that VM migrated on correct host
        """
        u_libs.testflow.step("Migrate the VM %s", conf.VM_NAME[2])
        assert ll_vms.migrateVm(positive=True, vm=conf.VM_NAME[2])

        vm_host = ll_vms.get_vm_host(vm_name=conf.VM_NAME[2])
        u_libs.testflow.step(
            "Check that VM %s migrated on the host %s",
            conf.VM_NAME[2], conf.HOSTS[0]
        )
        assert vm_host == conf.HOSTS[0]


class TestTakeInAccountVmMemoryED(BaseUpdateAndStartVmED):
    """
    Host_0 and Host_1 CPU normal utilized
    Host_0 and Host_1 memory overutilized
    Host_2 has memory near overutilized value,
     so if the engine will migrate additional VM on the Host_2,
     it will overutilized host memory
    All VM's must stay on old hosts
    """
    __test__ = True
    vms_to_params = {
        conf.VM_NAME[2]: conf.MEMORY_NEAR_OVERUTILIZED
    }
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_6

    @polarion("RHEVM3-12340")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[3:5]
        )
