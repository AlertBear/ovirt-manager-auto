"""
Numa - Numa Test
Check creation of VNUMA on vm, run it on host with NUMA architecture and
pining of VNUMA to host NUMA
"""
import os
import logging

from rhevmtests.sla.numa import config as c
from art.rhevm_api.resources import Host, RootUser

from art.unittest_lib import attr
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import SlaTest as TestCase
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as vm_api
import art.rhevm_api.tests_lib.low_level.hosts as host_api

logger = logging.getLogger(__name__)


@attr(tier=4)
class BaseNumaClass(TestCase):
    """
    Base class for Numa Test
    """
    __test__ = False
    host_executor_1 = None
    default_numa_node_params = {
        "index": 1, "memory": 1024, "cores": [0], "pin_list": [0]
    }

    @classmethod
    def setup_class(cls):
        """
        Get hosts executors
        """
        cls.host_executor_1 = c.VDS_HOSTS[0].executor()

    @classmethod
    def _get_numa_parameters_from_resource(cls, resource_executor):
        """
        Get numa parameters from host

        :param resource_executor: resource executor
        :type resource_executor: instance of RemoteExecutor
        :returns: dictionary of parameters({node_index: {cpus, memory}})
        :rtype: dict
        """
        param_dict = {}
        rc, out, err = resource_executor.run_cmd([c.NUMACTL, "-H"])
        if rc:
            logger.error(
                "Failed to get numa information from resource, err: %s", err
            )
            return param_dict
        lines = out.splitlines()
        for line in lines:
            line = line.replace(":", "")
            line_arr = line.split()
            if line_arr[0] == c.NUMA_NODE:
                if line_arr[1] == c.NUMA_NODE_DISTANCE:
                    break
                node_name = int(line_arr[1])
                if node_name not in param_dict:
                    param_dict[node_name] = {}
                if line_arr[2] == c.NUMA_NODE_CPUS:
                    param_dict[node_name][line_arr[2]] = [
                        int(value) for value in line_arr[3:]
                    ]
                else:
                    param_dict[node_name][line_arr[2]] = [int(line_arr[3])]
        return param_dict

    @classmethod
    def _get_vm_executor(cls, vm_name):
        """
        Get vm executor

        :param vm_name: name of vm
        :type vm_name: str
        :returns: vm executor
        :rtype: instance of RemoteExecutor or None
        """
        logger.info("Get ip from vm %s", vm_name)
        status, vm_ip = vm_api.waitForIP(
            vm_name, timeout=c.VM_IP_TIMEOUT
        )
        if not status:
            logger.error("Failed to receive ip from vm %s", c.VM_NAME[0])
            return None
        logger.info(
            "Create VDS instance with root user from vm with ip %s",
            vm_ip["ip"]
        )
        v = Host(vm_ip["ip"])
        v.users.append(RootUser(c.VMS_LINUX_PW))
        return v.executor()

    @classmethod
    def _get_numa_parameters_from_vm(cls, vm_name):
        """
        Get numa parameters from vm

        :param vm_name: vm name
        :type vm_name: str
        :returns: dictionary of parameters({node_index: {cpus, memory}})
        :rtype: dict
        """
        params_dict = {}
        vm_executor = cls._get_vm_executor(vm_name)
        if not vm_executor:
            return params_dict
        return cls._get_numa_parameters_from_resource(vm_executor)

    @classmethod
    def _get_pining_of_vm_from_host(cls, host_executor, vm_name, pinning_type):
        """
        Get information about cpu and memory pining of vm from host

        :param host_executor: host executor
        :type host_executor: instance of RemoteExecutor
        :param vm_name: vm name
        :type vm_name: str
        :param pinning_type: pinning type(cpu, memory)
        :type pinning_type: str
        :returns: dictionary with pinning information
        :rtype: dict
        """
        pinning_dict = {}
        vm_pid = cls._get_vm_process_pid(host_executor, vm_name)
        cmd = [
            "cat", "/proc/%s/task/*/status" % vm_pid, "|", "grep", pinning_type
        ]
        rc, out, err = host_executor.run_cmd(cmd)
        if rc:
            logger.error(
                "Failed to get pinning information about vm %s, err: %s",
                vm_name, err
            )
            return pinning_dict
        for proc_index, line in enumerate(out.splitlines()):
            pinning_arr = []
            line_arr = line.split(":")
            if "," in line_arr[1]:
                values_arr = line_arr[1].split(",")
                for values in values_arr:
                    pinning_arr.extend(
                        cls.__get_values_from_pinning(values)
                    )
            else:
                pinning_arr.extend(
                    cls.__get_values_from_pinning(line_arr[1])
                )
            pinning_dict[proc_index] = pinning_arr
        return pinning_dict

    @classmethod
    def __get_values_from_pinning(cls, values):
        """
        Return pinning values for lines that include "-"

        :param values: values that include "-"
        :type values: str
        :returns: list of pinning values
        :rtype: list
        """
        pinning_arr = []
        if "-" in values:
            value = values.split("-")
            pinning_arr.extend(
                range(int(value[0]), int(value[1]) + 1)
            )
        else:
            pinning_arr.append(int(values))
        return pinning_arr

    @classmethod
    def _get_vm_process_pid(cls, host_executor, vm_name):
        """
        Get vm process pid

        :param host_executor: host executor
        :type host_executor: instance of RemoteExecutor
        :param vm_name: vm name
        :type vm_name: str
        :returns: vm process pid
        :rtype: str
        :raises: HostException
        """
        vm_pid_file = os.path.join(
            c.LIBVIRTD_PID_DIRECTORY, "%s.pid" % vm_name
        )
        cmd = ["cat", vm_pid_file]
        rc, out, err = host_executor.run_cmd(cmd)
        if rc:
            raise errors.HostException(
                "Failed to get vm %s process pid, err: " % vm_name, err
            )
        return out

    @classmethod
    def _get_numa_mode_from_vm_process(cls, host_executor, vm_name):
        """
        Get information about numa mode for vm process

        :param host_executor: host executor
        :type host_executor: instance of RemoteExecutor
        :param vm_name: vm name
        :type vm_name: str
        :returns: numa memory mode
        :rtype: str
        """
        numa_mode = ""
        vm_pid = cls._get_vm_process_pid(host_executor, vm_name)
        cmd = ["tail", "-n", "1", "/proc/%s/numa_maps" % vm_pid]
        rc, out, err = host_executor.run_cmd(cmd)
        if rc:
            logger.error(
                "Failed to get numa mode information about vm %s, err: %s",
                vm_name, err
            )
            return numa_mode
        return out.split()[1].split(":")[0]

    @classmethod
    def _create_number_of_equals_numa_nodes(
            cls, vm_name, host_executor, num_of_numa_nodes
    ):
        """
        Create list of given number of numa nodes,
        with equal amount of memory and cpu

        :param vm_name: vm name
        :type vm_name: str
        :param host_executor: host executor
        :type host_executor: instance of RemoteExecutor
        :param num_of_numa_nodes: number of numa nodes to create
        :type num_of_numa_nodes: int
        :returns: list of numa nodes
        :rtype: list
        """
        numa_nodes_list = []
        h_numa_node_indexes = cls._get_numa_parameters_from_resource(
            host_executor
        ).keys()
        v_numa_node_memory = vm_api.get_vm_memory(
            vm_name
        ) / num_of_numa_nodes / c.MB
        v_numa_node_cores = vm_api.get_vm_cores(vm_name) / num_of_numa_nodes
        for index in range(num_of_numa_nodes):
            cores = range(
                index * v_numa_node_cores,
                (index + 1) * v_numa_node_cores
            )
            numa_node_dict = {
                "index": index, "memory": v_numa_node_memory, "cores": cores,
                "pin_list": [h_numa_node_indexes[index]]
            }
            numa_nodes_list.append(numa_node_dict)
        return numa_nodes_list

    @classmethod
    def _update_vm_numa_mode(cls, vm_name, numa_mode):
        """
        Update vm numa mode

        :param vm_name: vm name
        :type vm_name: str
        :param numa_mode: numa mode
        :type numa_mode: str
        :raises: VMException
        """
        logging.info("Update vm %s numa mode to %s", vm_name, numa_mode)
        if not vm_api.updateVm(True, vm_name, numa_mode=numa_mode):
            raise errors.VMException("Failed to update vm %s" % vm_name)

    @classmethod
    def _get_os_version(cls, resource):
        """
        Get os version from vm or host

        :param resource: host or vm resource
        :type resource: instance of VDS
        :returns: tuple of major and minor version
        :rtype: tuple
        :raises: HostException
        """
        ver_arr = resource.get_os_info()['ver'].split(".")
        return ver_arr[0], ver_arr[1]


class TestGetNumaStatisticFromHost(BaseNumaClass):
    """
    Check that engine receives correct information from host about numa nodes
    """
    __test__ = True

    @polarion("RHEVM3-9546")
    def test_check_numa_statistics(self):
        """
        Check that information about numa nodes in engine and on host the same
        """
        numa_nodes_params = self._get_numa_parameters_from_resource(
            self.host_executor_1
        )
        logger.info("Numa node parameters: %s", numa_nodes_params)
        for node_index, numa_node_param in numa_nodes_params.iteritems():
            numa_node_obj = host_api.get_numa_node_by_index(
                c.HOSTS[0], node_index
            )
            logger.info(
                "Check that engine receives correct "
                "memory value for node %s and host %s",
                node_index, c.HOSTS[0]
            )
            memory_from_engine = host_api.get_numa_node_memory(numa_node_obj)
            self.assertEqual(
                memory_from_engine, numa_node_param[c.NUMA_NODE_MEMORY][0],
                "Memory numa node values not equal: "
                "from engine: %s and from numactl: %s" %
                (memory_from_engine, numa_node_param[c.NUMA_NODE_MEMORY][0])
            )
            logger.info(
                "Check that engine receives correct "
                "cpu's value for node %s and host %s",
                node_index, c.HOSTS[0]
            )
            cpus_from_engine = host_api.get_numa_node_cpus(numa_node_obj)
            self.assertEqual(
                cpus_from_engine, numa_node_param[c.NUMA_NODE_CPUS],
                "Cpu's numa node values not equal: "
                "from engine: %s and from numactl: %s" %
                (memory_from_engine, numa_node_param[c.NUMA_NODE_CPUS])
            )


class UpdateVm(BaseNumaClass):
    """
    Base class for test cases that update vm
    """
    __test__ = False
    old_vm_params = {
        "memory": c.GB,
        "memory_guaranteed": c.GB,
        "cpu_cores": 1,
        "cpu_socket": 1,
        "placement_host": c.VM_ANY_HOST,
        "placement_affinity": c.VM_MIGRATABLE,
        "vcpu_pinning": []
    }
    new_vm_params = None
    num_of_vm_numa_nodes = 1
    vms_to_update = c.VM_NAME[:1]

    @classmethod
    def _add_numa_node(cls, vm_name, numa_node_params):
        """
        Add default numa node to give vm

        :param vm_name: vm name
        :type vm_name: str
        :param numa_node_params: parameters for numa node
        :type numa_node_params: dict
        :returns: True, if operation success, otherwise False
        :rtype: bool
        """
        logger.info(
            "Add numa node to vm %s, with parameters %s",
            vm_name, numa_node_params
        )
        return vm_api.add_numa_node_to_vm(
            vm_name, c.HOSTS[0], **numa_node_params
        )

    @classmethod
    def __update_vms(cls, vms_params):
        """
        Update number of vms to given parameters

        :param vms_params: parameters to update
        :type vms_params: dict
        :raises: VMException
        """
        for vm in cls.vms_to_update:
            logger.info(
                "Update vm %s, to parameters: %s", vm, vms_params
            )
            if not vm_api.updateVm(True, vm, **vms_params):
                raise errors.VMException("Failed to update vm %s" % vm)

    @classmethod
    def setup_class(cls):
        """
        Update vm to new parameters
        """
        super(UpdateVm, cls).setup_class()
        cls.new_vm_params[
            "cpu_cores"
        ] = cls.num_of_vm_numa_nodes * c.CORES_MULTIPLIER
        cls.__update_vms(cls.new_vm_params)

    @classmethod
    def teardown_class(cls):
        """
        Update vm to old parameters
        """
        vm_numa_nodes_index = [
            vm_numa_node.index for vm_numa_node in vm_api.get_vm_numa_nodes(
                c.VM_NAME[0]
            )
        ]
        logger.info("Remove all numa nodes from vm %s", c.VM_NAME[0])
        for numa_node_index in vm_numa_nodes_index:
            logger.info("Remove numa node with index %s", numa_node_index)
            if not vm_api.remove_numa_node_from_vm(
                c.VM_NAME[0], numa_node_index
            ):
                raise errors.VMException("Failed to remove numa node")
        cls.__update_vms(cls.old_vm_params)


# All negative cases not work via REST, no any validation
class TestNegativeUpdateVmWithNumaAndAutomaticMigration(UpdateVm):
    """
    Try to add numa node to vm with AutomaticMigration option
    """
    __test__ = True
    new_vm_params = {"placement_host": c.HOSTS[0]}
    bz = {
        "1211176": {"engine": None, "version": ["3.5.1"]}
    }

    @polarion("RHEVM3-9565")
    def test_add_numa_node(self):
        """
        Add numa node to vm with AutomaticMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                c.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class TestNegativeUpdateVmWithNumaAndManualMigration(UpdateVm):
    """
    Try to add numa node to vm with ManualMigration option
    """
    __test__ = True
    new_vm_params = {
        "placement_host": c.HOSTS[0],
        "placement_affinity": c.VM_USER_MIGRATABLE
    }
    bz = {
        '1211176': {'engine': None, 'version': ['3.5.1']}
    }

    @polarion("RHEVM3-9564")
    def test_add_numa_node(self):
        """
        Add numa node to vm with ManualMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                c.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class TestNegativeUpdateVmWithNumaAndAnyHostPlacement(UpdateVm):
    """
    Try to add numa node to vm with AnyHostInCluster option
    """
    __test__ = True
    new_vm_params = {"placement_affinity": c.VM_PINNED}

    @polarion("RHEVM3-9566")
    def test_add_numa_node(self):
        """
        Add numa node to vm with AutomaticMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                c.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class AddNumaNodes(UpdateVm):
    """
    Base class for tests cases that need to add numa nodes to vm
    """
    __test__ = False
    new_vm_params = {
        "placement_affinity": c.VM_PINNED,
        "placement_host": c.HOSTS[0],
    }
    numa_mode = c.INTERLEAVE_MODE
    add_nodes = True
    numa_params = None

    @classmethod
    def setup_class(cls):
        """
        Add numa nodes to vm
        """
        super(AddNumaNodes, cls).setup_class()
        cls.numa_params = cls._create_number_of_equals_numa_nodes(
            c.VM_NAME[0], cls.host_executor_1,
            cls.num_of_vm_numa_nodes
        )
        if cls.add_nodes:
            for numa_param in cls.numa_params:
                if not cls._add_numa_node(c.VM_NAME[0], numa_param):
                    raise errors.VMException("Failed to add numa node to vm")
        cls._update_vm_numa_mode(
            c.VM_NAME[0], c.ENGINE_NUMA_MODES[cls.numa_mode]
        )


class StartVms(AddNumaNodes):
    """
    Base class for tests that need to run vm
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Start vms
        """
        super(StartVms, cls).setup_class()
        vm_api.start_vms(cls.vms_to_update)

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        vm_api.stop_vms_safely(cls.vms_to_update)
        super(StartVms, cls).teardown_class()


###############################################################################
# Numa memory mode test cases #################################################
###############################################################################
class CheckNumaModes(StartVms):
    """
    Base class to check run vm under different numa modes
    """
    __test__ = False
    num_of_vm_numa_nodes = 2

    @classmethod
    def _check_pinning(cls, pinning_type, numa_mode):
        """
        Check if cpu or memory pinning of vm correct

        :param pinning_type: pinning type
        (CPU_PINNING_TYPE, MEMORY_PINNING_TYPE)
        :type pinning_type: str
        :param numa_mode: numa mode(STRICT_MODE, PREFER_MODE, INTERLEAVE_MODE)
        :type numa_mode: str
        :returns: return True, if pinning correct, otherwise False
        :rtype: bool
        """
        h_numa_nodes_params = cls._get_numa_parameters_from_resource(
            cls.host_executor_1
        )
        vm_pinning = cls._get_pining_of_vm_from_host(
            cls.host_executor_1, c.VM_NAME[0], pinning_type
        )
        if pinning_type == c.CPU_PINNING_TYPE:
            return cls.__check_if_cpu_pinning_correct(
                h_numa_nodes_params, vm_pinning
            )
        elif pinning_type == c.MEMORY_PINNING_TYPE:
            h_os_major_ver, h_os_minor_ver = cls._get_os_version(
                c.VDS_HOSTS[0]
            )
            correct_ver = h_os_major_ver == "7" and h_os_minor_ver >= "1"
            if numa_mode == c.STRICT_MODE and correct_ver:
                return cls.__check_if_memory_pinning_correct_strict(
                    h_numa_nodes_params, vm_pinning
                )
            else:
                return cls.__check_if_memory_pinning_correct(
                    h_numa_nodes_params, vm_pinning
                )
        return False

    @classmethod
    def __check_if_cpu_pinning_correct(cls, h_numa_nodes_params, vm_pinning):
        """
        Check if cpu pinning of vm correct

        :param h_numa_nodes_params: dictionary of numa parameters from host
        :type h_numa_nodes_params: dict
        :param vm_pinning: dictionary of vm cpu pinning values
        :type vm_pinning: dict
        :returns: return True, if cpu pinning correct, otherwise False
        :rtype: bool
        """
        for pinning in h_numa_nodes_params.values():
            with_pinning = sum(
                x == pinning[c.NUMA_NODE_CPUS] for x in vm_pinning.values()
            )
            if with_pinning != c.CORES_MULTIPLIER:
                return False
        return True

    @classmethod
    def __check_if_memory_pinning_correct_strict(
            cls, h_numa_nodes_params, vm_pinning
    ):
        """
        Check if memory pinning of vm under strict mode is correct

        :param h_numa_nodes_params: dictionary of numa parameters from host
        :type h_numa_nodes_params: dict
        :param vm_pinning: dictionary of vm cpu pinning values
        :type vm_pinning: dict
        :returns: return True, if memory pinning correct, otherwise False
        :rtype: bool
        """
        for pinning in h_numa_nodes_params.keys():
            with_pinning = sum(
                x == [pinning] for x in vm_pinning.values()
            )
            if with_pinning != c.CORES_MULTIPLIER:
                return False
        return True

    @classmethod
    def __check_if_memory_pinning_correct(
            cls, h_numa_nodes_params, vm_pinning
    ):
        """
        Check if memory pinning of vm under
        prefer and interleave mode is correct

        :param h_numa_nodes_params: dictionary of numa parameters from host
        :type h_numa_nodes_params: dict
        :param vm_pinning: dictionary of vm cpu pinning values
        :type vm_pinning: dict
        :returns: return True, if memory pinning correct, otherwise False
        :rtype: bool
        """
        for pinning in vm_pinning.values():
            if pinning != h_numa_nodes_params.keys():
                return False
        return True


class TestStrictNumaModeOnVM(CheckNumaModes):
    """
    Run vm with two numa nodes, with pinning under strict mode and
    check if pinning on host correct
    """
    __test__ = True
    numa_mode = c.STRICT_MODE

    @polarion("RHEVM3-9567")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        self.assertTrue(
            self._check_pinning(c.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @bz({"1173928": {"engine": None, "version": ["3.5"]}})
    @polarion("RHEVM3-12234")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        self.assertTrue(
            self._check_pinning(c.MEMORY_PINNING_TYPE, self.numa_mode),
            "Memory pinning not correct"
        )

    @polarion("RHEVM3-12235")
    def test_numa_memory_mode(self):
        """
        Check memory numa mode
        """
        self.assertEqual(
            self._get_numa_mode_from_vm_process(
                self.host_executor_1, c.VM_NAME[0]
            ),
            self.numa_mode,
            "Vm process numa mode not equal to %s" % self.numa_mode
        )


class TestPreferModeOnVm(CheckNumaModes):
    """
    Run vm with two numa nodes, with pinning under prefer mode and
    check if pinning on host correct
    """
    __test__ = True
    numa_mode = c.PREFER_MODE
    num_of_vm_numa_nodes = 1
    bz = {
        "1211270": {"engine": None, "version": ["3.5.1"]}
    }

    @polarion("RHEVM3-9568")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        self.assertTrue(
            self._check_pinning(c.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @polarion("RHEVM3-12236")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        self.assertTrue(
            self._check_pinning(c.MEMORY_PINNING_TYPE, self.numa_mode),
            "Memory pinning not correct"
        )

    @polarion("RHEVM3-12237")
    def test_numa_memory_mode(self):
        """
        Check memory numa mode
        """
        self.assertEqual(
            self._get_numa_mode_from_vm_process(
                self.host_executor_1, c.VM_NAME[0]
            ),
            self.numa_mode,
            "Vm process numa mode not equal to %s" % self.numa_mode
        )


class TestInterleaveModeOnVm(CheckNumaModes):
    """
    Run vm with two numa nodes, with pinning under interleave mode and
    check if pinning on host correct
    """
    __test__ = True

    @polarion("RHEVM3-9569")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        self.assertTrue(
            self._check_pinning(c.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @polarion("RHEVM3-12238")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        self.assertTrue(
            self._check_pinning(c.MEMORY_PINNING_TYPE, self.numa_mode),
            "Memory pinning not correct"
        )

    @polarion("RHEVM3-12239")
    def test_numa_memory_mode(self):
        """
        Check memory numa mode
        """
        self.assertEqual(
            self._get_numa_mode_from_vm_process(
                self.host_executor_1, c.VM_NAME[0]
            ),
            self.numa_mode,
            "Vm process numa mode not equal to %s" % self.numa_mode
        )

###############################################################################


class TestCpuPinningOverrideNumaPinning(StartVms):
    """
    Check that cpu pinning override numa pinning options(for cpu only)
    """
    __test__ = True
    num_of_vm_numa_nodes = 1

    @classmethod
    def setup_class(cls):
        """
        Update vm with cpu pinning
        """
        cls.new_vm_params["vcpu_pinning"] = [{"0": "0"}]
        super(TestCpuPinningOverrideNumaPinning, cls).setup_class()
        cls.new_vm_params.pop("vcpu_pinning")

    @polarion("RHEVM3-9570")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            self.host_executor_1, c.VM_NAME[0], c.CPU_PINNING_TYPE
        )
        with_pinning = sum(
            x == [0] for x in vm_pinning.values()
        )
        self.assertEqual(with_pinning, 1, "Cpu pinning not correct")


###############################################################################
# Validation tests for vm numa nodes ##########################################
###############################################################################
class BaseClassForVmNumaNodesValidations(AddNumaNodes):
    """
    Base class for all validations tests
    """
    __test__ = False
    numa_mode = c.INTERLEAVE_MODE
    num_of_vm_numa_nodes = 2
    new_numa_params = None
    vms_to_stop = None

    @classmethod
    def _update_numa_nodes(
            cls, vm_name, numa_node_index, new_numa_node_params
    ):
        """
        Add default numa node to given vm

        :param vm_name: vm name
        :type vm_name: str
        :param numa_node_index: numa node index to update
        :type numa_node_index: int
        :param new_numa_node_params: new parameters for numa node
        :type new_numa_node_params: dict
        :returns: True, if operation success, otherwise False
        :rtype: bool
        """
        logger.info(
            "Update numa node with index %s on vm %s, with parameters %s",
            vm_name, numa_node_index, new_numa_node_params
        )
        return vm_api.update_numa_node_on_vm(
            vm_name, c.HOSTS[0], numa_node_index, **new_numa_node_params
        )

    @classmethod
    def _start_vm_and_get_numa_params(cls, vm_name):
        """
        Start vm and get numa parameters

        :param vm_name: vm name
        :type vm_name: str
        :returns: vm numa parameters
        :rtype: dict
        """
        vm_numa_params = {}
        logger.info("Start vm %s", vm_name)
        if not vm_api.startVm(True, vm_name):
            logger.error("Failed to start vm %s", vm_name)
        else:
            vm_numa_params = cls._get_numa_parameters_from_vm(
                c.VM_NAME[0]
            )
        return vm_numa_params

    @classmethod
    def _check_if_vm_have_correct_number_of_numa_nodes(cls, vm_numa_params):
        """
        Check if vm have correct number of numa node

        :param vm_numa_params: vm numa parameters
        :type vm_numa_params: dict
        :returns: True, if vm have correct number of numa nodes,
        otherwise False
        :rtype: bool
        """
        logger.info(
            "Check if vm %s have %d numa nodes",
            c.VM_NAME[0], cls.num_of_vm_numa_nodes
        )
        return len(vm_numa_params.keys()) == cls.num_of_vm_numa_nodes

    @classmethod
    def _check_numa_nodes_values(cls, type_of_value, vm_numa_params):
        """
        Check numa nodes values

        :param type_of_value: type of value to check(cpu, memory)
        :type type_of_value: str
        :param vm_numa_params: vm numa nodes parameters
        :type vm_numa_params: dict
        :returns: True, if value correct, otherwise False
        :rtype: bool
        """
        for vm_numa_index, vm_numa_param in vm_numa_params.iteritems():
            exp_value = cls.new_numa_params[
                vm_numa_index
            ][c.VM_NUMA_PARAMS[type_of_value]]
            vm_value = vm_numa_param[type_of_value]
            logger.info(
                "Check if %s on vm numa node %d is approximately equal to %s",
                c.VM_NUMA_PARAMS[type_of_value], vm_numa_index, exp_value
            )
            if type_of_value == c.NUMA_NODE_MEMORY:
                if vm_value < exp_value - c.MEMORY_ERROR:
                    return False
            else:
                if exp_value != vm_value:
                    return False
        return True

    @classmethod
    def setup_class(cls):
        """
        Create dictionary of numa nodes
        """
        super(BaseClassForVmNumaNodesValidations, cls).setup_class()
        for numa_node_param in cls.numa_params:
            numa_node_index = numa_node_param["index"]
            if not cls._update_numa_nodes(
                c.VM_NAME[0], numa_node_index,
                cls.new_numa_params[numa_node_index]
            ):
                raise errors.VMException("Failed to update numa node of vm")

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        if cls.vms_to_stop:
            vm_api.stop_vms_safely(cls.vms_to_stop)
        super(BaseClassForVmNumaNodesValidations, cls).teardown_class()


class TestTotalVmMemoryEqualToNumaNodesMemory(
    BaseClassForVmNumaNodesValidations
):
    """
    Create two numa nodes on vm, that sum of numa nodes memory equal to
    vm memory and check that numa nodes appear under guest OS
    """
    __test__ = True
    new_numa_params = [{"memory": 754}, {"memory": 270}]
    vms_to_stop = [c.VM_NAME[0]]

    @polarion("RHEVM3-9571")
    def test_check_numa_node(self):
        """
        Run vm and check numa nodes on vm
        """
        vm_numa_params = self._start_vm_and_get_numa_params(c.VM_NAME[0])
        self.assertTrue(
            vm_numa_params,
            "Failed to get numa parameters from vm %s" % c.VM_NAME[0]
        )
        self.assertTrue(
            self._check_if_vm_have_correct_number_of_numa_nodes(
                vm_numa_params
            ),
            "Vm %s have incorrect number of numa nodes"
        )
        self.assertTrue(
            self._check_numa_nodes_values(
                c.NUMA_NODE_MEMORY, vm_numa_params
            ),
            "Vm %s numa node memory have incorrect value" % c.VM_NAME[0]
        )


class TestNegativeTotalVmMemoryEqualToNumaNodesMemory(
    BaseClassForVmNumaNodesValidations
):
    """
    Create two numa nodes on vm, that sum of numa nodes memory not equal to
    vm memory, start vm and check number of numa node on guest OS
    """
    __test__ = True
    new_numa_params = [{"memory": 100}, {"memory": 200}]
    vms_to_stop = [c.VM_NAME[0]]

    @polarion("RHEVM3-9572")
    def test_check_numa_node(self):
        """
        Run vm and check numa nodes on vm
        """
        logger.info("Start vm %s", c.VM_NAME[0])
        self.assertFalse(
            vm_api.startVm(True, c.VM_NAME[0], timeout=c.START_VM_TIMEOUT),
            "Success to start vm %s" % c.VM_NAME[0]
        )


class TestTotalVmCpusEqualToNumaNodesCpus(BaseClassForVmNumaNodesValidations):
    """
    Create two numa nodes on vm, that sum of numa nodes cpus equal to
    total number of vm cpus and check that numa nodes appear under guest OS
    """
    __test__ = True
    new_numa_params = [{"cores": [0]}, {"cores": [1, 2, 3]}]
    vms_to_stop = [c.VM_NAME[0]]

    @polarion("RHEVM3-9573")
    def test_check_numa_nodes(self):
        """
        Run vm and check numa nodes on vm
        """
        vm_numa_params = self._start_vm_and_get_numa_params(c.VM_NAME[0])
        self.assertTrue(
            vm_numa_params,
            "Failed to get numa parameters from vm %s" % c.VM_NAME[0]
        )
        self.assertTrue(
            self._check_if_vm_have_correct_number_of_numa_nodes(
                vm_numa_params
            ),
            "Vm %s have incorrect number of numa nodes"
        )
        self.assertTrue(
            self._check_numa_nodes_values(
                c.NUMA_NODE_CPUS, vm_numa_params
            ),
            "Vm %s numa node cpus have incorrect value" % c.VM_NAME[0]
        )


class TestTotalVmCpusNotEqualToNumaNodesCpus(
    BaseClassForVmNumaNodesValidations
):
    """
    Create two numa nodes on vm, that sum of numa nodes cpus not equal to
    total number of vm cpus and start vm
    """
    __test__ = True
    new_numa_params = [{"cores": [0, 4]}, {"cores": [1, 2, 3]}]
    vms_to_stop = [c.VM_NAME[0]]

    @polarion("RHEVM3-9574")
    def test_check_numa_node(self):
        """
        Run vm and check numa nodes on vm
        """
        vm_numa_params = self._start_vm_and_get_numa_params(c.VM_NAME[0])
        self.assertTrue(
            vm_numa_params,
            "Failed to get numa parameters from vm %s" % c.VM_NAME[0]
        )
        self.assertTrue(
            self._check_if_vm_have_correct_number_of_numa_nodes(
                vm_numa_params
            ),
            "Vm %s have incorrect number of numa nodes"
        )


class TestPinningOneVNUMAToTwoPNUMA(BaseClassForVmNumaNodesValidations):
    """
    Check pinning of one virtual numa to two physical numa's
    """
    __test__ = True
    num_of_vm_numa_nodes = 1
    vms_to_stop = [c.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Update virtual numa node pin list
        """
        h_numa_nodes_indexes = host_api.get_numa_nodes_indexes(c.HOSTS[0])
        if h_numa_nodes_indexes and len(h_numa_nodes_indexes) >= 2:
            cls.new_numa_params = [{"pin_list": h_numa_nodes_indexes[:2]}]
        else:
            raise errors.HostException(
                "Number of numa nodes on host %s less than two" %
                c.HOSTS[0]
            )
        super(TestPinningOneVNUMAToTwoPNUMA, cls).setup_class()
        logging.info("Start vm %s", c.VM_NAME[0])
        if not vm_api.startVm(True, c.VM_NAME[0], wait_for_ip=True):
            raise errors.VMException("Failed to run vm %s" % c.VM_NAME[0])

    @polarion("RHEVM3-9552")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            self.host_executor_1, c.VM_NAME[0], c.CPU_PINNING_TYPE
        )
        cores_list = []
        for numa_node_index in self.new_numa_params[0]["pin_list"]:
            h_numa_node_obj = host_api.get_numa_node_by_index(
                c.HOSTS[0], numa_node_index
            )
            cores_list.extend(host_api.get_numa_node_cpus(h_numa_node_obj))
        for cpu_pinning in vm_pinning.values():
            self.assertEqual(
                cpu_pinning.sort(), cores_list.sort(),
                "Cpu pinning not correct"
            )


class TestPinningTwoVNUMAToOnePNUMA(BaseClassForVmNumaNodesValidations):
    """
    Check pinning of two virtual numa to one physical numa's
    """
    __test__ = True
    num_of_vm_numa_nodes = 2
    vms_to_stop = [c.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Update virtual numa node pin list
        """
        h_numa_nodes_indexes = host_api.get_numa_nodes_indexes(c.HOSTS[0])
        if h_numa_nodes_indexes and len(h_numa_nodes_indexes) >= 1:
            cls.new_numa_params = [
                {"pin_list": h_numa_nodes_indexes[0]},
                {"pin_list": h_numa_nodes_indexes[0]}
            ]
        else:
            raise errors.HostException(
                "Number of numa nodes on host %s less than one" %
                c.HOSTS[0]
            )
        super(TestPinningTwoVNUMAToOnePNUMA, cls).setup_class()
        logging.info("Start vm %s", c.VM_NAME[0])
        if not vm_api.startVm(True, c.VM_NAME[0], wait_for_ip=True):
            raise errors.VMException("Failed to run vm %s" % c.VM_NAME[0])

    @polarion("RHEVM3-9555")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            self.host_executor_1, c.VM_NAME[0], c.CPU_PINNING_TYPE
        )
        h_numa_node_obj = host_api.get_numa_node_by_index(
            c.HOSTS[0], self.new_numa_params[0]["pin_list"]
        )
        cores_list = host_api.get_numa_node_cpus(h_numa_node_obj)
        for cpu_pinning in vm_pinning.values():
            self.assertEqual(
                cpu_pinning.sort(), cores_list.sort(),
                "Cpu pinning not correct"
            )


###############################################################################
# Validation tests for vm numa nodes pinning ##################################
###############################################################################
class BaseNumaNodePinningValidation(AddNumaNodes):
    """
    Base class for numa nodes pinning validation
    """
    __test__ = False
    negative = False
    add_nodes = False
    num_of_vm_numa_nodes = 1

    @classmethod
    def setup_class(cls):
        """
        Update vm memory
        """
        h_numa_nodes = host_api.get_numa_nodes_from_host(c.HOSTS[0])
        if len(h_numa_nodes) > 0:
            h_numa_node_mem = host_api.get_numa_node_memory(h_numa_nodes[0])
        else:
            raise errors.HostException(
                "Failed to get numa nodes from host %s" % c.HOSTS[0]
            )
        if cls.negative:
            v_numa_node_mem = h_numa_node_mem * c.MB + c.GB
        else:
            v_numa_node_mem = h_numa_node_mem * c.MB - c.GB
        cls.new_vm_params["memory"] = v_numa_node_mem
        cls.new_vm_params["memory_guaranteed"] = v_numa_node_mem
        super(BaseNumaNodePinningValidation, cls).setup_class()
        cls.new_vm_params.pop("memory")
        cls.new_vm_params.pop("memory_guaranteed")


class TestPinVNUMAWithLessMemoryThanOnPNUMAStrict(
    BaseNumaNodePinningValidation
):
    """
    Pin vnuma with memory less than pnuma memory under strict mode
    """
    __test__ = True
    numa_mode = c.STRICT_MODE

    @polarion("RHEVM3-9575")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertTrue(
            self._add_numa_node(c.VM_NAME[0], self.numa_params[0]),
            "Failed to add virtual node with pinning to vm %s" %
            c.VM_NAME[0]
        )


class TestNegativePinVNUMAWithLessMemoryThanOnPNUMAStrict(
    BaseNumaNodePinningValidation
):
    """
    Pin vnuma with memory greater than pnuma memory under strict mode
    """
    __test__ = True
    numa_mode = c.STRICT_MODE
    negative = True

    @polarion("RHEVM3-9576")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertFalse(
            self._add_numa_node(c.VM_NAME[0], self.numa_params[0]),
            "Success to add virtual node with pinning to vm %s" %
            c.VM_NAME[0]
        )


class TestPinVNUMAWithLessMemoryThanOnPNUMAInterleave(
    BaseNumaNodePinningValidation
):
    """
    Pin vnuma with memory greater than pnuma memory under interleave mode
    """
    __test__ = True
    numa_mode = c.INTERLEAVE_MODE
    negative = True

    @polarion("RHEVM3-9549")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertTrue(
            self._add_numa_node(c.VM_NAME[0], self.numa_params[0]),
            "Failed to add virtual node with pinning to vm %s" %
            c.VM_NAME[0]
        )


class TestHotplugCpuUnderNumaPinning(StartVms):
    """
    Run vm with numa pinning, hotplug cpu and check numa pinning
    """
    __test__ = True
    num_of_vm_numa_nodes = 2
    new_num_of_sockets = 2

    @polarion("RHEVM3-9556")
    def test_hotplug_cpu_and_check_numa_status(self):
        """
        Hotplug additional cpu to vm and check vm numa architecture
        """
        logging.info(
            "Update vm %s number of sockets to %d",
            c.VM_NAME[0], self.new_num_of_sockets
        )
        self.assertTrue(
            vm_api.updateVm(
                True, c.VM_NAME[0], cpu_socket=self.new_num_of_sockets
            ),
            "Failed to update vm %s" % c.VM_NAME[0]
        )
        logging.info("Receive numa parameters from vm %s", c.VM_NAME[0])
        vm_numa_params = self._get_numa_parameters_from_vm(c.VM_NAME[0])
        logger.info(
            "Vm %s numa parameters %s", c.VM_NAME[0], vm_numa_params
        )
        self.assertTrue(
            vm_numa_params,
            "Failed to receive numa parameters from vm %s" % c.VM_NAME[0]
        )
        expected_value = 6
        logging.info("Check number of cores for second numa node")
        self.assertEqual(
            len(vm_numa_params[1][c.NUMA_NODE_CPUS]), expected_value,
            "Number of cpus on second vm %s numa node not equal to %d" %
            (c.VM_NAME[0], expected_value)
        )
