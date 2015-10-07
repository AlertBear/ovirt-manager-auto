"""
Virt test
"""

import logging
from art.unittest_lib import VirtTest as TestCase
from art.test_handler.tools import polarion, bz  # pylint: disable=E0611
from art.unittest_lib import attr
from rhevmtests.virt import config
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.test_handler.exceptions as errors
logger = logging.getLogger(__name__)

########################################################################
#                            Functions                                 #
########################################################################


def run_once_with_boot_dev(boot_device):
    """
    run once with chosen boot device

    :param boot_device: boot device
    :type boot_device: str
    :return: True, if succeeded to run once with boot device
    :rtype: bool
    """
    logger.info("Run once vm %s boot from %s", config.VM_RUN_ONCE, boot_device)
    if not ll_vms.runVmOnce(
            True, config.VM_RUN_ONCE,
            cdrom_image=config.CDROM_IMAGE_1,
            boot_dev=boot_device
    ):
        logger.info(
            "Failed to run once vm %s to boot from %s",
            config.VM_RUN_ONCE, boot_device
        )
        return False
    boot_list = ll_vms.get_vm_boot_sequence(config.VM_RUN_ONCE)
    if boot_list[0] == boot_device:
        logger.info("Succeeded to run once with %s", boot_device)
        return True

########################################################################
#                            classes                                   #
########################################################################


@attr(tier=1)
class TestRunVmOnce(TestCase):
    """
    Run once
    """
    __test__ = True

    @polarion("RHEVM3-9809")
    def test_boot_from_cd(self):
        """
        Run once VM boot from CD
        """
        self.assertTrue(
            run_once_with_boot_dev(config.ENUMS['boot_sequence_cdrom'])
        )

    @polarion("RHEVM3-9808")
    def test_boot_from_network(self):
        """
        Run once VM boot from Network
        """
        self.assertTrue(
            run_once_with_boot_dev(config.ENUMS['boot_sequence_network'])
        )

    @polarion("RHEVM3-9803")
    def test_start_in_pause_mode(self):
        """
        Run once VM in paused mode
        """
        logger.info("Run once vm %s in pause mode", config.VM_RUN_ONCE)
        if not ll_vms.runVmOnce(True, config.VM_RUN_ONCE, pause='true'):
            raise errors.VMException(
                "Failed to run VM %s in pause mode", config.VM_RUN_ONCE
            )
        logger.info("Check that vm started in pause mode")
        self.assertTrue(
            ll_vms.get_vm_state(config.VM_RUN_ONCE) ==
            config.VM_PAUSED
        )

    @polarion("RHEVM3-12353")
    def test_run_once_vm_with_pause_and_change_cd(self):
        """
        Run once VM with "Start in paused" enables, and when VM in pause mode,
        change VM cd
        """
        logger.info(
            "Run once vm %s in pause mode with attached cd", config.VM_RUN_ONCE
        )
        if not ll_vms.runVmOnce(
                True, config.VM_RUN_ONCE,
                cdrom_image=config.CDROM_IMAGE_1,
                pause='true'
        ):
            raise errors.VMException("Failed to run vm")
        logger.info("Check if vm state is paused")
        self.assertTrue(
            ll_vms.waitForVMState(
                config.VM_RUN_ONCE,
                state=config.ENUMS['vm_state_paused']
            )
        )
        logger.info("Change vm %s cd", config.VM_RUN_ONCE)
        self.assertTrue(
            ll_vms.changeCDWhileRunning(
                config.VM_RUN_ONCE,
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
            config.VM_RUN_ONCE, config.FLOPPY_IMAGE
        )
        self.assertTrue(
            ll_vms.runVmOnce(
                True, config.VM_RUN_ONCE,
                floppy_image=config.FLOPPY_IMAGE,
                pause='true'
            )
        )

    @polarion("RHEVM3-9800")
    def test_run_once_with_specific_host(self):
        """
        Run once VM on specific host
        """
        logger.info(
            "Run once vm %s on specific host %s",
            config.VM_RUN_ONCE, config.HOSTS[0]
        )
        self.assertTrue(
            ll_vms.runVmOnce(True, config.VM_RUN_ONCE, host=config.HOSTS[1])
        )

    @polarion("RHEVM3-9810")
    def test_run_once_with_administrator(self):
        """
        Run once VM as administrator
        """
        logger.info("Run once vm with administrator password and org name")
        self.assertTrue(
            ll_vms.runVmOnce(
                True, config.VM_RUN_ONCE,
                host=config.HOSTS[0],
                user_name=config.VDC_ADMIN_USER,
                password=config.VDC_PASSWORD
            )
        )

    @bz({'1117783': {'engine': None, 'version': None}})
    @polarion("RHEVM3-12352")
    def test_run_once_vm_with_specific_domain(self):
        """
        Run once vm with specific domain
        """
        logger.info(
            "Run once vm %s with domain %s",
            self.vm_name, config.VDC_ADMIN_DOMAIN
        )
        if not ll_vms.runVmOnce(
                True, self.vm_name,
                domainName=config.VDC_ADMIN_DOMAIN,
                user_name=config.VDC_ADMIN_USER,
                password=config.VDC_PASSWORD
        ):
            raise errors.VMException("Failed to run vm")
        vm_obj = ll_vms.get_vm_obj(self.vm_name)
        logger.info("Check if vm domain is correct")
        self.assertTrue(vm_obj.get_domain() == config.VDC_ADMIN_DOMAIN)

    def tearDown(self):
        """
        stop VM if the Vm is Running
        """
        if (
            ll_vms.get_vm_state(config.VM_RUN_ONCE) !=
            config.ENUMS['vm_state_down']
        ):
            logger.info("Stop %s vm", config.VM_RUN_ONCE)
            if not ll_vms.stopVm(True, config.VM_RUN_ONCE):
                raise errors.VMException(
                    "Failed to stop vm %s", config.VM_RUN_ONCE
                )


########################################################################


@attr(tier=1)
class TestRunVmOnceStatelessNoDisk(TestCase):
    """
    Test run once VM without disk in stateless mode
    """

    __test__ = True

    def setUp(self):
        """
        remove disk from VM and set VM as stateless
        """

        logger.info("set VM as stateless")
        if not ll_vms.updateVm(True, config.VM_RUN_ONCE, stateless=True):
            raise errors.VMException(
                "Failed to update VM %s to be stateless" % config.VM_RUN_ONCE
            )
        logger.info("remove disk from VM %s", config.VM_RUN_ONCE)
        disk = ll_vms.getVmDisks(config.VM_RUN_ONCE)[0].name
        if not ll_vms.removeDisk(True, config.VM_RUN_ONCE, disk):
            raise errors.VMException(
                "Failed tp remove CD from vm %s", config.VM_RUN_ONCE
            )

    @polarion("RHEVM3-9781")
    def test_run_once_stateless_no_disk(self):
        """
        run once VM without disk in stateless mode
        """
        logger.info("run once VM %s without disk", config.VM_RUN_ONCE)
        self.assertTrue(
            run_once_with_boot_dev(config.ENUMS['boot_sequence_cdrom'])
        )

    def tearDown(self):
        """
        stop Vm if the vm is running and add Disk
        """
        logger.info("Stop %s VM", config.VM_RUN_ONCE)
        if not ll_vms.stopVm(True, config.VM_RUN_ONCE):
            raise errors.VMException(
                "Failed to stop vm %s", config.VM_RUN_ONCE
            )
        logger.info("add disk to %s VM", config.VM_RUN_ONCE)
        if not ll_vms.addDisk(
            True, config.VM_RUN_ONCE, 2 * config.GB,
            storagedomain=config.STORAGE_NAME[0]
        ):
            raise errors.VMException(
                "Can't return disk to vm %s", config.VM_RUN_ONCE
            )
        if not ll_vms.updateVm(True, config.VM_RUN_ONCE, stateless=False):
            raise errors.VMException(
                "Failed to set VM %s as stateless", config.VM_RUN_ONCE
            )

########################################################################


@attr(tier=1)
class TestNegativeBootFromNetwork(TestCase):
    """
    Test run once, negative test that boot from network
    """

    __test__ = True

    def setUp(self):
        """
        remove nic from vm
        """
        logger.info("Remove nic from %s", config.VM_RUN_ONCE)
        if not ll_vms.removeNic(True, config.VM_RUN_ONCE, config.NIC_NAME[0]):
            raise errors.VMException(
                "Failed to remove %s from %s" %
                (config.NIC_NAME[0], config.VM_RUN_ONCE)
            )

    @polarion("RHEVM3-9805")
    def test_negative_boot_from_network(self):
        """
        negative test - run once VM without nic to boot from network
        """
        self.assertFalse(
            run_once_with_boot_dev(config.ENUMS['boot_sequence_network'])
        )

    def tearDown(self):
        """
        stop vm if the vm is running and add nic
        """
        logger.info("Stop %s vm", config.VM_RUN_ONCE)
        if not ll_vms.stopVm(True, config.VM_RUN_ONCE):
            raise errors.VMException(
                "Failed to stop vm %s", config.VM_RUN_ONCE
            )
        logger.info("add nic to %s", config.VM_RUN_ONCE)
        if not ll_vms.addNic(
                True, config.VM_RUN_ONCE,
                name=config.NIC_NAME[0], network=config.MGMT_BRIDGE
        ):
            raise errors.VMException(
                "Failed to add nic to %s" % config.VM_RUN_ONCE
            )
########################################################################


@attr(tier=1)
class TesNegativeHAStatelessVM(TestCase):
    """
    Test run once, negative test that run once HA VM in stateless mode
    """

    __test__ = True

    def setUp(self):
        """
        change vm to HA
        """
        logger.info("change vm to HA")
        if not ll_vms.updateVm(
                True, config.VM_RUN_ONCE, highly_available=True
        ):
            raise errors.VMException("Failed to set VM as highly available")

    @polarion("RHEVM3-9783")
    def test_negative_HA_and_stateless(self):
        """
        Nagtive test - run once HA VM in stateless mode
        """

        self.assertFalse(
            ll_vms.runVmOnce(True, config.VM_RUN_ONCE, stateless=True)
        )

    def tearDown(self):
        """
        stop vm and set vm as not highly available
        """
        logger.info("Stop %s vm", config.VM_RUN_ONCE)
        if not ll_vms.stopVm(True, config.VM_RUN_ONCE):
            raise errors.VMException(
                "Failed to stop vm %s", config.VM_RUN_ONCE
            )
        if not ll_vms.updateVm(
                True, config.VM_RUN_ONCE, highly_available=False
        ):
            raise errors.VMException(
                "Failed to set VM %s as not highly available"
                % config.VM_RUN_ONCE
            )
