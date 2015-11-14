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
                for host in hosts_d[conf.HOST]:
                    if not ll_hosts.wait_for_host_cpu_load(
                        host_name=host, expected_min_load=load - 5
                    ):
                        raise errors.HostException(
                            "Host %s have cpu load below expected one" % host
                        )
        if cls.load_memory_d:
            for host, load_vm in cls.load_memory_d.iteritems():
                logger.info("Start vm %s on host %s", load_vm, host)
                if not ll_vms.runVmOnce(positive=True, vm=load_vm, host=host):
                    raise errors.VMException("Failed to start vm %s" % load_vm)
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
            try:
                ll_vms.stop_vms_safely(vms_list=cls.load_memory_d.values())
            except errors.VMException as e:
                logger.error(e.message)
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


class StartVmsClass(BaseTestPolicyWithMemory):
    """
    Base class for tests, that need start vms first
    """

    @classmethod
    def setup_class(cls):
        """
        Start one vm on each host
        """
        for vm_name, host_name in zip(conf.VM_NAME[:2], conf.HOSTS[:2]):
            logger.info("Start vm %s on host %s", vm_name, host_name)
            if not ll_vms.runVmOnce(positive=True, vm=vm_name, host=host_name):
                raise errors.VMException("Failed to start vm %s" % vm_name)
        super(StartVmsClass, cls).setup_class()

    @classmethod
    def teardown_class(cls):
        """
        Stop vms
        """
        try:
            ll_vms.stop_vms_safely(conf.VM_NAME[:2])
        except errors.VMException as e:
            logger.error(e.message)
        super(StartVmsClass, cls).teardown_class()
