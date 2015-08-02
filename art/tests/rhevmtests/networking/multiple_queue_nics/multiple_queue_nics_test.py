"""
multiple_queue_nics
"""

import logging
from art.rhevm_api.tests_lib.high_level.vms import start_vm_on_specific_host
from art.rhevm_api.tests_lib.low_level.hosts import(
    get_host_ip_from_engine, get_host_name_from_engine
)
from art.rhevm_api.tests_lib.low_level.networks import updateVnicProfile
from art.rhevm_api.tests_lib.low_level.templates import(
    createTemplate, removeTemplate
)
from art.rhevm_api.tests_lib.low_level.vms import(
    stopVm, suspendVm, createVm, removeVm, waitForIP, migrateVm, startVm,
    get_vm_host
)
from art.rhevm_api.utils.test_utils import setPersistentNetwork
from art.test_handler.exceptions import NetworkException
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from rhevmtests.networking import config
from art.test_handler.tools import polarion  # pylint: disable=E0611
from rhevmtests.networking.multiple_queue_nics.helper import(
    check_queues_from_qemu
)


logger = logging.getLogger("Multiple_Queues_Nics_Cases")
HOST_NAME0 = None  # Fill in setup_module
HOST_NAME1 = None  # Fill in setup_module


def setup_module():
    """
    Get host names from engine
    """
    global HOST_NAME0
    global HOST_NAME1
    HOST_NAME0 = get_host_name_from_engine(config.VDS_HOSTS[0].ip)
    HOST_NAME1 = get_host_name_from_engine(config.VDS_HOSTS[1].ip)


@attr(extra_reqs={'rhel': 7})
class TestMultipleQueueNicsTearDown(TestCase):
    """
    Teardown class for MultipleQueueNics
    """

    @classmethod
    def teardown_class(cls):
        """
        Teardown class for MultipleQueueNics
        Remove queues from MGMT vNIC profile and stop the VM
        """
        logger.info(
            "Remove custom properties on %s", config.MGMT_BRIDGE
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0], custom_properties="clear"
        ):
            logger.error(
                "Failed to remove custom properties from %s",
                config.MGMT_BRIDGE
            )
        logger.info("Stop %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            logger.error("Failed to stop %s", config.VM_NAME[0])


@attr(tier=1)
class TestMultipleQueueNics01(TestMultipleQueueNicsTearDown):
    """
    Config queue on existing network
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Configure and update queue value on vNIC profile for exiting network
        (vNIC CustomProperties) and start VM
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])

    @polarion("RHEVM3-4309")
    def test_multiple_queue_nics(self):
        """
        Check that queue exist in qemu process, vdsm.log and engine.log
        """
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )


@attr(tier=1)
class TestMultipleQueueNics02(TestMultipleQueueNicsTearDown):
    """
    1) Verify that number of queues is not updated on running VM
    2) Verify that number of queues is updated on new VM boot
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Config and update queue value on vNIC profile for exiting network
        (vNIC CustomProperties) and start VM
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )

    @polarion("RHEVM3-4310")
    def test_multiple_queue_nics_update(self):
        """
        Make sure that number of queues does not change on running VM
        stop VM
        start VM
        make sure number of queues changed on new boot
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[1]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[1]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )

        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)

        logger.info("Check that qemu still has %s queues after properties "
                    "update", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj, num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected %s queues",
                config.NUM_QUEUES[0]
            )
        logger.info("Stopping VM %s", config.VM_NAME[0])
        stopVm(positive=True, vm=config.VM_NAME[0])

        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[1])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[1]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )


@attr(tier=1)
class TestMultipleQueueNics03(TestMultipleQueueNicsTearDown):
    """
    Check that queue survive VM hibernate
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Config and update queue value on vNIC profile for exiting network
        (vNIC CustomProperties) and start VM
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )

    @polarion("RHEVM3-4312")
    def test_multiple_queue_nics(self):
        """
        hibernate the VM and check the queue still configured on qemu
        """
        logger.info("Suspend %s", config.VM_NAME[0])
        if not suspendVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Failed to suspend %s" % config.VM_NAME[0])
        # TODO: take care of cases when resume of the VM fails (now it resta

        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )


@attr(tier=1)
class TestMultipleQueueNics04(TestMultipleQueueNicsTearDown):
    """
    Check queue exists for VM from template
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Config and update queue value on vNIC profile for existing network
        (vNIC CustomProperties)
        Create template from the VM
        Create VM from the template
        Start the new VM created from the template
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s", config.VM_NAME[0])
        if not startVm(positive=True, vm=config.VM_NAME[0], wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(get_vm_host(config.VM_NAME[0]))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )

        logger.info("Waiting for IP from %s", config.VM_NAME[0])
        rc, out = waitForIP(vm=config.VM_NAME[0], timeout=180, sleep=10)
        if not rc:
            raise NetworkException('Failed to get VM IP on mgmt network')

        ip = out['ip']
        logger.info("Running setPersistentNetwork on %s", config.VM_NAME[0])
        if not setPersistentNetwork(ip, config.VMS_LINUX_PW):
            raise NetworkException("Failed to seal %s" % config.VM_NAME[0])

        logger.info("Stop %s", config.VM_NAME[0])
        if not stopVm(positive=True, vm=config.VM_NAME[0]):
            raise NetworkException("Failed to stop %s" % config.VM_NAME[0])

        logger.info("Create queues_template from %s", config.VM_NAME[0])
        if not createTemplate(
            positive=True, vm=config.VM_NAME[0], name="queues_template"
        ):
            raise NetworkException(
                "Failed to create queues_template from %s" % config.VM_NAME[0]
            )

        logger.info("Create VM from queues_template")
        if not createVm(
            positive=True, vmName=config.VM_FROM_TEMPLATE,
            cluster=config.CLUSTER_NAME[0], vmDescription="from_template",
            template="queues_template"
        ):
            raise NetworkException("Failed to create VM from queues_template")

        logger.info("Start %s", config.VM_FROM_TEMPLATE)
        if not startVm(
                positive=True, vm=config.VM_FROM_TEMPLATE,
                wait_for_ip=True
        ):
            raise NetworkException(
                "Failed to start %s", config.VM_FROM_TEMPLATE
            )

    @polarion("RHEVM3-4313")
    def test_multiple_queue_nics(self):
        """
        Check that queue exist on VM from template
        """
        # get IP of the host where VM runs
        vm_host_ip = get_host_ip_from_engine(
            get_vm_host(config.VM_FROM_TEMPLATE))
        # find apropriate host object for the vm_host_ip in VDS_HOSTS
        host_obj = config.VDS_HOSTS[0].get(vm_host_ip)
        logger.info("Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_FROM_TEMPLATE,
            host_obj=host_obj,
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove VM
        Remove template
        """
        logger.info("Stop and remove %s", config.VM_FROM_TEMPLATE)
        if not removeVm(
                positive=True, vm=config.VM_FROM_TEMPLATE, stopVM="True",
                wait=True
        ):
            logger.error(
                "Failed to stop and remove %s", config.VM_FROM_TEMPLATE)
        logger.info("Remove queues_template")
        if not removeTemplate(positive=True, template="queues_template"):
            logger.error("Failed to remove queues_template")

        super(TestMultipleQueueNics04, cls).teardown_class()


@attr(tier=1)
class TestMultipleQueueNics05(TestMultipleQueueNicsTearDown):
    """
    Check that queues survive VM migration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Config and update queue value on vNIC profile for exiting network
        (vNIC CustomProperties)
        Start VM
        Check number of queues
        Migrate VM
        Check number of queues
        """
        logger.info(
            "Update custom properties on %s to %s", config.MGMT_BRIDGE,
            config.PROP_QUEUES[0]
        )
        if not updateVnicProfile(
            name=config.MGMT_BRIDGE, network=config.MGMT_BRIDGE,
            data_center=config.DC_NAME[0],
            custom_properties=config.PROP_QUEUES[0]
        ):
            raise NetworkException(
                "Failed to set custom properties on %s" % config.MGMT_BRIDGE
            )
        logger.info("Start %s", config.VM_NAME[0])
        if not start_vm_on_specific_host(
                vm=config.VM_NAME[0], host=HOST_NAME0, wait_for_ip=True):
            raise NetworkException("Failed to start %s" % config.VM_NAME[0])

        logger.info(
            "Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=config.VDS_HOSTS[0],
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )
        if not migrateVm(
                positive=True, vm=config.VM_NAME[0], host=HOST_NAME1
        ):
            raise NetworkException(
                "Failed to migrate %s from %s to %s" %
                (config.VM_NAME[0], HOST_NAME0, HOST_NAME1)
            )

    @polarion("RHEVM3-4311")
    def test_multiple_queue_nics(self):
        """
        Check number of queues after VM migration
        """
        logger.info(
            "Check that qemu has %s queues", config.NUM_QUEUES[0])
        if not check_queues_from_qemu(
            vm=config.VM_NAME[0],
            host_obj=config.VDS_HOSTS[1],
            num_queues=config.NUM_QUEUES[0]
        ):
            raise NetworkException(
                "qemu did not return the expected number of queues"
            )
