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
from rhevmtests.sla.ha_reservation import config

from art.unittest_lib import SlaTest as TestCase
from nose.plugins.attrib import attr
from art.test_handler.tools import tcms, bz  # pylint: disable=E0611

import art.test_handler.exceptions as errors

from art.rhevm_api.tests_lib.low_level import vms
from art.rhevm_api.tests_lib.low_level import hosts

from time import sleep
from art.unittest_lib.common import is_bz_state

logger = logging.getLogger(__name__)
TMP_LOG = '/tmp/HA_reservation.log'
RESERVATION_TIMEOUT = 300

########################################################################
#                             Base Class                               #
########################################################################


class HAReservation(TestCase):
    """
    Base class for operations
    """

    __test__ = False

    def check_ha(self, positive):
        """
        Check if cluster is HA safe return True/False or None in case of error

        :returns: True if cluster if HA safe otherwise False
        """
        engine_machine = hosts.get_linux_machine_obj(
            config.VDC_HOST, config.VDC_ROOT_USER,
            config.VDC_ROOT_PASSWORD, by_ip=False
        )
        rc, out = engine_machine.runCmd(
            ['cp', config.ENGINE_LOG, TMP_LOG]
        )

        self.assertTrue(rc, "Failed to make backup of log")

        logger.info("Waiting for %ds for log to update", RESERVATION_TIMEOUT)
        sleep(RESERVATION_TIMEOUT)

        rc, out = engine_machine.runCmd(
            ['diff', config.ENGINE_LOG, TMP_LOG,
             '|', 'grep', 'reservation']
        )
        self.assertTrue(rc, "Error: no event in engine.log, output: " + out)

        fail_status = "fail to pass HA reservation check"
        status = out.find(fail_status) > -1

        rc, out = engine_machine.runCmd(
            ['rm', TMP_LOG]
        )

        self.assertTrue(rc, "Failed to remove backup of log")

        if status:
            return not positive
        return positive

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
class Maintenance(HAReservation):
    """
    Moving host to maintenance should make cluster not HA safe
    """

    __test__ = True
    vm_name = "VM_test_maintenance"

    @classmethod
    def setup_class(cls):
        """
        Create and startHA VM
        """
        config.GENERAL_VM_PARAMS['memory'] = 4 * config.GB
        config.INSTALL_VM_PARAMS['installation'] = False
        config.GENERAL_VM_PARAMS.update(config.INSTALL_VM_PARAMS)
        logger.info("Create vm %s with parameters %s",
                    cls.vm_name, config.GENERAL_VM_PARAMS)
        if not vms.createVm(
            True, vmName=cls.vm_name,
            vmDescription="VM for testcase 339927",
            **config.GENERAL_VM_PARAMS
        ):
            raise errors.VMException("Failed to create VM")
        logger.info("VM %s successfully created", cls.vm_name)
        if not vms.startVm(
            True, vm=cls.vm_name, wait_for_status=config.ENUMS['vm_state_up']
        ):
            raise errors.VMException("Failed to start VM %s" % cls.vm_name)
        logger.info("VM %s is running", cls.vm_name)

    @tcms('12344', '339927')
    def test_host_maintenance(self):
        """
        Check if cluster is HA safe
        Move host to maintenance
        Check if cluster is not HA safe
        """
        self.assertTrue(self.check_ha(True),
                        "Cluster HA reservation check failed")
        logger.info("Cluster %s is HA safe - SUCCESS", config.CLUSTER_NAME[0])

        hosts.deactivateHost(True, config.HOSTS[1])
        logger.info("Host %s moved to maintenance", config.HOSTS[1])

        self.assertTrue(self.check_ha(False), "Cluster HA reservation check"
                                              " passed and shouldn't")
        logger.info("Cluster %s failed Ha reservation check - SUCCESS",
                    config.CLUSTER_NAME[0])

    @tcms('12344', '338501')
    def test_set_cluster_ha_safe(self):
        """
        Activate host
        Check if cluster is Ha safe
        """
        hosts.activateHost(True, config.HOSTS[1])
        logger.info("Host %s activated", config.HOSTS[1])

        self.assertTrue(self.check_ha(True),
                        "Cluster HA reservation check failed")
        logger.info("Cluster %s passed HA reservation check",
                    config.CLUSTER_NAME[0])

    @classmethod
    def teardown_class(cls):
        """
        Remove VM
        """
        if not vms.safely_remove_vms([cls.vm_name]):
            raise errors.VMException("Failed to remove VM %s" % cls.vm_name)
        logger.info("VM %s successfully removed", cls.vm_name)


@attr(tier=1)
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
        vms.startVms(
            [config.HA_RESERVATION_ALLOC, config.HA_RESERVATION_VM],
            wait_for_status=config.ENUMS['vm_state_up']
        )

    @tcms('12344', '336832')
    def test_insufficient_resources(self):
        """
        2 host scenario, 1st host has memory allocated,
        2nd host has running HA VM
        """
        if not self.check_ha(False):
            self.assertTrue(
                vms.migrateVm(True, config.HA_RESERVATION_VM),
                "Cluster HA reservation check passed and shouldn't"
            )
        else:
            logger.info(
                "Cluster %s did not pass Ha reservation check",
                config.CLUSTER_NAME[0]
            )

            self.assertTrue(
                vms.stopVm(True, config.HA_RESERVATION_ALLOC),
                "Failed to stop VM allocating memory"
            )
            logger.info(
                "Memory allocating VM %s removed from host %s",
                config.HA_RESERVATION_ALLOC, config.HOSTS[0]
            )

            self.assertTrue(
                self.check_ha(True),
                "Cluster HA reservation check failed"
            )
            logger.info(
                "Cluster %s passwd Ha reservation check",
                config.CLUSTER_NAME[0]
            )


@attr(tier=1)
class MultiVM(HAReservation):
    """
    Create 8 Ha Vms in HA safe cluster and make
    host fail (move to maintenance)
    """

    __test__ = True
    vm_name = "VM_pool"

    @classmethod
    def setup_class(cls):
        """
        Create 8 VMs and run them on 1st host
        """
        if is_bz_state('1107992'):
            config.GENERAL_VM_PARAMS['memory'] = config.GB / 2
            config.INSTALL_VM_PARAMS['installation'] = False
            config.GENERAL_VM_PARAMS.update(config.INSTALL_VM_PARAMS)
            cls.vm_list = ["%s_%d" % (cls.vm_name, i) for i in range(8)]
            for vm in cls.vm_list:
                logger.info("Create vm %s with parameters %s",
                            vm, config.GENERAL_VM_PARAMS)
                if not vms.createVm(
                    True, vmName=vm,
                    vmDescription="VM allocating memory",
                    **config.GENERAL_VM_PARAMS
                ):
                    raise errors.VMException("Failed to create VM %s" % vm)
            if not vms.startVms(cls.vm_list):
                raise errors.VMException("Failed to start VMs")
            logger.info(
                "VMs %s successfully created and all VMs running",
                cls.vm_list
            )

    @bz({'1107992': {'engine': None, 'version': None}})
    @tcms('12344', '339926')
    def test_multi_vms(self):
        """
        Make Host fail (move to maintenance)
        """
        self.assertTrue(
            self.check_ha(True),
            "Cluster HA reservation check failed"
        )
        self.assertTrue(hosts.deactivateHost(True, config.HOSTS[0]))
        logger.info("Host %s moved to maintenance", config.HOSTS[0])

        for vm in self.vm_list:
            vms.checkVmState(
                True, vm, config.ENUMS['vm_state_up'],
                host=config.HOSTS[1]
            )
        logger.info("All VMs running on host %s- SUCCESS", config.HOSTS[1])

        self.assertTrue(
            self.check_ha(False),
            "Cluster HA reservation check passed and shouldn't"
        )

    @classmethod
    def teardown_class(cls):
        """
        Activate host and remove all created VMs
        """
        logger.info("MultiVM teardown")
        if is_bz_state('1107992'):
            if not vms.safely_remove_vms(cls.vm_list):
                raise errors.VMException("Failed to remove VMs")
            logger.info("All VMs removed")

            if not hosts.activateHost(True, config.HOSTS[0]):
                raise errors.HostException(
                    "Failed to activate host %s" % config.HOSTS[0]
                )
            logger.info("Host %s activated", config.HOSTS[0])
