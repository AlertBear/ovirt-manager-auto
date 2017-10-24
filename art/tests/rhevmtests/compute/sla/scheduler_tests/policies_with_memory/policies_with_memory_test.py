"""
Test power saving and even distribution scheduler policy 
under different CPU and memory conditions
"""
from art.test_handler.tools import polarion
from base_class import *  # flake8: noqa
from rhevmtests.compute.sla.fixtures import stop_vms


class BasePSWithMemory(BaseStartVmsUnderPolicyWithMemory):
    """
    Base class for PS scheduler tests with the memory load
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_PS_CPU,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }


class TestPSBalanceModuleUnderMemoryAndCPULoad1(BasePSWithMemory):
    """
    Host_0 CPU and memory under utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_0

    @polarion("RHEVM3-11388")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad2(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory over utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_1

    @polarion("RHEVM3-11390")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad3(BasePSWithMemory):
    """
    Host_0 CPU normal utilized and memory under utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_1 must migrate on the Host_0
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_0
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_0

    @polarion("RHEVM3-11391")
    def test_vm_migration(self):
        """
        Check if VM from the Host_1 migrated on the Host_0
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad4(BasePSWithMemory):
    """
    Host_0 CPU normal utilized and memory over utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_0
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_1

    @polarion("RHEVM3-11393")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad5(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory under utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_0

    @polarion("RHEVM3-11394")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad6(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory over utilized
    Host_1 CPU under utilized and memory normal utilized
    VM from the Host_0 must migrate the on Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_1

    @polarion("RHEVM3-11396")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad7(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory under utilized
    Host_1 CPU normal utilized and memory under utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_2
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_0

    @polarion("RHEVM3-11397")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad8(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory over utilized
    Host_1 CPU normal utilized and memory under utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_2
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11399")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad9(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory under utilized
    Host_1 CPU normal utilized and memory under utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_0

    @polarion("RHEVM3-11400")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad10(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU normal utilized and memory under utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.LOAD_NORMALUTILIZED_VMS[0]: {conf.VM_RUN_ONCE_HOST: 0}
    }

    @polarion("RHEVM3-11401")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad11(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory over utilized
    Host_1 CPU normal utilized and memory under utilized
    VM from Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11402")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad12(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory normal utilized
    Host_1 CPU normal utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_2
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_3

    @polarion("RHEVM3-11404")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad13(BasePSWithMemory):
    """
    Host_0 CPU normal utilized and memory under utilized
    Host_1 CPU normal utilized and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_4
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_0

    @polarion("RHEVM3-11406")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad14(BasePSWithMemory):
    """
    Host_0 CPU normal utilized and memory normal utilized
    Host_1 CPU normal utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_4
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_3

    @polarion("RHEVM3-11407")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad15(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory under utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_2
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_5

    @polarion("RHEVM3-11412")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad16(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory over utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_2
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_4

    @polarion("RHEVM3-11414")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad17(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory under utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_5

    @polarion("RHEVM3-11415")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad18(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = {
        conf.VM_NAME[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.VM_NAME[1]: {conf.VM_RUN_ONCE_HOST: 1},
        conf.LOAD_NORMALUTILIZED_VMS[0]: {conf.VM_RUN_ONCE_HOST: 0},
        conf.LOAD_OVERUTILIZED_VMS[1]: {conf.VM_RUN_ONCE_HOST: 1}
    }

    @polarion("RHEVM3-11416")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad19(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory over utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_3
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_4

    @polarion("RHEVM3-11417")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad20(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory under utilized
    Host_1 CPU over utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_5
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_0

    @polarion("RHEVM3-11418")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad21(BasePSWithMemory):
    """
    Host_0 CPU under utilized and memory over utilized
    Host_1 CPU over utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_5
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_1

    @polarion("RHEVM3-11419")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad22(BasePSWithMemory):
    """
    Host_0 CPU over utilized and memory over utilized
    Host_1 CPU over utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_6
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_1

    @polarion("RHEVM3-11423")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0],
            expected_num_of_vms=2,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class BaseUpdateAndStartVmPS(BaseUpdateAndStartVmsUnderPolicyWithMemory):
    """
    Base class for VM start and migration under PS scheduler policy
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_PS_MEMORY,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    vms_to_params = {
        conf.VM_NAME[0]: {
            conf.VM_MEMORY: 2 * conf.GB,
            conf.VM_MEMORY_GUARANTEED: 2 * conf.GB
        }
    }
    vms_to_run = conf.DEFAULT_VMS_TO_RUN_1


@pytest.mark.usefixtures(stop_vms.__name__)
class TestStartVmPS(BaseUpdateAndStartVmPS):
    """
    Host_0, Host_1 and Host_2 CPU normal utilized
    Load additional one GB of memory on the Host_0
    Start additional VM, VM must start on the Host_0
    """
    vms_to_stop = [conf.VM_NAME[3]]

    @polarion("RHEVM3-11645")
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


class TestMigrateVmPS(BaseUpdateAndStartVmPS):
    """
    Host_0, Host_1 and Host_2 CPU normal utilized
    Load additional one GB of memory on the Host_0
    Migrate VM from the Host_2, VM must migrate on the Host_0
    """

    @polarion("RHEVM3-11646")
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


class TestTakeInAccountVmMemoryPS(BaseTakeVmMemoryInAccount):
    """
    Host_0 and Host_1 CPU normal utilized
    Host_0 and Host_1 memory overutilized
    Host_2 has memory near overutilized value,
     so if the engine will migrate additional VM on the Host_2,
     it will overutilized host memory
    All VM's must stay on old hosts
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_PS_MEMORY,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_PS_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }

    @polarion("RHEVM3-12339")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )


class BaseEDWithMemory(BaseStartVmsUnderPolicyWithMemory):
    """
    Base class for ED scheduler tests with the memory load
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_ED_CPU,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }


class TestEDBalanceModuleUnderMemoryAndCPULoad1(BaseEDWithMemory):
    """
    Host_0 CPU and memory normal utilized
    Host_1 CPU and memory normal utilized
    All VM's must stay on old hosts
    """
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
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad2(BaseEDWithMemory):
    """
    Host_0 CPU normal utilized and memory over utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11633")
    def test_vm_migration(self):
        """
        Check if VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad3(BaseEDWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_7

    @polarion("RHEVM3-11634")
    def test_vm_migration(self):
        """
        Check if the VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad4(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU and memory normal utilized
    VM from the Host_0 must migrate on the Host_1
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
    vms_to_run = conf.MEMORY_LOAD_VMS_TO_RUN_2

    @polarion("RHEVM3-11635")
    def test_vm_migration(self):
        """
        Check if the VM from the Host_0 migrated on the Host_1
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1],
            expected_num_of_vms=2,
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad5(BaseEDWithMemory):
    """
    Host_0 CPU over utilized and memory normal utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
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
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad6(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU normal utilized and memory over utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_1
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
            additional_vms=conf.VM_NAME[4:6]
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad7(BaseEDWithMemory):
    """
    Host_0 CPU and memory over utilized
    Host_1 CPU over utilized and memory normal utilized
    All VM's must stay on old hosts
    """
    hosts_cpu_load = conf.HOST_CPU_LOAD_6
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
            additional_vms=conf.VM_NAME[4:6]
        )


class BaseUpdateAndStartVmED(BaseUpdateAndStartVmsUnderPolicyWithMemory):
    """
    Base class for VM start and migration under ED scheduler policy
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_ED_MEMORY,
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


class TestTakeInAccountVmMemoryED(BaseTakeVmMemoryInAccount):
    """
    Host_0 and Host_1 CPU normal utilized
    Host_0 and Host_1 memory overutilized
    Host_2 has memory near overutilized value,
     so if the engine will migrate additional VM on the Host_2,
     it will overutilized host memory
    All VM's must stay on old hosts
    """
    cluster_to_update_params = {
        conf.CLUSTER_SCH_POLICY: conf.POLICY_CUSTOM_ED_MEMORY,
        conf.CLUSTER_SCH_POLICY_PROPERTIES: conf.DEFAULT_ED_PARAMS,
        conf.CLUSTER_OVERCOMMITMENT: conf.CLUSTER_OVERCOMMITMENT_NONE
    }
    hosts_cpu_load = {conf.CPU_LOAD_50: xrange(2)}

    @polarion("RHEVM3-12340")
    def test_vm_migration(self):
        """
        Check if all VM's stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2],
            expected_num_of_vms=1,
            negative=True,
            additional_vms=conf.VM_NAME[4:6]
        )
