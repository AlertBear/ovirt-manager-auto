"""
Base module for scheduler tests with memory load
"""
import logging
import config as conf
import art.unittest_lib as libs
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.sla as ll_sla
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters


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
            for load, hosts_d in cls.load_cpu_d.iteritems():
                if not ll_sla.start_cpu_loading_on_resources(
                    hosts_d[conf.RESOURCE], load
                ):
                    raise errors.HostException(
                        "Failed to load hosts %s CPU" % hosts_d[conf.RESOURCE]
                    )
                expected_load = min(
                    conf.DEFAULT_PS_PARAMS[conf.HIGH_UTILIZATION], load
                )
                for host in hosts_d[conf.HOST]:
                    if not ll_hosts.wait_for_host_cpu_load(
                        host_name=host, expected_min_load=expected_load
                    ):
                        raise errors.HostException(
                            "Host %s have cpu load below expected one" % host
                        )
        if cls.load_memory_d:
            vm_host_d = dict(
                (vm_name, {"host": host_name, "wait_for_state": conf.VM_UP})
                for host_name, vm_name in cls.load_memory_d.iteritems()
            )
            ll_vms.run_vms_once(
                vms=cls.load_memory_d.values(), **vm_host_d
            )
        cluster_policy_name = cls.cluster_policy.get("name")
        cluster_policy_params = cls.cluster_policy.get("params")
        logger.info(
            "Update cluster %s policy to %s with parameters: %s",
            conf.CLUSTER_NAME[0], cluster_policy_name, cluster_policy_params
        )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=cluster_policy_name,
            properties=cluster_policy_params
        ):
            raise errors.ClusterException(
                "Failed to update cluster %s" % conf.CLUSTER_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Teardown:
        1) Update cluster policy to default
        2) Stop memory load on hosts
        3) Stop CPU load on hosts
        """
        logger.info(
            "Update cluster %s policy to %s",
            conf.CLUSTER_NAME[0], conf.CLUSTER_POLICY_NONE
        )
        if not ll_clusters.updateCluster(
            positive=True,
            cluster=conf.CLUSTER_NAME[0],
            scheduling_policy=conf.CLUSTER_POLICY_NONE
        ):
            logger.error(
                "Failed to update cluster %s", conf.CLUSTER_NAME[0]
            )
        if cls.load_memory_d:
            logger.info("Stop memory load on hosts")
            ll_vms.stop_vms_safely(vms_list=cls.load_memory_d.values())
        if cls.load_cpu_d:
            for hosts_d in cls.load_cpu_d.itervalues():
                ll_sla.stop_cpu_loading_on_resources(hosts_d[conf.RESOURCE])
                for host in hosts_d[conf.HOST]:
                    if not ll_hosts.wait_for_host_cpu_load(
                        host_name=host, expected_max_load=5
                    ):
                        logger.error(
                            "Host %s have cpu load below expected one", host
                        )

    @staticmethod
    def _is_balancing_happen(host_name, expected_num_of_vms, negative=False):
        """
        Check if balance module work correct

        :param host_name: host name
        :type host_name: str
        :param expected_num_of_vms: expected number of active vms on host
        :type expected_num_of_vms: int
        :param negative: negative or positive expectation
        :type negative: bool
        :return: True, if host has expected number of vms, otherwise False
        :rtype: bool
        """
        log_msg = (
            conf.BALANCE_LOG_MSG_NEGATIVE
            if negative else conf.BALANCE_LOG_MSG_POSITIVE
        )
        logger.info(log_msg, host_name)
        return ll_hosts.wait_for_active_vms_on_host(
            host_name=host_name,
            num_of_vms=expected_num_of_vms,
            negative=negative,
            timeout=conf.MIGRATION_TIMEOUT
        )


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
