#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Virt - Cloud init sanity Test
Check basic cases with cloud init
"""
import logging
import config
import helper
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import common
import art.rhevm_api.data_struct.data_structures as data_struct
import art.test_handler.exceptions as errors
import art.rhevm_api.tests_lib.low_level.vms as ll_vms

logger = logging.getLogger("cloud_init")


@common.attr(tier=1)
@common.skip_class_if(config.PPC_ARCH, config.PPC_SKIP_MESSAGE)
class CloudInitBase(common.VirtTest):
    """
    Base class for Cloud init Test
    General note for all cases:
    There is BZs on networks configuration
    BZ#: https://bugzilla.redhat.com/show_bug.cgi?id=1284767
    https://bugzilla.redhat.com/show_bug.cgi?id=1288105
    Network check is incomplete, when BZs will be solved we will update cases
    """
    vm_name = config.CLOUD_INIT_VM_NAME
    initialization = None
    __test__ = True

    @classmethod
    def setup_class(cls):
        logger.info(
            "Set Initialization with: %s", helper.initialization_params
        )
        cls.initialization = data_struct.Initialization(
            **helper.initialization_params
        )

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove vm after each test case
        """
        logger.info("Remove vm %s", cls.vm_name)
        if not ll_vms.remove_all_vms_from_cluster(
            config.CLUSTER_NAME[0], skip=config.VM_NAME
        ):
            logger.error("Failed to remove vms")

    @classmethod
    def _create_vm(cls, initialization=None):
        """
        Create new vm from template with initialization parameters
        """
        logger.info("Create new vm %s from cloud init template", cls.vm_name)
        if not ll_vms.createVm(
            positive=True, vmName=cls.vm_name, vmDescription=cls.vm_name,
            cluster=config.CLUSTER_NAME[0],
            template=config.CLOUD_INIT_TEMPLATE, os_type=config.VM_OS_TYPE,
            display_type=config.VM_DISPLAY_TYPE,
            initialization=initialization,
            nic=config.NIC_NAME[0],
            network=config.MGMT_BRIDGE
        ):
            raise errors.VMException("Failed to create vm %s" % cls.vm_name)
        logger.info("update disk to bootable")
        ll_vms.updateVmDisk(
            positive=True, vm=cls.vm_name,
            disk=config.CLOUD_INIT_VM_DISK_NAME, bootable=True
        )


class TestCloudInitCase01(CloudInitBase):
    """
    Cloud init case 1: Create new VM with cloud init parameters
    Run vm, and check configuration exists on VM
    """

    @polarion("RHEVM3-14364")
    def test_new_vm_with_cloud_init(self):
        """
        Create vm and start vm with cloud init parameters.
        """
        logger.info(
            "Create vm %s with initialization: %s",
            self.vm_name, self.initialization
        )
        self._create_vm(self.initialization)
        if not ll_vms.startVm(
            positive=True, vm=self.vm_name, wait_for_ip=True,
            use_cloud_init=True
        ):
            raise errors.VMException(
                "Failed to start vm: %s" % self.vm_name
            )
        self.assertTrue(
            helper.check_cloud_init_parameters(
                script_content=helper.SCRIPT_CONTENT,
                time_zone=config.NEW_ZEALAND_TZ_VALUE,
                hostname=config.CLOUD_INIT_HOST_NAME
            ),
            "Failed checking VM, one or more of init parameter/s didn't set"
        )


class TestCloudInitCase02(CloudInitBase):
    """
    Cloud init case 2: Create new VM with cloud init parameters
    Run vm with run once with user root, and check configuration exists on VM
    """

    @classmethod
    def setup_class(cls):
        logger.info("Update user to root")
        config.VM_USER_CLOUD_INIT = config.VDC_ROOT_USER
        helper.initialization_params['user_name'] = config.VDC_ROOT_USER
        super(TestCloudInitCase02, cls).setup_class()
        logger.info("Create vm %s ", cls.vm_name)
        cls._create_vm()

    @classmethod
    def teardown_class(cls):
        logger.info("Restore cloud init user name")
        helper.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        helper.initialization_params['user_name'] = config.VM_USER_CLOUD_INIT_1
        super(TestCloudInitCase02, cls).teardown_class()

    @polarion("RHEVM3-4795")
    def test_new_vm_with_cloud_init_run_once(self):
        """
        Create vm and start vm with run once
        """

        logger.info(
            "Start Vm with Run once with initialization %s",
            self.initialization
        )
        if not ll_vms.runVmOnce(
            positive=True, vm=self.vm_name, use_cloud_init=True,
            initialization=self.initialization,
            wait_for_state=config.VM_UP
        ):
            raise errors.VMException(
                "Failed to start VM %s " % self.vm_name
            )
        logger.info("Check VM with root user")
        self.assertTrue(
            helper.check_cloud_init_parameters(
                time_zone=config.NEW_ZEALAND_TZ_VALUE,
                check_nic=False, script_content=helper.SCRIPT_CONTENT,
            ),
            "Failed checking VM, one or more of init parameter/s didn't set"
        )


class TestCloudInitCase03(CloudInitBase):
    """
    Cloud init case 3: Update VM cloud init configuration with run once
    And check configuration exists
    """

    @classmethod
    def setup_class(cls):
        """
        Create vm with initialization, run and stop it.
        """

        logger.info("Create vm %s", cls.vm_name)
        cls._create_vm(initialization=cls.initialization)
        logger.info("Start vm %s", cls.vm_name)
        if not ll_vms.startVm(
            True, cls.vm_name, wait_for_ip=False, use_cloud_init=True
        ):
            raise errors.VMException(
                "Failed to start vm: %s" % cls.vm_name
            )
        if ll_vms.get_vm_state(cls.vm_name) not in config.VM_DOWN:
            logger.info("Stop vm %s", cls.vm_name)
            if not ll_vms.stopVm(True, cls.vm_name):
                raise errors.VMException(
                    "Failed to stop vm: %s" % cls.vm_name
                )

    @classmethod
    def tearDown(cls):
        logger.info("Restore cloud init user name")
        helper.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        helper.updated_initialization_params['user_name'] = (
            config.VM_USER_CLOUD_INIT
        )
        super(TestCloudInitCase03, cls).teardown_class()

    @polarion("RHEVM3-14365")
    def test_update_vm_from_run_once(self):
        """
        Update cloud init parameters with run once, login with new user
        """
        logger.info(
            "Update initialization with: new user name %s, time zone %s",
            config.VM_USER_CLOUD_INIT_2, config.MEXICO_TZ_VALUE
        )
        logger.info("update user name to: %s", config.VM_USER_CLOUD_INIT_2)
        config.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_2
        helper.updated_initialization_params['user_name'] = (
            config.VM_USER_CLOUD_INIT_2
        )
        initialization = data_struct.Initialization(
            **helper.updated_initialization_params
        )
        logger.info("Run VM with run once")
        if not ll_vms.runVmOnce(
            positive=True, vm=self.vm_name, use_cloud_init=True,
            initialization=initialization, wait_for_state=config.VM_UP
        ):
            raise errors.VMException(
                "Failed to start VM %s " % self.vm_name
            )
        self.assertTrue(
            helper.check_cloud_init_parameters(
                time_zone=config.MEXICO_TZ_VALUE,
                check_nic=False, hostname=config.CLOUD_INIT_HOST_NAME,
                script_content=helper.SCRIPT_CONTENT,
            ),
            "Failed checking VM, one or more of parameter/s didn't updated"
        )


class TestCloudInitCase04(CloudInitBase):
    """
    Cloud init case 4: Check migration of VM with Cloud init configuration
    """

    @classmethod
    def setup_class(cls):
        """
        Create and new vm, start vm with initialization, stop vm.
        """
        logger.info("Setting user name to: %s", config.VM_USER_CLOUD_INIT_1)
        helper.VM_USER_CLOUD_INIT = config.VM_USER_CLOUD_INIT_1
        helper.initialization_params['user_name'] = (
            config.VM_USER_CLOUD_INIT
        )
        super(TestCloudInitCase04, cls).setup_class()
        cls._create_vm(initialization=cls.initialization)
        if not ll_vms.startVm(
            positive=True, vm=cls.vm_name, wait_for_ip=True,
            use_cloud_init=True
        ):
            raise errors.VMException(
                "Failed to start vm: %s" % cls.vm_name
            )

    @polarion("RHEVM3-14369")
    def test_migration_vm(self):
        """
        Migration VM with cloud init configuration
        """
        logger.info("Migration VM")
        self.assertTrue(
            ll_vms.migrateVm(
                positive=True, vm=self.vm_name
            ),
            "Failed to migrate VM: %s " % self.vm_name
        )
        logger.info(
            "Check that all cloud init configuration exists after migration"
        )
        self.assertTrue(
            helper.check_cloud_init_parameters(
                script_content=helper.SCRIPT_CONTENT,
                time_zone=config.NEW_ZEALAND_TZ_VALUE,
                hostname=config.CLOUD_INIT_HOST_NAME
            ),
            "Failed checking VM, one or more of parameter/s didn't set"
        )


class TestCloudInitCase05(CloudInitBase):
    """
    Cloud init case 5: Check authorized ssh keys setting, connecting
    to vm without password
    """

    @classmethod
    def setup_class(cls):
        """
        Create and new vm, start vm with initialization.
        """
        super(TestCloudInitCase05, cls).setup_class()
        logger.info("Set ssh public key in initialization")
        cls.initialization.set_authorized_ssh_keys(
            config.ENGINE_HOST.get_ssh_public_key()
        )
        logger.info("Set use private key")
        config.USER_PKEY = True
        cls._create_vm(cls.initialization)
        logger.info("Start vm %s", cls.vm_name)
        if not ll_vms.startVm(
            positive=True, vm=cls.vm_name, wait_for_ip=True,
            use_cloud_init=True
        ):
            raise errors.VMException(
                "Failed to start vm: %s" % cls.vm_name
            )

    @classmethod
    def teardown_class(cls):
        """
        Stop and remove vm after each test case
        """
        config.USER_PKEY = False
        super(TestCloudInitCase05, cls).teardown_class()

    @polarion("RHEVM3-4796")
    def test_authorized_ssh_keys(self):
        """
        Check connectivity without password
        """
        logger.info("Check connectivity without password")
        self.assertTrue(
            helper.check_cloud_init_parameters(
                script_content=helper.SCRIPT_CONTENT,
                time_zone=config.NEW_ZEALAND_TZ_VALUE,
                hostname=config.CLOUD_INIT_HOST_NAME
            ),
            "Failed checking VM, one or more of parameter/s didn't set"
        )
