"""
Test power saving scheduler policy under different cpu and memory conditions
"""
import logging
import config as conf
import base_class as base_c
from art.test_handler.tools import polarion  # pylint: disable=E0611

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
                host_name=conf.HOSTS[0], expected_num_of_vms=2
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
                host_name=conf.HOSTS[0], expected_num_of_vms=2
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
                host_name=conf.HOSTS[0], expected_num_of_vms=2
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
