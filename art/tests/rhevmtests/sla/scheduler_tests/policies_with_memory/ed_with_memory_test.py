"""
Test even distribution scheduler policy
under different cpu and memory conditions
"""
import logging

import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import base_class as base_c
import config as conf
import rhevmtests.sla.scheduler_tests.helpers as sch_helpers
from art.test_handler.tools import polarion

logger = logging.getLogger(__name__)


class BaseTestEDWithMemory(base_c.StartVms):
    """
    Base class for ED scheduler tests with memory load
    """
    cluster_policy = {
        conf.CLUSTER_POLICY_NAME: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_POLICY_PARAMS: conf.DEFAULT_ED_PARAMS
    }


class TestEDBalanceModuleUnderMemoryAndCPULoad1(BaseTestEDWithMemory):
    """
    Host_1 CPU and memory normal utilized
    Host_2 CPU and memory normal utilized
    All VMS must stay on old hosts
    """
    __test__ = True

    @polarion("RHEVM3-11632")
    def test_vm_migration(self):
        """
        Check if all VMS stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad2(BaseTestEDWithMemory):
    """
    Host_1 CPU normal utilized and memory over utilized
    Host_2 CPU and memory normal utilized
    VM from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0]
        }
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[2]],
                conf.HOST: [conf.HOSTS[2]]
            }
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad2, cls).setup_class()

    @polarion("RHEVM3-11633")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1], expected_num_of_vms=2
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad3(BaseTestEDWithMemory):
    """
    Host_1 CPU over utilized and memory normal utilized
    Host_2 CPU and memory normal utilized
    VM from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0], conf.VDS_HOSTS[2]],
                conf.HOST: [conf.HOSTS[0], conf.HOSTS[2]]
            }
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad3, cls).setup_class()

    @polarion("RHEVM3-11634")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1], expected_num_of_vms=2
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad4(BaseTestEDWithMemory):
    """
    Host_1 CPU and memory over utilized
    Host_2 CPU and memory normal utilized
    VM from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0], conf.VDS_HOSTS[2]],
                conf.HOST: [conf.HOSTS[0], conf.HOSTS[2]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0]
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad4, cls).setup_class()

    @polarion("RHEVM3-11635")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        assert sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[1], expected_num_of_vms=2
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad5(BaseTestEDWithMemory):
    """
    Host_1 CPU over utilized and memory normal utilized
    Host_2 CPU normal utilized and memory over utilized
    All VMS must stay on old hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0], conf.VDS_HOSTS[2]],
                conf.HOST: [conf.HOSTS[0], conf.HOSTS[2]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad5, cls).setup_class()

    @polarion("RHEVM3-11636")
    def test_vm_migration(self):
        """
        Check if all VMS stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=1, negative=True
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad6(BaseTestEDWithMemory):
    """
    Host_1 CPU and memory over utilized
    Host_2 CPU normal utilized and memory over utilized
    All VMS must stay on old hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0], conf.VDS_HOSTS[2]],
                conf.HOST: [conf.HOSTS[0], conf.HOSTS[2]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad6, cls).setup_class()

    @polarion("RHEVM3-11637")
    def test_vm_migration(self):
        """
        Check if all VMS stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=2, negative=True
        )


class TestEDBalanceModuleUnderMemoryAndCPULoad7(BaseTestEDWithMemory):
    """
    Host_1 CPU and memory over utilized
    Host_2 CPU over utilized and memory normal utilized
    All VMS must stay on old hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: conf.VDS_HOSTS[:3],
                conf.HOST: conf.HOSTS[:3]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0]
        }
        super(TestEDBalanceModuleUnderMemoryAndCPULoad7, cls).setup_class()

    @polarion("RHEVM3-11639")
    def test_vm_migration(self):
        """
        Check if all VMS stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[0], expected_num_of_vms=2, negative=True
        )


class StartAndMigrateVmEDBase(base_c.StartAndMigrateVmBase):
    """
    Base class for start and migrate of VM under ED scheduler policy
    """
    cluster_policy = {
        conf.CLUSTER_POLICY_NAME: conf.POLICY_EVEN_DISTRIBUTION,
        conf.CLUSTER_POLICY_PARAMS: conf.DEFAULT_ED_PARAMS
    }
    update_vm_d = {
        conf.VM_NAME[0]: {
            conf.VM_MEMORY: 256 * conf.MB,
            conf.VM_MEMORY_GUARANTEED: 256 * conf.MB
        }
    }


class TestStartVm(StartAndMigrateVmEDBase):
    """
    Host_1, Host_2 and Host_3 CPU normal utilized
    Host_1 has more scheduling memory to start VM than Host_2
    Start additional VM, VM must start on Host_1
    """
    __test__ = True
    vm_to_start = conf.VM_NAME[3]

    @polarion("RHEVM3-11643")
    def test_start_vm(self):
        """
        1) Start vm
        2) Check that vm started on correct host
        """
        assert ll_vms.startVm(
            positive=True, vm=self.vm_to_start
        ), "Failed to start vm %s" % self.vm_to_start
        vm_host = ll_vms.get_vm_host(vm_name=self.vm_to_start)
        assert vm_host == conf.HOSTS[0], (
            "Vm %s started on wrong host %s" % (self.vm_to_start, vm_host)
        )

    @classmethod
    def teardown_class(cls):
        """
        Stop additional vm
        """
        logger.info("Stop vm %s", cls.vm_to_start)
        if not ll_vms.stopVm(positive=True, vm=cls.vm_to_start):
            logger.error("Failed to stop vm %s", cls.vm_to_start)
        super(TestStartVm, cls).teardown_class()


class TestMigrateVm(StartAndMigrateVmEDBase):
    """
    Host_1, Host_2 and Host_3 CPU normal utilized
    Load additional one GB of memory on Host_1
    Migrate VM from Host_3, VM must migrate to Host_1
    """
    __test__ = True
    vm_to_migrate = conf.VM_NAME[2]

    @polarion("RHEVM3-11644")
    def test_migrate_vm(self):
        """
        1) Migrate vm
        2) Check that vm migrated to correct host
        """
        assert ll_vms.migrateVm(
            positive=True, vm=self.vm_to_migrate
        ), "Failed to migrate vm %s" % self.vm_to_migrate
        vm_host = ll_vms.get_vm_host(vm_name=self.vm_to_migrate)
        assert vm_host == conf.HOSTS[0], (
            "Vm %s migrated to wrong host %s" % (self.vm_to_migrate, vm_host)
        )


class TestTakeInAccountVmMemory(StartAndMigrateVmEDBase):
    """
    Host_1 and Host_2 CPU normal utilized
    Host_1 and Host_2 memory overutilized
    Host_3 has memory near overutilized value,
     so if engine will migrate additional vm on Host_3,
     it will overutilized host memory
    All vms must stay on old hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Override vm update parameters
        2) Override memory load parameters
        """
        cls.update_vm_d = {
            conf.VM_NAME[2]: {
                conf.VM_MEMORY: (
                    conf.DEFAULT_PS_PARAMS[
                        conf.MIN_FREE_MEMORY
                    ] * conf.MB - conf.GB / 2
                ),
                conf.VM_MEMORY_GUARANTEED: (
                    conf.DEFAULT_PS_PARAMS[
                        conf.MIN_FREE_MEMORY
                    ] * conf.MB - conf.GB / 2
                )
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestTakeInAccountVmMemory, cls).setup_class()

    @polarion("RHEVM3-12340")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        assert not sch_helpers.is_balancing_happen(
            host_name=conf.HOSTS[2], expected_num_of_vms=1, negative=True
        )
