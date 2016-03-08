"""
Test power saving scheduler policy under different cpu and memory conditions
"""
import logging
import config as conf
import base_class as base_c
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger(__name__)


class BaseTestPSWithMemory(base_c.StartVms):
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

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad1, cls).setup_class()

    @polarion("RHEVM3-11388")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad2(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory over utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad2, cls).setup_class()

    @polarion("RHEVM3-11390")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad3(BaseTestPSWithMemory):
    """
    Host_1 CPU normal utilized and memory under utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_2 must migrate on Host_1
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad3, cls).setup_class()

    @polarion("RHEVM3-11391")
    def test_vm_migration(self):
        """
        Check if vm from Host_2 migrated on Host_1
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[1], conf.HOSTS[0]))


class TestPSBalanceModuleUnderMemoryAndCPULoad4(BaseTestPSWithMemory):
    """
    Host_1 CPU normal utilized and memory over utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad4, cls).setup_class()

    @polarion("RHEVM3-11393")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad5(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory under utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad5, cls).setup_class()

    @polarion("RHEVM3-11394")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad6(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory over utilized
    Host_2 CPU under utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad6, cls).setup_class()

    @polarion("RHEVM3-11396")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad7(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory under utilized
    Host_2 CPU normal utilized and memory under utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad7, cls).setup_class()

    @polarion("RHEVM3-11397")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad8(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory over utilized
    Host_2 CPU normal utilized and memory under utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad8, cls).setup_class()

    @polarion("RHEVM3-11399")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad9(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory under utilized
    Host_2 CPU normal utilized and memory under utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad9, cls).setup_class()

    @polarion("RHEVM3-11400")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad10(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory normal utilized
    Host_2 CPU normal utilized and memory under utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_NORMALUTILIZED_VMS[0]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad10, cls).setup_class()

    @polarion("RHEVM3-11401")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad11(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory over utilized
    Host_2 CPU normal utilized and memory under utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad11, cls).setup_class()

    @polarion("RHEVM3-11402")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad12(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory normal utilized
    Host_2 CPU normal utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_NORMALUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad12, cls).setup_class()

    @polarion("RHEVM3-11404")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad13(BaseTestPSWithMemory):
    """
    Host_1 CPU normal utilized and memory under utilized
    Host_2 CPU normal utilized and memory normal utilized
    Vm from Host_1 must migrate on Host_2
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: conf.VDS_HOSTS[:2],
                conf.HOST: conf.HOSTS[:2]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad13, cls).setup_class()

    @polarion("RHEVM3-11406")
    def test_vm_migration(self):
        """
        Check if vm from Host_1 migrated on Host_2
        """
        self.assertTrue(self._check_migration(conf.VM_NAME[0], conf.HOSTS[1]))


class TestPSBalanceModuleUnderMemoryAndCPULoad14(BaseTestPSWithMemory):
    """
    Host_1 CPU normal utilized and memory normal utilized
    Host_2 CPU normal utilized and memory normal utilized
    All VMS must stay on old hosts
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Override class parameters
        """
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: conf.VDS_HOSTS[:2],
                conf.HOST: conf.HOSTS[:2]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_NORMALUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad14, cls).setup_class()

    @polarion("RHEVM3-11407")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad15(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory under utilized
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
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad15, cls).setup_class()

    @polarion("RHEVM3-11412")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=1
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad16(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory over utilized
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
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad16, cls).setup_class()

    @polarion("RHEVM3-11414")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad17(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory under utilized
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
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad17, cls).setup_class()

    @polarion("RHEVM3-11415")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=1
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad18(BaseTestPSWithMemory):
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
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_NORMALUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad18, cls).setup_class()

    @polarion("RHEVM3-11416")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad19(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory over utilized
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
            conf.CPU_LOAD_50: {
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            },
            conf.CPU_LOAD_100: {
                conf.RESOURCE: [conf.VDS_HOSTS[0]],
                conf.HOST: [conf.HOSTS[0]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_OVERUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad19, cls).setup_class()

    @polarion("RHEVM3-11417")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad20(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory under utilized
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
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad20, cls).setup_class()

    @polarion("RHEVM3-11418")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=1
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad21(BaseTestPSWithMemory):
    """
    Host_1 CPU under utilized and memory over utilized
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
                conf.RESOURCE: [conf.VDS_HOSTS[1]],
                conf.HOST: [conf.HOSTS[1]]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad21, cls).setup_class()

    @polarion("RHEVM3-11419")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class TestPSBalanceModuleUnderMemoryAndCPULoad22(BaseTestPSWithMemory):
    """
    Host_1 CPU over utilized and memory over utilized
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
                conf.RESOURCE: conf.VDS_HOSTS[:2],
                conf.HOST: conf.HOSTS[:2]
            }
        }
        cls.load_memory_d = {
            conf.HOSTS[0]: conf.LOAD_OVERUTILIZED_VMS[0],
            conf.HOSTS[1]: conf.LOAD_NORMALUTILIZED_VMS[1]
        }
        super(TestPSBalanceModuleUnderMemoryAndCPULoad22, cls).setup_class()

    @polarion("RHEVM3-11423")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=2
            )
        )


class StartAndMigrateVmPSBase(base_c.StartAndMigrateVmBase):
    cluster_policy = {
        conf.CLUSTER_POLICY_NAME: conf.CLUSTER_POLICY_PS,
        conf.CLUSTER_POLICY_PARAMS: conf.DEFAULT_PS_PARAMS
    }
    update_vm_d = {
        conf.VM_NAME[0]: {
            "memory": 2 * conf.GB,
            "memory_guaranteed": 2 * conf.GB
        }
    }


class TestStartVm(StartAndMigrateVmPSBase):
    """
    Host_1 and Host_2 CPU normal utilized
    Load additional one GB of memory on Host_1
    Start additional VM, VM must start on Host_1
    """
    __test__ = True
    vm_to_start = conf.VM_NAME[3]

    @bz({"1260381": {}})
    @polarion("RHEVM3-11645")
    def test_start_vm(self):
        """
        1) Start vm
        2) Check that vm started on correct host
        """
        self.assertTrue(
            ll_vms.startVm(positive=True, vm=self.vm_to_start),
            "Failed to start vm %s" % self.vm_to_start
        )
        vm_host = ll_vms.get_vm_host(vm_name=self.vm_to_start)
        self.assertEqual(
            vm_host, conf.HOSTS[0],
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


class TestMigrateVm(StartAndMigrateVmPSBase):
    """
    Host_1 and Host_2 CPU normal utilized
    Load additional one GB of memory on Host_1
    Migrate VM from Host_3, VM must migrate to Host_1
    """
    __test__ = True
    vm_to_migrate = conf.VM_NAME[2]

    @polarion("RHEVM3-11646")
    def test_migrate_vm(self):
        """
        1) Migrate vm
        2) Check that vm migrated to correct host
        """
        self.assertTrue(
            ll_vms.migrateVm(positive=True, vm=self.vm_to_migrate),
            "Failed to migrate vm %s" % self.vm_to_migrate
        )
        vm_host = ll_vms.get_vm_host(vm_name=self.vm_to_migrate)
        self.assertEqual(
            vm_host, conf.HOSTS[0],
            "Vm %s migrated to wrong host %s" % (self.vm_to_migrate, vm_host)
        )


class TestTakeInAccountVmMemory(StartAndMigrateVmPSBase):
    """
    Host_1 and Host_2 CPU normal utilized
    Host_2 memory overutilized
    Host_1 has memory near overutilized value,
     so if engine will migrate additional vm on Host_1,
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
            conf.VM_NAME[0]: {
                "memory": (
                    conf.DEFAULT_PS_PARAMS[
                        conf.MIN_FREE_MEMORY
                    ] * conf.MB - conf.GB / 2
                ),
                "memory_guaranteed": (
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

    @polarion("RHEVM3-12339")
    def test_vm_migration(self):
        """
        Check if all vms stay on old hosts
        """
        self.assertFalse(
            self._is_migration_not_happen(
                host_name=conf.HOSTS[0], expected_num_of_vms=1
            )
        )
