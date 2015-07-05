"""
Virt test
"""

import logging
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
logger = logging.getLogger(__name__)

########################################################################
#                            Functions                                 #
########################################################################


def run_once_with_boot_dev(vm_name, boot_device):
    """
    run once with chosen boot device

    :param vm_name: vm name
    :type vm_name: str
    :param boot_device: boot device
    :type boot_device: str
    :return: True, if succeeded to run once with boot device
    :rtype: bool
    """
    logger.info("Run once vm %s boot from %s", vm_name, boot_device)
    if not ll_vms.runVmOnce(
            True, config.VM_NAME[0],
            cdrom_image=config.CDROM_IMAGE_1,
            boot_dev=boot_device
    ):
        logger.info(
            "Failed to run once vm %s to boot from %s", vm_name, boot_device
        )
        return False
    boot_list = ll_vms.get_vm_boot_sequence(config.VM_NAME[0])
    if boot_list[0] == boot_device:
        logger.info("Succeeded to run once with %s", boot_device)
        return True

########################################################################
#                            classes                                   #
########################################################################


@attr(tier=0)
class TestRunVmOnce(TestCase):
    """
    Run once
    """
    __test__ = True

    @polarion("RHEVM3-9794")
    def test_boot_from_cd(self):
        """
        Run once VM boot from CD
        """
        self.assertTrue(
            run_once_with_boot_dev(
                config.VM_NAME[0], config.ENUMS['boot_sequence_cdrom']
            )
        )

    @polarion("RHEVM3-9808")
    def test_boot_from_network(self):
        """
        Run once VM boot from Network
        """
        self.assertTrue(
            run_once_with_boot_dev(
                config.VM_NAME[0], config.ENUMS['boot_sequence_network']
            )
        )

    @polarion("RHEVM3-9803")
    def test_start_in_pause_mode(self):
        """
        Run once VM in paused mode
        """
        logger.info("Run once vm %s in pause mode", config.VM_NAME[0])
        if not ll_vms.runVmOnce(True, config.VM_NAME[0], pause='true'):
            raise errors.VMException(
                "Failed to run VM %s in pause mode", config.VM_NAME[0]
            )
        logger.info("Check that vm started in pause mode")
        self.assertTrue(
            ll_vms.get_vm_state(config.VM_NAME[0]) ==
            config.VM_PAUSED
        )

    def test_run_once_vm_with_pause_and_change_cd(self):
        """
        Run once VM with "Start in paused" enables, and when VM in pause mode,
        change VM cd
        """
        logger.info(
            "Run once vm %s in pause mode with attached cd", config.VM_NAME[0]
        )
        if not ll_vms.runVmOnce(
                True, config.VM_NAME[0],
                cdrom_image=config.CDROM_IMAGE_1,
                pause='true'
        ):
            raise errors.VMException("Failed to run vm")
        logger.info("Check if vm state is paused")
        self.assertTrue(
            ll_vms.waitForVMState(
                config.VM_NAME[0],
                state=config.ENUMS['vm_state_paused']
            )
        )
        logger.info("Change vm %s cd", config.VM_NAME[0])
        self.assertTrue(
            ll_vms.changeCDWhileRunning(
                config.VM_NAME[0],
                config.CDROM_IMAGE_2
            )
        )

    @polarion("RHEVM3-9794")
    def test_run_once_vm_with_attached_floppy(self):
        """
        Run once VM with attached floppy
        """
        logger.info(
            "Run once vm %s with attached floppy %s",
            config.VM_NAME[0], config.FLOPPY_IMAGE
        )
        self.assertTrue(
            ll_vms.runVmOnce(
                True, config.VM_NAME[0],
                floppy_image=config.FLOPPY_IMAGE,
                pause='true'
            )
        )

    @polarion("RHEVM3-9794")
    def test_run_once_with_specific_host(self):
        """
        Run once VM on specific host
        """
        logger.info(
            "Run once vm %s on specific host %s",
            config.VM_NAME[0], config.HOSTS[0]
        )
        self.assertTrue(
            ll_vms.runVmOnce(True, config.VM_NAME[0], host=config.HOSTS[1])
        )

    @polarion("RHEVM3-9810")
    def test_run_once_with_administrator(self):
        """
        Run once VM as administrator
        """
        logger.info("Run once vm with administrator password and org name")
        self.assertTrue(
            ll_vms.runVmOnce(
                True, config.VM_NAME[0],
                host=config.HOSTS[0],
                user_name=config.VDC_ADMIN_USER,
                password=config.VDC_PASSWORD
            )
        )

    def tearDown(self):
        """
        stop VM if the Vm is Running
        """
        if (
            ll_vms.get_vm_state(config.VM_NAME[0]) !=
            config.ENUMS['vm_state_down']
        ):
            logger.info("Stop %s vm", config.VM_NAME[0])
            if not ll_vms.stopVm(True, config.VM_NAME[0]):
                raise errors.VMException(
                    "Failed to stop vm %s", config.VM_NAME[0]
                )


########################################################################


@attr(tier=0)
class TestRunVmOnceStatelessNoDisk(TestCase):
    """
    Test run once VM without disk in stateless mode
    """

    __test__ = True

    def setUp(self):
        """
        Remove cd from vm
        """
        logger.info("remove CD from VM %s", config.VM_NAME[0])
        disk = ll_vms.getVmDisks(config.VM_NAME[0])[0].name
        if not ll_vms.removeDisk(True, config.VM_NAME[0], disk):
            raise errors.VMException(
                "Failed tp remove CD from vm %s", config.VM_NAME[0])

    @polarion("RHEVM3-9781")
    def test_run_once_stateless_no_disk(self):
        """
        run once VM with no CD in statless mode
        """
        self.assertTrue(
            run_once_with_boot_dev(
                config.VM_NAME[0], config.ENUMS['boot_sequence_cdrom']
            )
        )

    def tearDown(self):
        """
        stop Vm if the vm is running and return add a disk
        """
        logger.info("Stop %s vm", config.VM_NAME[0])
        if not ll_vms.stopVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to stop vm %s", config.VM_NAME[0])
        if not ll_vms.addDisk(
                True, config.VM_NAME[0], 5 * config.GB,
                storagedomain=config.STORAGE_NAME[0]
        ):
            raise errors.VMException(
                "Can't return disk to vm %s", config.VM_NAME[0]
            )

########################################################################


@attr(tier=0)
class TestNegativeBootFromNetwork(TestCase):
    """
    Test run once, negative test that boot from network
    """

    __test__ = True

    def setUp(self):
        """
        remove nic from vm
        """
        logger.info("Remove nic from %s", config.VM_NAME[0])
        if not ll_vms.removeNic(True, config.VM_NAME[0], config.NIC_NAME[0]):
            raise errors.VMException(
                "Failed to remove %s from %s" %
                (config.NIC_NAME[0], config.VM_NAME[0])
            )

    @polarion("RHEVM3-9781")
    def test_negative_boot_from_network(self):
        """
        negative test - run once VM without nic to boot from network
        """

        self.assertFalse(
            run_once_with_boot_dev(
                config.VM_NAME[0], config.ENUMS['boot_sequence_network']
            )
        )

    def tearDown(self):
        """
        stop vm if the vm is running and add nic
        """
        logger.info("Stop %s vm", config.VM_NAME[0])
        if not ll_vms.stopVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to stop vm %s", config.VM_NAME[0])
        logger.info("add nic to %s", config.VM_NAME[0])
        if not ll_vms.addNic(
                True, config.VM_NAME[0],
                name=config.NIC_NAME[0], network=config.MGMT_BRIDGE
        ):
            raise errors.VMException(
                "Failed to add nic to %s" % config.VM_NAME[0]
            )
########################################################################


@attr(tier=0)
class TesNegativeHAStatlessVM(TestCase):
    """
    Test run once, negative test that run once HA VM in statless mode
    """

    __test__ = True
    bz = {'1231546': {'engine': ['sdk'], 'version': None}}

    def setUp(self):
        """
        change vm to HA
        """
        logger.info("change vm to HA")
        if not ll_vms.updateVm(True, config.VM_NAME[0], highly_available=True):
            raise errors.VMException("Failed to set VM as highly available")

    @polarion("RHEVM3-9783")
    def test_negative_HA_and_statless(self):
        """
        Nagtive test - run once HA VM in statless mode
        """

        self.assertFalse(
            ll_vms.runVmOnce(True, config.VM_NAME[0], stateless=True)
        )

    def tearDown(self):
        """
        stop vm and set vm as not highly available
        """
        logger.info("Stop %s vm", config.VM_NAME[0])
        if not ll_vms.stopVm(True, config.VM_NAME[0]):
            raise errors.VMException("Failed to stop vm %s", config.VM_NAME[0])
        if not ll_vms.updateVm(
                True, config.VM_NAME[0], highly_available=False
        ):
            raise errors.VMException(
                "Failed to set VM %s as not highly available"
                % config.VM_NAME[0]
            )
