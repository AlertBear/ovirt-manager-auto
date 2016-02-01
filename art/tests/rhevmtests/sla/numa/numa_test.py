"""
Numa - Numa Test
Check creation of VNUMA on vm, run it on host with NUMA architecture and
pining of VNUMA to host NUMA
"""
import logging
import config as conf
import art.unittest_lib as u_libs
from art.unittest_lib import attr
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
import art.test_handler.exceptions as errors
import rhevmtests.networking.helper as network_helpers
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts

logger = logging.getLogger(__name__)


@attr(tier=2)
class BaseNumaClass(u_libs.SlaTest):
    """
    Base class for Numa Test
    """
    default_numa_node_params = {
        "index": 1, "memory": 1024, "cores": [0], "pin_list": [0]
    }

    @classmethod
    def _get_numa_parameters_from_resource(cls, vds_resource):
        """
        Get numa parameters from host

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :returns: dictionary of parameters({node_index: {cpus, memory}})
        :rtype: dict
        """
        param_dict = {}
        rc, out, _ = vds_resource.run_command(command=[conf.NUMACTL, "-H"])
        if rc:
            logger.error("Failed to get numa information from resource")
            return param_dict
        for line in out.splitlines():
            line = line.replace(":", "")
            line_arr = line.split()
            if line_arr[0] == conf.NUMA_NODE:
                if line_arr[1] == conf.NUMA_NODE_DISTANCE:
                    break
                node_name = int(line_arr[1])
                if node_name not in param_dict:
                    param_dict[node_name] = {}
                if line_arr[2] == conf.NUMA_NODE_CPUS:
                    param_dict[node_name][line_arr[2]] = [
                        int(value) for value in line_arr[3:]
                    ]
                else:
                    param_dict[node_name][line_arr[2]] = [int(line_arr[3])]
        return param_dict

    @classmethod
    def _get_numa_parameters_from_vm(cls, vm_name):
        """
        Install if needed numactl package on vm and get vm numa parameters

        :param vm_name: vm name
        :type vm_name: str
        :returns: dictionary of parameters({node_index: {cpus, memory}})
        :rtype: dict
        """
        params_dict = {}
        vm_resource = network_helpers.get_vm_resource(vm=vm_name)
        if not vm_resource:
            return params_dict
        logger.info(
            "Install %s package on host %s", conf.NUMACTL_PACKAGE, vm_resource
        )
        if not vm_resource.package_manager.install(conf.NUMACTL_PACKAGE):
            raise errors.HostException(
                "Failed to install package %s on host %s" %
                (conf.NUMACTL_PACKAGE, vm_resource)
            )

        return cls._get_numa_parameters_from_resource(vm_resource)

    @classmethod
    def _get_pining_of_vm_from_host(cls, vds_resource, vm_name, pinning_type):
        """
        Get information about cpu and memory pining of vm from host

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :param vm_name: vm name
        :type vm_name: str
        :param pinning_type: pinning type(cpu, memory)
        :type pinning_type: str
        :returns: dictionary with pinning information
        :rtype: dict
        """
        pinning_dict = {}
        logger.info("Get vm %s pid from host %s", vm_name, vds_resource.fqdn)
        vm_pid = vds_resource.get_vm_process_pid(vm_name)
        if not vm_pid:
            logger.error("Failed to get vm %s pid", vm_name)
            return pinning_dict
        cmd = [
            "cat", "/proc/%s/task/*/status" % vm_pid, "|", "grep", pinning_type
        ]
        rc, out, _ = vds_resource.run_command(command=cmd)
        if rc:
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
    def _get_numa_mode_from_vm_process(cls, vds_resource, vm_name):
        """
        Get information about numa mode for vm process

        :param vds_resource: vds resource
        :type vds_resource: VDS
        :param vm_name: vm name
        :type vm_name: str
        :returns: numa memory mode
        :rtype: str
        """
        numa_mode = ""
        logger.info("Get vm %s pid", vm_name)
        vm_pid = vds_resource.get_vm_process_pid(vm_name)
        if not vm_pid:
            logger.error("Failed to get vm %s pid", vm_name)
            return numa_mode
        cmd = ["tail", "-n", "1", "/proc/%s/numa_maps" % vm_pid]
        rc, out, _ = vds_resource.run_command(command=cmd)
        return numa_mode if rc else out.split()[1].split(":")[0]

    @classmethod
    def _create_number_of_equals_numa_nodes(
            cls, vm_name, num_of_numa_nodes
    ):
        """
        Create list of given number of numa nodes,
        with equal amount of memory and cpu

        :param vm_name: vm name
        :type vm_name: str
        :param num_of_numa_nodes: number of numa nodes to create
        :type num_of_numa_nodes: int
        :returns: list of numa nodes
        :rtype: list
        """
        numa_nodes_list = []
        h_numa_node_indexes = cls._get_numa_parameters_from_resource(
            conf.VDS_HOSTS[0]
        ).keys()
        v_numa_node_memory = ll_vms.get_vm_memory(
            vm_name
        ) / num_of_numa_nodes / conf.MB
        v_numa_node_cores = ll_vms.get_vm_cores(vm_name) / num_of_numa_nodes
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
        if not ll_vms.updateVm(True, vm_name, numa_mode=numa_mode):
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


@attr(tier=1)
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
            conf.VDS_HOSTS[0]
        )
        logger.info("Numa node parameters: %s", numa_nodes_params)
        for node_index, numa_node_param in numa_nodes_params.iteritems():
            numa_node_obj = ll_hosts.get_numa_node_by_index(
                conf.HOSTS[0], node_index
            )
            logger.info(
                "Check that engine receives correct "
                "memory value for node %s and host %s",
                node_index, conf.HOSTS[0]
            )
            memory_from_engine = ll_hosts.get_numa_node_memory(numa_node_obj)
            self.assertEqual(
                memory_from_engine, numa_node_param[conf.NUMA_NODE_MEMORY][0],
                "Memory numa node values not equal: "
                "from engine: %s and from numactl: %s" %
                (memory_from_engine, numa_node_param[conf.NUMA_NODE_MEMORY][0])
            )
            logger.info(
                "Check that engine receives correct "
                "cpu's value for node %s and host %s",
                node_index, conf.HOSTS[0]
            )
            cpus_from_engine = ll_hosts.get_numa_node_cpus(numa_node_obj)
            self.assertEqual(
                cpus_from_engine, numa_node_param[conf.NUMA_NODE_CPUS],
                "Cpu's numa node values not equal: "
                "from engine: %s and from numactl: %s" %
                (memory_from_engine, numa_node_param[conf.NUMA_NODE_CPUS])
            )


class UpdateVm(BaseNumaClass):
    """
    Base class for test cases that update vm
    """
    __test__ = False
    old_vm_params = {
        "memory": conf.GB,
        "memory_guaranteed": conf.GB,
        "cpu_cores": 1,
        "cpu_socket": 1,
        "placement_host": conf.VM_ANY_HOST,
        "placement_affinity": conf.VM_MIGRATABLE,
        "numa_mode": conf.ENGINE_NUMA_MODES[conf.INTERLEAVE_MODE],
        "vcpu_pinning": []
    }
    new_vm_params = None
    num_of_vm_numa_nodes = 1
    vms_to_update = conf.VM_NAME[:1]

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
        return ll_vms.add_numa_node_to_vm(
            vm_name, conf.HOSTS[0], **numa_node_params
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
            if not ll_vms.updateVm(True, vm, **vms_params):
                logger.error("Failed to update vm %s" % vm)

    @classmethod
    def setup_class(cls):
        """
        Update vm to new parameters
        """
        cls.new_vm_params[
            "cpu_cores"
        ] = cls.num_of_vm_numa_nodes * conf.CORES_MULTIPLIER
        cls.__update_vms(cls.new_vm_params)

    @classmethod
    def teardown_class(cls):
        """
        Update vm to old parameters
        """
        vm_numa_nodes_index = [
            vm_numa_node.index for vm_numa_node in ll_vms.get_vm_numa_nodes(
                conf.VM_NAME[0]
            )
        ]
        logger.info("Remove all numa nodes from vm %s", conf.VM_NAME[0])
        for numa_node_index in vm_numa_nodes_index:
            logger.info("Remove numa node with index %s", numa_node_index)
            if not ll_vms.remove_numa_node_from_vm(
                conf.VM_NAME[0], numa_node_index
            ):
                logger.error(
                    "Failed to remove numa node with index %s", numa_node_index
                )
        cls.__update_vms(cls.old_vm_params)


# All negative cases not work via REST, no any validation
class TestNegativeUpdateVmWithNumaAndAutomaticMigration(UpdateVm):
    """
    Try to add numa node to vm with AutomaticMigration option
    """
    __test__ = True
    bz = {
        "1211176": {"engine": None, "version": ["3.5.1"]}
    }

    @classmethod
    def setup_class(cls):
        cls.new_vm_params = {"placement_host": conf.HOSTS[0]}
        super(
            TestNegativeUpdateVmWithNumaAndAutomaticMigration, cls,
        ).setup_class()

    @polarion("RHEVM3-9565")
    def test_add_numa_node(self):
        """
        Add numa node to vm with AutomaticMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                conf.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class TestNegativeUpdateVmWithNumaAndManualMigration(UpdateVm):
    """
    Try to add numa node to vm with ManualMigration option
    """
    __test__ = True
    new_vm_params = {
        "placement_affinity": conf.VM_USER_MIGRATABLE
    }
    bz = {
        '1211176': {'engine': None, 'version': ['3.5.1']}
    }

    @classmethod
    def setup_class(cls):
        cls.new_vm_params["placement_host"] = conf.HOSTS[0]
        super(
            TestNegativeUpdateVmWithNumaAndManualMigration, cls,
        ).setup_class()

    @polarion("RHEVM3-9564")
    def test_add_numa_node(self):
        """
        Add numa node to vm with ManualMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                conf.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class TestNegativeUpdateVmWithNumaAndAnyHostPlacement(UpdateVm):
    """
    Try to add numa node to vm with AnyHostInCluster option
    """
    __test__ = True
    new_vm_params = {"placement_affinity": conf.VM_PINNED}

    @polarion("RHEVM3-9566")
    def test_add_numa_node(self):
        """
        Add numa node to vm with AutomaticMigration option
        """
        self.assertFalse(
            self._add_numa_node(
                conf.VM_NAME[0], self.default_numa_node_params
            ),
            "Success to add numa node to vm"
        )


class AddNumaNodes(UpdateVm):
    """
    Base class for tests cases that need to add numa nodes to vm
    """
    __test__ = False
    new_vm_params = {
        "placement_affinity": conf.VM_PINNED,
    }
    numa_mode = conf.INTERLEAVE_MODE
    add_nodes = True
    numa_params = None

    @classmethod
    def setup_class(cls):
        """
        Add numa nodes to vm
        """
        cls.new_vm_params["placement_host"] = conf.HOSTS[0]
        super(AddNumaNodes, cls).setup_class()
        cls.numa_params = cls._create_number_of_equals_numa_nodes(
            conf.VM_NAME[0], cls.num_of_vm_numa_nodes
        )
        if cls.add_nodes:
            for numa_param in cls.numa_params:
                if not cls._add_numa_node(conf.VM_NAME[0], numa_param):
                    raise errors.VMException("Failed to add numa node to vm")
        cls._update_vm_numa_mode(
            conf.VM_NAME[0], conf.ENGINE_NUMA_MODES[cls.numa_mode]
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
        ll_vms.start_vms(cls.vms_to_update)

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        ll_vms.stop_vms_safely(cls.vms_to_update)
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
    skip_test = False

    @classmethod
    def setup_class(cls):
        """
        Check host numa nodes and add skip flag
        in case if host numa node indexes 0 and 1
        """
        super(CheckNumaModes, cls).setup_class()
        h_numa_nodes_params = cls._get_numa_parameters_from_resource(
            conf.VDS_HOSTS[0]
        )
        if not h_numa_nodes_params or len(h_numa_nodes_params.keys()) < 2:
            raise errors.SkipTest(
                "Number of NUMA nodes on host %s less than 2" %
                conf.VDS_HOSTS[0].fqdn
            )
        else:
            for index, params in h_numa_nodes_params.items()[:2]:
                if params[conf.NUMA_NODE_MEMORY] <= 0:
                    cls.skip_test = True
                    logger.error(
                        "Numa node with index %d does not have enough memory "
                        "to run memory check test", index
                    )

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
            conf.VDS_HOSTS[0]
        )
        vm_pinning = cls._get_pining_of_vm_from_host(
            conf.VDS_HOSTS[0], conf.VM_NAME[0], pinning_type
        )
        if pinning_type == conf.CPU_PINNING_TYPE:
            return cls.__check_if_cpu_pinning_correct(
                h_numa_nodes_params, vm_pinning
            )
        elif pinning_type == conf.MEMORY_PINNING_TYPE:
            h_os_major_ver, h_os_minor_ver = cls._get_os_version(
                conf.VDS_HOSTS[0]
            )
            correct_ver = h_os_major_ver == "7" and h_os_minor_ver >= "1"
            if numa_mode == conf.STRICT_MODE and correct_ver:
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
        for pinning in h_numa_nodes_params.values()[:cls.num_of_vm_numa_nodes]:
            with_pinning = sum(
                x == pinning[conf.NUMA_NODE_CPUS] for x in vm_pinning.values()
            )
            if with_pinning != conf.CORES_MULTIPLIER:
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
        for pinning in h_numa_nodes_params.keys()[:cls.num_of_vm_numa_nodes]:
            with_pinning = sum(
                x == [pinning] for x in vm_pinning.values()
            )
            if with_pinning != conf.CORES_MULTIPLIER:
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


@attr(tier=1)
class TestStrictNumaModeOnVM(CheckNumaModes):
    """
    Run vm with two numa nodes, with pinning under strict mode and
    check if pinning on host correct
    """
    __test__ = True
    numa_mode = conf.STRICT_MODE

    @polarion("RHEVM3-9567")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        self.assertTrue(
            self._check_pinning(conf.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @bz({"1173928": {"engine": None, "version": ["3.5"]}})
    @polarion("RHEVM3-12234")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        self.assertTrue(
            self._check_pinning(conf.MEMORY_PINNING_TYPE, self.numa_mode),
            "Memory pinning not correct"
        )


@attr(tier=1)
class TestPreferModeOnVm(CheckNumaModes):
    """
    Run vm with one pinned numa node under prefer mode and
    check if pinning on host correct
    """
    __test__ = True
    numa_mode = conf.PREFER_MODE
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
            self._check_pinning(conf.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @polarion("RHEVM3-12236")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        if not self.skip_test:
            self.assertTrue(
                self._check_pinning(conf.MEMORY_PINNING_TYPE, self.numa_mode),
                "Memory pinning not correct"
            )

    @polarion("RHEVM3-12237")
    def test_numa_memory_mode(self):
        """
        Check memory numa mode
        """
        self.assertEqual(
            self._get_numa_mode_from_vm_process(
                conf.VDS_HOSTS[0], conf.VM_NAME[0]
            ),
            self.numa_mode,
            "Vm process numa mode not equal to %s" % self.numa_mode
        )


@attr(tier=1)
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
            self._check_pinning(conf.CPU_PINNING_TYPE, self.numa_mode),
            "CPU pinning not correct"
        )

    @polarion("RHEVM3-12238")
    def test_check_memory_pinning(self):
        """
        Check memory pinning
        """
        if not self.skip_test:
            self.assertTrue(
                self._check_pinning(conf.MEMORY_PINNING_TYPE, self.numa_mode),
                "Memory pinning not correct"
            )

    @polarion("RHEVM3-12239")
    def test_numa_memory_mode(self):
        """
        Check memory numa mode
        """
        self.assertEqual(
            self._get_numa_mode_from_vm_process(
                conf.VDS_HOSTS[0], conf.VM_NAME[0]
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
        cls.host_online_cpu = ll_sla.get_list_of_online_cpus_on_resource(
            conf.VDS_HOSTS[0]
        )[0]
        cls.new_vm_params["vcpu_pinning"] = [{"0": cls.host_online_cpu}]
        super(TestCpuPinningOverrideNumaPinning, cls).setup_class()
        cls.new_vm_params.pop("vcpu_pinning")

    @polarion("RHEVM3-9570")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            conf.VDS_HOSTS[0], conf.VM_NAME[0], conf.CPU_PINNING_TYPE
        )
        with_pinning = sum(
            x == [self.host_online_cpu] for x in vm_pinning.values()
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
    numa_mode = conf.INTERLEAVE_MODE
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
        return ll_vms.update_numa_node_on_vm(
            vm_name, conf.HOSTS[0], numa_node_index, **new_numa_node_params
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
        if not ll_vms.startVm(True, vm_name):
            logger.error("Failed to start vm %s", vm_name)
        else:
            vm_numa_params = cls._get_numa_parameters_from_vm(
                conf.VM_NAME[0]
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
            conf.VM_NAME[0], cls.num_of_vm_numa_nodes
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
            ][conf.VM_NUMA_PARAMS[type_of_value]]
            vm_value = vm_numa_param[type_of_value]
            logger.info(
                "Check if %s on vm numa node %d is approximately equal to %s",
                conf.VM_NUMA_PARAMS[type_of_value], vm_numa_index, exp_value
            )
            if type_of_value == conf.NUMA_NODE_MEMORY:
                if (
                    vm_value[0] < exp_value - conf.MEMORY_ERROR or
                    vm_value[0] > exp_value + conf.MEMORY_ERROR
                ):
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
                conf.VM_NAME[0], numa_node_index,
                cls.new_numa_params[numa_node_index]
            ):
                raise errors.VMException("Failed to update numa node of vm")

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        if cls.vms_to_stop:
            ll_vms.stop_vms_safely(cls.vms_to_stop)
        super(BaseClassForVmNumaNodesValidations, cls).teardown_class()


@attr(tier=1)
class TestTotalVmMemoryEqualToNumaNodesMemory(
    BaseClassForVmNumaNodesValidations
):
    """
    Create two numa nodes on vm, that sum of numa nodes memory equal to
    vm memory and check that numa nodes appear under guest OS
    """
    __test__ = True
    new_numa_params = [
        {"memory": 768}, {"memory": 256}
    ] if conf.PPC_ARCH else [
        {"memory": 754}, {"memory": 270}
    ]
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-9571")
    def test_check_numa_node(self):
        """
        Run vm and check numa nodes on vm
        """
        vm_numa_params = self._start_vm_and_get_numa_params(conf.VM_NAME[0])
        self.assertTrue(
            vm_numa_params,
            "Failed to get numa parameters from vm %s" % conf.VM_NAME[0]
        )
        self.assertTrue(
            self._check_if_vm_have_correct_number_of_numa_nodes(
                vm_numa_params
            ),
            "Vm %s have incorrect number of numa nodes"
        )
        self.assertTrue(
            self._check_numa_nodes_values(
                conf.NUMA_NODE_MEMORY, vm_numa_params
            ),
            "Vm %s numa node memory have incorrect value" % conf.VM_NAME[0]
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
    vms_to_stop = [conf.VM_NAME[0]]
    bz = {
        "1294462": {"engine": None, "version": ["3.6"]}
    }

    @polarion("RHEVM3-9572")
    def test_check_numa_node(self):
        """
        Start vm
        """
        logger.info("Start vm %s", conf.VM_NAME[0])
        self.assertTrue(
            ll_vms.startVm(
                True, conf.VM_NAME[0], timeout=conf.START_VM_TIMEOUT
            ),
            "Failed to start vm %s" % conf.VM_NAME[0]
        )


@attr(tier=1)
class TestTotalVmCpusEqualToNumaNodesCpus(BaseClassForVmNumaNodesValidations):
    """
    Create two numa nodes on vm, that sum of numa nodes cpus equal to
    total number of vm cpus and check that numa nodes appear under guest OS
    """
    __test__ = True
    new_numa_params = [{"cores": [0]}, {"cores": [1, 2, 3]}]
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-9573")
    def test_check_numa_nodes(self):
        """
        Run vm and check numa nodes on vm
        """
        vm_numa_params = self._start_vm_and_get_numa_params(conf.VM_NAME[0])
        self.assertTrue(
            vm_numa_params,
            "Failed to get numa parameters from vm %s" % conf.VM_NAME[0]
        )
        self.assertTrue(
            self._check_if_vm_have_correct_number_of_numa_nodes(
                vm_numa_params
            ),
            "Vm %s have incorrect number of numa nodes"
        )
        self.assertTrue(
            self._check_numa_nodes_values(
                conf.NUMA_NODE_CPUS, vm_numa_params
            ),
            "Vm %s numa node cpus have incorrect value" % conf.VM_NAME[0]
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
    vms_to_stop = [conf.VM_NAME[0]]

    @polarion("RHEVM3-9574")
    def test_check_numa_node(self):
        """
        Start vm
        """
        # W/A until we will have normal validation on VNUMA nodes creation
        logger.info("Try to start vm %s", conf.VM_NAME[0])
        if ll_vms.startVm(
            positive=True, vm=conf.VM_NAME[0], timeout=conf.START_VM_TIMEOUT
        ):
            logger.info("Get numa parameters from vm %s", conf.VM_NAME[0])
            vm_numa_params = self._get_numa_parameters_from_vm(
                conf.VM_NAME[0]
            )
            self.assertTrue(
                vm_numa_params,
                "Failed to get numa parameters from vm %s" % conf.VM_NAME[0]
            )
            logger.info(
                "Check that vm %s has different NUMA architecture",
                conf.VM_NAME[0]
            )
            self.assertNotEqual(
                vm_numa_params[0][conf.NUMA_NODE_CPUS],
                self.new_numa_params[0]["cores"],
                "Vm %s has correct NUMA architecture" % conf.VM_NAME[0]
            )


class TestPinningOneVNUMAToTwoPNUMA(BaseClassForVmNumaNodesValidations):
    """
    Check pinning of one virtual numa to two physical numa's
    """
    __test__ = True
    num_of_vm_numa_nodes = 1
    vms_to_stop = [conf.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Update virtual numa node pin list
        """
        h_numa_nodes_indexes = ll_hosts.get_numa_nodes_indexes(conf.HOSTS[0])
        if h_numa_nodes_indexes and len(h_numa_nodes_indexes) >= 2:
            cls.new_numa_params = [{"pin_list": h_numa_nodes_indexes[:2]}]
        else:
            raise errors.HostException(
                "Number of numa nodes on host %s less than two" %
                conf.HOSTS[0]
            )
        super(TestPinningOneVNUMAToTwoPNUMA, cls).setup_class()
        logging.info("Start vm %s", conf.VM_NAME[0])
        if not ll_vms.startVm(True, conf.VM_NAME[0], wait_for_ip=True):
            raise errors.VMException("Failed to run vm %s" % conf.VM_NAME[0])

    @polarion("RHEVM3-9552")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            conf.VDS_HOSTS[0], conf.VM_NAME[0], conf.CPU_PINNING_TYPE
        )
        cores_list = []
        for numa_node_index in self.new_numa_params[0]["pin_list"]:
            h_numa_node_obj = ll_hosts.get_numa_node_by_index(
                conf.HOSTS[0], numa_node_index
            )
            cores_list.extend(ll_hosts.get_numa_node_cpus(h_numa_node_obj))
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
    vms_to_stop = [conf.VM_NAME[0]]

    @classmethod
    def setup_class(cls):
        """
        Update virtual numa node pin list
        """
        h_numa_nodes_indexes = ll_hosts.get_numa_nodes_indexes(conf.HOSTS[0])
        if h_numa_nodes_indexes and len(h_numa_nodes_indexes) >= 1:
            cls.new_numa_params = [
                {"pin_list": [h_numa_nodes_indexes[0]]},
                {"pin_list": [h_numa_nodes_indexes[0]]}
            ]
        else:
            raise errors.HostException(
                "Number of numa nodes on host %s less than one" %
                conf.HOSTS[0]
            )
        super(TestPinningTwoVNUMAToOnePNUMA, cls).setup_class()
        logging.info("Start vm %s", conf.VM_NAME[0])
        if not ll_vms.startVm(True, conf.VM_NAME[0], wait_for_ip=True):
            raise errors.VMException("Failed to run vm %s" % conf.VM_NAME[0])

    @polarion("RHEVM3-9555")
    def test_check_cpu_pinning(self):
        """
        Check cpu pinning
        """
        vm_pinning = self._get_pining_of_vm_from_host(
            conf.VDS_HOSTS[0], conf.VM_NAME[0], conf.CPU_PINNING_TYPE
        )
        h_numa_node_obj = ll_hosts.get_numa_node_by_index(
            conf.HOSTS[0], self.new_numa_params[0]["pin_list"][0]
        )
        cores_list = ll_hosts.get_numa_node_cpus(h_numa_node_obj)
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
        h_numa_nodes = ll_hosts.get_numa_nodes_from_host(conf.HOSTS[0])
        if len(h_numa_nodes) > 0:
            h_numa_node_mem = ll_hosts.get_numa_node_memory(h_numa_nodes[0])
        else:
            raise errors.HostException(
                "Failed to get numa nodes from host %s" % conf.HOSTS[0]
            )
        if cls.negative:
            v_numa_node_mem = h_numa_node_mem * conf.MB + conf.GB
        else:
            v_numa_node_mem = h_numa_node_mem * conf.MB - conf.GB
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
    numa_mode = conf.STRICT_MODE

    @polarion("RHEVM3-9575")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertTrue(
            self._add_numa_node(conf.VM_NAME[0], self.numa_params[0]),
            "Failed to add virtual node with pinning to vm %s" %
            conf.VM_NAME[0]
        )


class TestNegativePinVNUMAWithLessMemoryThanOnPNUMAStrict(
    BaseNumaNodePinningValidation
):
    """
    Pin vnuma with memory greater than pnuma memory under strict mode
    """
    __test__ = True
    numa_mode = conf.STRICT_MODE
    negative = True

    @polarion("RHEVM3-9576")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertFalse(
            self._add_numa_node(conf.VM_NAME[0], self.numa_params[0]),
            "Success to add virtual node with pinning to vm %s" %
            conf.VM_NAME[0]
        )


class TestPinVNUMAWithLessMemoryThanOnPNUMAInterleave(
    BaseNumaNodePinningValidation
):
    """
    Pin vnuma with memory greater than pnuma memory under interleave mode
    """
    __test__ = True
    numa_mode = conf.INTERLEAVE_MODE
    negative = True

    @polarion("RHEVM3-9549")
    def test_pin_virtual_numa_node(self):
        """
        Try to pin virtual numa node to physical numa node
        """
        self.assertTrue(
            self._add_numa_node(conf.VM_NAME[0], self.numa_params[0]),
            "Failed to add virtual node with pinning to vm %s" %
            conf.VM_NAME[0]
        )


@u_libs.common.skip_class_if(conf.PPC_ARCH, conf.PPC_SKIP_MESSAGE)
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
            conf.VM_NAME[0], self.new_num_of_sockets
        )
        self.assertTrue(
            ll_vms.updateVm(
                True, conf.VM_NAME[0], cpu_socket=self.new_num_of_sockets
            ),
            "Failed to update vm %s" % conf.VM_NAME[0]
        )
        logging.info("Receive numa parameters from vm %s", conf.VM_NAME[0])
        vm_numa_params = self._get_numa_parameters_from_vm(conf.VM_NAME[0])
        logger.info(
            "Vm %s numa parameters %s", conf.VM_NAME[0], vm_numa_params
        )
        self.assertTrue(
            vm_numa_params,
            "Failed to receive numa parameters from vm %s" % conf.VM_NAME[0]
        )
        expected_amount_of_cpus = 8
        logging.info(
            "Check total number of cpus under NUMA stats on vm %s",
            conf.VM_NAME[0]
        )
        real_amount_of_cpus = sum(
            len(params[conf.NUMA_NODE_CPUS])
            for params in vm_numa_params.itervalues()
        )
        self.assertEqual(
            real_amount_of_cpus, expected_amount_of_cpus,
            "Total number of cpus under NUMA stats on vm %s "
            "does not equal to %d" %
            (conf.VM_NAME[0], expected_amount_of_cpus)
        )
