"""
Testing memory HA reservation on Cluster, this feature should find out
if cluster is HA safe
Prerequisites: 1 DC, 2 hosts, 1 SD (NFS)
Tests covers:
    Warning on insufficient memory
    Setting system to HA safe
    multiple VMs
    host-maintenance
"""

import logging
from time import sleep
from art.test_handler.tools import polarion
from art.unittest_lib import SlaTest as TestCase, attr
import art.test_handler.exceptions as errors
from rhevmtests.sla.ha_reservation import config
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_sd
import rhevmtests.sla as sla


logger = logging.getLogger(__name__)

########################################################################
#                             Base Class                               #
########################################################################


def setup_module():
    """
    Prepare environment for  HA reservation test
    """
    config.GENERAL_VM_PARAMS['placement_host'] = config.HOSTS[0]
    config.SPECIFIC_VMS_PARAMS[
        config.VM_NAME[0]
    ]['placement_host'] = config.HOSTS[0]
    config.SPECIFIC_VMS_PARAMS[
        config.VM_NAME[1]
    ]['placement_host'] = config.HOSTS[0] if len(config.HOSTS) >= 2 else None

    logger.info(
        "Deactivate host %s on cluster %s", config.HOSTS[2],
        config.CLUSTER_NAME[0]
    )
    if not ll_hosts.deactivateHost(True, config.HOSTS[2]):
        raise errors.HostException(
            "Failed to deactivate host %s" % config.HOSTS[2]
        )
    if not ll_sd.waitForStorageDomainStatus(
        True, config.DC_NAME[0], config.STORAGE_NAME[0],
        config.SD_ACTIVE,
    ):
        raise errors.StorageDomainException(
            "Failed to activate Storage Domain %s"
            % config.STORAGE_NAME[0]
        )

    logger.info(
        "Update cluster %s memory over commitment to %d percent",
        config.CLUSTER_NAME[0], config.CLUSTER_OVERCOMMITMENT_NONE
    )
    if not ll_clusters.updateCluster(
        positive=True,
        cluster=config.CLUSTER_NAME[0],
        ha_reservation=True,
        mem_ovrcmt_prc=config.CLUSTER_OVERCOMMITMENT_NONE
    ):
        raise errors.ClusterException(
            "Failed to update cluster %s" % config.CLUSTER_NAME[0]
        )
    for vm_name, params in config.SPECIFIC_VMS_PARAMS.iteritems():
        logger.info("Update vm %s with parameters: %s", vm_name, params)
        if not ll_vms.updateVm(
            positive=True, vm=vm_name, **params
        ):
            raise errors.VMException(
                "Failed to update vm %s" % vm_name
            )


def teardown_module():
    """
    SLA teardown
    """
    logger.info("Teardown...")
    logger.info(
        "Update cluster %s memory over commitment to %d percent",
        config.CLUSTER_NAME[0], config.CLUSTER_OVERCOMMITMENT_DESKTOP
    )
    if not ll_clusters.updateCluster(
        positive=True,
        cluster=config.CLUSTER_NAME[0],
        ha_reservation=False,
        mem_ovrcmt_prc=config.CLUSTER_OVERCOMMITMENT_DESKTOP
    ):
        logger.error(
            "Failed to update cluster memory overcommitment %s",
            config.CLUSTER_NAME[0]
        )
    logger.info(
        "Activate host %s on cluster %s",
        config.HOSTS[2], config.CLUSTER_NAME[0]
    )
    if not ll_hosts.activateHost(True, config.HOSTS[2]):
        logger.error("Failed to activate host %s", config.HOSTS[0])
    sla.sla_cleanup()


@attr(tier=2)
class HAReservation(TestCase):
    """
    Base class for operations
    """
    __test__ = False

    @classmethod
    def setup_class(cls):
        """
        Enable HA reservation on cluster
        """
        logger.info(
            "Enable HA reservation on cluster %s", config.CLUSTER_NAME[0]
        )
        if not ll_clusters.updateCluster(
            positive=True, cluster=config.CLUSTER_NAME[0], ha_reservation=True
        ):
            raise errors.ClusterException(
                "Failed to update cluster %s" % config.CLUSTER_NAME[0]
            )

    @classmethod
    def teardown_class(cls):
        """
        Disable HA reservation on cluster
        """
        logger.info(
            "Disable HA reservation on cluster %s", config.CLUSTER_NAME[0]
        )
        if not ll_clusters.updateCluster(
            positive=True, cluster=config.CLUSTER_NAME[0], ha_reservation=False
        ):
            logger.error(
                "Failed to update cluster %s", config.CLUSTER_NAME[0]
            )

    def is_cluster_ha_safe(self):
        """
        Check if cluster is HA safe

        :returns: True, if cluster is HA safe, otherwise False
        :rtype: bool
        """
        engine_executor = config.ENGINE_HOST.executor()
        cmd = ['cp', config.ENGINE_LOG, config.TMP_LOG]
        logger.info(
            "Make backup of engine log to %s on resource %s",
            config.TMP_LOG, config.ENGINE_HOST
        )
        logger.info(
            "Run command '%s' on resource %s",
            " ".join(cmd), config.ENGINE_HOST
        )
        rc, out, err = engine_executor.run_cmd(cmd)
        self.assertTrue(
            not rc,
            "Failed to make backup of log; out: %s; err: %s" % (out, err)
        )
        logger.info(
            "Waiting %d seconds until engine will update log",
            config.RESERVATION_TIMEOUT
        )
        sleep(config.RESERVATION_TIMEOUT)
        logger.info("Run diff between new and old engine log")
        cmd = [
            'diff', config.ENGINE_LOG, config.TMP_LOG,
            '|', 'grep', 'reservation'
        ]
        logger.info(
            "Run command '%s' on resource %s",
            " ".join(cmd), config.ENGINE_HOST
        )
        rc, out, err = engine_executor.run_cmd(cmd)
        self.assertTrue(
            not rc,
            "Error: no event in engine.log, out: %s; err: %s" % (out, err)
        )

        fail_status = "fail to pass HA reservation check"
        status = not out.find(fail_status) > -1

        logger.info(
            "Remove backup log %s from resource %s",
            config.TMP_LOG, config.ENGINE_HOST
        )
        cmd = ['rm', config.TMP_LOG]
        logger.info(
            "Run command '%s' on resource %s",
            " ".join(cmd), config.ENGINE_HOST
        )
        rc, out, err = engine_executor.run_cmd(cmd)
        self.assertTrue(
            not rc,
            "Failed to remove backup of log; out: %s; err: %s" % (out, err)
        )

        return status

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
class Maintenance(HAReservation):
    """
    Moving host to maintenance should make cluster not HA safe
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and startHA VM
        """
        super(Maintenance, cls).setup_class()
        logger.info(
            "Update vm %s with parameters: %s",
            config.VM_NAME[2], config.GENERAL_VM_PARAMS
        )
        if not ll_vms.updateVm(
            positive=True, vm=config.VM_NAME[2], **config.GENERAL_VM_PARAMS
        ):
            raise errors.VMException(
                "Failed to update vm %s" % config.VM_NAME[2]
            )
        logger.info("Start vm %s", config.VM_NAME[2])
        if not ll_vms.startVm(
            True, config.VM_NAME[2], wait_for_status=config.VM_UP
        ):
            raise errors.VMException(
                "Failed to start VM %s" % config.VM_NAME[2]
            )
        logger.info("VM %s is running", config.VM_NAME[2])

    @polarion("RHEVM3-4995")
    def test_host_maintenance(self):
        """
        Check if cluster is HA safe
        Move host to maintenance
        Check if cluster is not HA safe
        """
        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertTrue(
            self.is_cluster_ha_safe(),
            "Cluster %s HA reservation check failed" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s passed HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

        logger.info("Deactivate host %s", config.HOSTS[1])
        self.assertTrue(
            ll_hosts.deactivateHost(True, config.HOSTS[1]),
            "Failed to deactivate host %s" % config.HOSTS[1]
        )
        logger.info("Host %s deactivated", config.HOSTS[1])

        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertFalse(
            self.is_cluster_ha_safe(),
            "Cluster %s is still HA safe" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s failed HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

    @polarion("RHEVM3-4992")
    def test_set_cluster_ha_safe(self):
        """
        Activate host
        Check if cluster is Ha safe
        """
        logger.info("Activate host %s", config.HOSTS[1])
        self.assertTrue(
            ll_hosts.activateHost(True, config.HOSTS[1]),
            "Failed to activate host %s" % config.HOSTS[1]
        )
        logger.info("Host %s activated", config.HOSTS[1])

        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertTrue(
            self.is_cluster_ha_safe(), "Cluster HA reservation check failed"
        )
        logger.info(
            "Cluster %s passed HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove VM
        """
        logger.info("Stop vm %s", config.VM_NAME[2])
        ll_vms.stop_vms_safely([config.VM_NAME[2]])
        logger.info(
            "Update vm %s with parameters: %s",
            config.VM_NAME[2], config.DEFAULT_VM_PARAMETERS
        )
        if not ll_vms.updateVm(
            positive=True, vm=config.VM_NAME[2], **config.DEFAULT_VM_PARAMETERS
        ):
            raise errors.VMException(
                "Failed to update vm %s" % config.VM_NAME[2]
            )
        super(Maintenance, cls).teardown_class()


class NotCompatibleHost(HAReservation):
    """
    Cluster failing HA reservation check based on
    insufficient resources
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Allocate memory on host
        Create testing VM
        """
        super(NotCompatibleHost, cls).setup_class()
        new_memory = hl_vms.calculate_memory_for_memory_filter(
            config.HOSTS[:2]
        )
        for vm_name, vm_memory, vm_host in zip(
                config.VM_NAME[:2], new_memory, config.HOSTS[:2]
        ):
            logger.info(
                "Update vm %s memory and guaranteed memory to %d",
                vm_name, vm_memory
            )
            if not ll_vms.updateVm(
                positive=True,
                vm=vm_name,
                memory=vm_memory,
                memory_guaranteed=vm_memory,
                placement_host=vm_host
            ):
                raise errors.VMException(
                    "Failed to update vm %s" % vm_name
                )
        logger.info(
            "Start vms %s", config.VM_NAME[:2]
        )
        if not ll_vms.startVms(
            vms=config.VM_NAME[:2], wait_for_status=config.VM_UP
        ):
            raise errors.VMException(
                "Failed to start vms %s" % config.VM_NAME[:2]
            )

    @polarion("RHEVM3-4987")
    def test_insufficient_resources(self):
        """
        2 host scenario, 1st host has memory allocated,
        2nd host has running HA VM
        """
        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertFalse(
            self.is_cluster_ha_safe(),
            "Cluster %s pass HA reservation check" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s did not pass HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

        logger.info("Stop vm %s", config.VM_NAME[0])
        self.assertTrue(
            ll_vms.stopVm(True, config.VM_NAME[0]),
            "Failed to stop vm %s" % config.VM_NAME[0]
        )
        logger.info(
            "Memory allocating VM %s removed from host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )

        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertTrue(
            self.is_cluster_ha_safe(),
            "Cluster %s HA reservation check failed" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s pass HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Stop VM_NAME[0] and VM_NAME[1] vms
        and update memory to 7 GB
        """
        logger.info(
            "Stop vms: %s", config.VM_NAME[:2]
        )
        ll_vms.stop_vms_safely(config.VM_NAME[:2])
        for vm_name in config.VM_NAME[:2]:
            logger.info(
                "Update vm %s parameters to default: %s",
                vm_name, config.DEFAULT_VM_PARAMETERS
            )
            if not ll_vms.updateVm(
                positive=True, vm=vm_name, **config.DEFAULT_VM_PARAMETERS
            ):
                logger.error(
                    "Failed to update vm %s", vm_name
                )
        super(NotCompatibleHost, cls).teardown_class()


class MultiVM(HAReservation):
    """
    Create 8 HA VMS in HA safe cluster and put one host to maintenance
    """
    __test__ = True
    vm_name = "VM_pool"

    @classmethod
    def setup_class(cls):
        """
        Create 8 VMs and run them on 1st host
        """
        super(MultiVM, cls).setup_class()
        param_dict = dict(config.GENERAL_VM_PARAMS)
        param_dict['memory'] = config.GB / 2
        param_dict['memory_guaranteed'] = config.GB / 2
        param_dict.update(config.INSTALL_VM_PARAMS)
        cls.vm_list = ["%s_%d" % (cls.vm_name, i) for i in range(8)]
        for vm_name in cls.vm_list:
            logger.info(
                "Create vm %s with parameters %s", vm_name, param_dict
            )
            if not ll_vms.createVm(
                positive=True,
                vmName=vm_name,
                vmDescription="VM allocating memory",
                **param_dict
            ):
                raise errors.VMException("Failed to create VM %s" % vm_name)
        logger.info("Start vms: %s", cls.vm_list)
        if not ll_vms.startVms(cls.vm_list):
            raise errors.VMException("Failed to start VMs")

    @polarion("RHEVM3-4994")
    def test_multi_vms(self):
        """
        Put host to maintenance and check cluster HA safe status
        """
        logger.info("Start vm %s", config.VM_NAME[1])
        self.assertTrue(
            ll_vms.startVm(
                positive=True,
                vm=config.VM_NAME[1],
                wait_for_status=config.VM_UP
            ),
            "Failed to start vm %s" % config.VM_NAME[1]
        )

        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertTrue(
            self.is_cluster_ha_safe(),
            "Cluster %s HA reservation check failed" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s pass HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

        logger.info("Deactivate host %s", config.HOSTS[0])
        self.assertTrue(ll_hosts.deactivateHost(True, config.HOSTS[0]))
        logger.info("Host %s moved to maintenance", config.HOSTS[0])

        logger.info("Wait until vms %s will have state UP", self.vm_list)
        for vm in self.vm_list:
            ll_vms.checkVmState(
                positive=True,
                vmName=vm,
                state=config.VM_UP,
                host=config.HOSTS[1]
            )
        logger.info(
            "Vms %s running on host %s - SUCCESS",
            self.vm_list, config.HOSTS[1]
        )

        logger.info("Check if cluster %s is HA safe", config.CLUSTER_NAME[0])
        self.assertFalse(
            self.is_cluster_ha_safe(),
            "Cluster %s pass HA reservation check" % config.CLUSTER_NAME[0]
        )
        logger.info(
            "Cluster %s did not pass HA reservation check - SUCCESS",
            config.CLUSTER_NAME[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Activate host and remove all created VMs
        """
        logger.info("Stop vm %s", config.VM_NAME[1])
        ll_vms.stop_vms_safely([config.VM_NAME[1]])
        logger.info("Safely remove vms %s", cls.vm_list)
        if not ll_vms.safely_remove_vms(cls.vm_list):
            logger.error("Failed to remove VMs")

        logger.info("Activate host %s", config.HOSTS[0])
        if not ll_hosts.activateHost(True, config.HOSTS[0]):
            logger.error("Failed to activate host %s" % config.HOSTS[0])
        logger.info("Host %s activated", config.HOSTS[0])
        super(MultiVM, cls).teardown_class()
