"""
Base module for scheduler tests with memory load
"""
import logging

import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
import art.unittest_lib as libs
import config as conf
from rhevmtests.sla import helpers

logger = logging.getLogger(__name__)


@libs.attr(tier=2)
class BaseTestPolicyWithMemory(libs.SlaTest):
    """
    Base class for scheduler tests with memory load
    """
    load_cpu_d = None
    load_memory_d = None
    cluster_policy = None

    @classmethod
    def setup_class(cls):
        """
        Setup:
        1) Load hosts cpu if need
        2) Load hosts memory if need
        3) Change cluster policy
        """
        if cls.load_cpu_d:
            helpers.start_and_wait_for_cpu_load_on_resources(cls.load_cpu_d)
        if cls.load_memory_d:
            vm_host_d = dict(
                (vm_name, {"host": host_name, "wait_for_state": conf.VM_UP})
                for host_name, vm_name in cls.load_memory_d.iteritems()
            )
            ll_vms.run_vms_once(
                vms=cls.load_memory_d.values(), **vm_host_d
            )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=cls.cluster_policy.get("name"),
            properties=cls.cluster_policy.get("params")
        ):
            raise errors.ClusterException()

    @classmethod
    def teardown_class(cls):
        """
        Teardown:
        1) Update cluster policy to default
        2) Stop memory load on hosts
        3) Stop CPU load on hosts
        """
        ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.POLICY_NONE
        )
        if cls.load_memory_d:
            logger.info("Stop memory load on hosts")
            ll_vms.stop_vms_safely(vms_list=cls.load_memory_d.values())
        if cls.load_cpu_d:
            helpers.stop_load_on_resources(cls.load_cpu_d.values())


class StartVms(BaseTestPolicyWithMemory):
    """
    Base class for tests, that need start vms first
    """
    @classmethod
    def setup_class(cls):
        """
        Start one vm on each host
        """
        vm_host_d = dict(
            (vm_name, {"host": host_name})
            for vm_name, host_name in zip(conf.VM_NAME[:2], conf.HOSTS[:2])
        )
        ll_vms.run_vms_once(vms=conf.VM_NAME[:2], **vm_host_d)
        if not helpers.wait_for_active_vms_on_hosts(
            hosts=conf.HOSTS[:2], expected_num_of_vms=1
        ):
            raise errors.HostException()
        super(StartVms, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        ll_vms.stop_vms_safely(conf.VM_NAME[:2])
        super(StartVms, cls).teardown_class()


class StartAndMigrateVmBase(StartVms):
    """
    Base class for start and migrate vm test
    """
    update_vm_d = None

    @classmethod
    def setup_class(cls):
        """
        1) Update VM_NAME[0] memory to new value
        2) Start VM on HOSTS[2]
        3) Override load parameters
        """
        if cls.update_vm_d:
            for vm_name, vm_params in cls.update_vm_d.iteritems():
                logger.info(
                    "Update vm %s with parameters: %s", vm_name, vm_params
                )
                if not ll_vms.updateVm(positive=True, vm=vm_name, **vm_params):
                    raise errors.VMException(
                        "Failed to update vm %s" % vm_name
                    )
        logger.info("Start vm %s on host %s", conf.VM_NAME[2], conf.HOSTS[2])
        if not ll_vms.runVmOnce(
            positive=True,
            vm=conf.VM_NAME[2],
            host=conf.HOSTS[2],
            wait_for_state=conf.VM_UP
        ):
            raise errors.VMException("Failed to start vm %s" % conf.VM_NAME[2])
        cls.load_cpu_d = {
            conf.CPU_LOAD_50: {
                conf.RESOURCE: conf.VDS_HOSTS[:3],
                conf.HOST: conf.HOSTS[:3]
            }
        }
        super(StartAndMigrateVmBase, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        1) Stop VM on HOSTS[2]
        2) Update VM_NAME[0] to have default parameters
        """
        logger.info("Stop vm %s", conf.VM_NAME[2])
        if not ll_vms.stopVm(positive=True, vm=conf.VM_NAME[2]):
            logger.error("Failed to stop vm %s", conf.VM_NAME[2])
        super(StartAndMigrateVmBase, cls).teardown_class()
        if cls.update_vm_d:
            for vm_name in cls.update_vm_d.iterkeys():
                logger.info("Update vm %s with default parameters", vm_name)
                if not ll_vms.updateVm(
                    positive=True, vm=vm_name, **conf.DEFAULT_VM_PARAMETERS
                ):
                    logger.error("Failed to update vm %s", vm_name)
