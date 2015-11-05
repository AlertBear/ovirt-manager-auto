"""
__Author__ = slitmano

Description:
This test module test specific vm_pool features.
polarion test plan:
project/RHEVM3/wiki/Compute/3_5_VIRT_VMPools
"""
import logging
from art.rhevm_api.tests_lib.low_level import (
    vms as vm_api, vmpools as vm_pool_api
)
from art.test_handler import exceptions as errors
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import VirtTest as TestCase, attr
from rhevmtests.virt import config
from rhevmtests.virt.vm_pools import helpers
from utilities import timeout as timeout_api

logger = logging.getLogger(__name__)

POSITIVE_CREATION_MESSAGE = "Cannot create vm pool: %s"
NEGATIVE_CREATION_MESSAGE = (
    "Vm pool: %s was created with wrong values - check pool's parameters"
)
NEW_IMPLEMENTATION_VERSION = '4.0'


def _create_vm_pool(positive, pool_name, pool_params):
    message = (
        POSITIVE_CREATION_MESSAGE if positive else NEGATIVE_CREATION_MESSAGE
    )
    logger.info(
        "Creating vm pool: %s with following parameters: %s",
        pool_name, pool_params
    )
    if not vm_pool_api.addVmPool(positive, **pool_params):
        raise errors.VmPoolException(message, pool_name)


def _wait_for_vm_pool_removed(vmpool, timeout=60, interval=5):
    logger.info("Stoping all vms in pool: %s", vmpool)
    vm_pool_size = vm_pool_api.get_vm_pool_size(vmpool)
    if not vm_pool_api.stopVmPool(True, vmpool):
        logger.error(
            "Failed to stop vms in pool: %s", vmpool
        )
    sampler = timeout_api.TimeoutingSampler(
        timeout, interval, vm_pool_api.removeVmPool, True, vmpool
    )
    timeout_message = (
        "Timeout waiting for vms in Pool: '{0}' to restore snapshots "
        "before deleting the pool'".format(vmpool)
    )
    sampler.timeout_exc_args = timeout_message
    try:
        for sampleOk in sampler:
            if sampleOk:
                break
    except timeout_api.TimeoutExpiredError:
        logger.error(timeout_message)
    pool_vms_names = helpers.generate_vms_name_list_from_pool(
        vmpool, vm_pool_size
    )
    # TODO: remove this iteration after bz 1245630 is resolved
    for vm in pool_vms_names:
        if vm_api.does_vm_exist(vm):
            logger.error(
                "Remove vm pool did not remove vm: %s after detaching it due "
                "to bz: 1245630. applying WA", vm
            )
            vm_api.removeVm(True, vm)


@attr(tier=1)
class BaseVmPool(TestCase):

    __test__ = False

    pool_name = None
    pool_size = 2
    max_vms_per_user = None
    pool_params = {}
    version = config.COMP_VERSION

    @classmethod
    def setup_class(cls):
        logger.info("Base setup for VM pool test")
        updated_params = {
            'name': cls.pool_name,
            'size': cls.pool_size,
            'cluster': config.CLUSTER_NAME[0],
            'template': config.TEMPLATE_NAME[0],
            'max_user_vms': cls.max_vms_per_user,
            }
        cls.pool_params.update(updated_params)

    @classmethod
    def tearDown(cls):
        logger.info("Base teardown for VM pool test")
        if vm_pool_api.does_vm_pool_exist(cls.pool_name):
            logger.info(
                "Setting number of prestarted vms in pool: %s "
                "back to 0", cls.pool_name
            )
            if not vm_pool_api.updateVmPool(
                True,
                cls.pool_name,
                prestarted_vms=0
            ):
                logger.error(
                    "couldn't update pool: %s and set %d prestarted vms",
                    cls.pool_name, cls.prestarted_vms
                )
            logger.info(
                "Removing vm_pool :%s",
                cls.pool_name
            )
            if cls.version < NEW_IMPLEMENTATION_VERSION:
                _wait_for_vm_pool_removed(cls.pool_name)
            else:
                if not vm_pool_api.removeVmPool(True, cls.pool_name):
                    logger.error(
                        "Failed to remove pool: %s" % cls.pool_name)


class VmPool(BaseVmPool):

    __test__ = False

    @classmethod
    def setup_class(cls):
        super(VmPool, cls).setup_class()
        _create_vm_pool(True, cls.pool_name, cls.pool_params)


class TestCreatePoolSanity(BaseVmPool):

    __test__ = True

    pool_name = 'Virt_vmpool'

    @polarion("RHEVM3-9879")
    def test_create_vm_pool_sanity(self):
        _create_vm_pool(True, self.pool_name, self.pool_params)


class TestFullCreateRemovePoolCycle(BaseVmPool):
    """
    This test covers the basic vm pool flow not using the deleteVmPool
    function which handles stop vms -> detach vms -> delete vms -> delete pool
    in engine, but doing this process step by step.
    """

    __test__ = True

    pool_name = 'Virt_vmpool_full_cycle'

    @polarion("RHEVM-13976")
    def test_full_create_remove_pool_cycle(self):
        _create_vm_pool(True, self.pool_name, self.pool_params)
        if not vm_pool_api.start_vm_pool(True, self.pool_name):
            raise errors.VmPoolException(
                "Failed to start vms in pool: %s", self.pool_name
            )
        if not helpers.remove_whole_vm_pool(
            self.pool_name, self.pool_size, stop_vms=True
        ):
            raise errors.VmPoolException(
                "Failed to remove pool: %s and all it's vms" % self.pool_name
            )


class TestUpdatePoolWithPrestartedVms(VmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_update_prestarted'
    pool_size = 3
    prestarted_vms = 2

    @polarion("RHEVM3-9873")
    def test_update_vm_pool_with_prestarted_vms(self):
        if not vm_pool_api.updateVmPool(
            True,
            self.pool_name,
            prestarted_vms=self.prestarted_vms
        ):
            raise errors.VmPoolException(
                "couldn't update pool: %s and set %d prestarted vms" % (
                    self.pool_name,
                    self.prestarted_vms
                )
            )
        if not helpers.wait_for_prestarted_vms(self.pool_name):
            raise errors.VmPoolException(
                "Cannot find %d vms from pool that started",
                self.prestarted_vms
            )


class TestUpdatePoolWithTooManyPrestartedVms(VmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_invalid_prestarted'
    prestarted_vms = 3

    @polarion("RHEVM3-12740")
    def test_create_pool_with_too_many_prestarted_vms(self):
        if not vm_pool_api.updateVmPool(
            False,
            self.pool_name,
            prestarted_vms=self.prestarted_vms
        ):
            raise errors.VmPoolException(
                "There are more prestarted vms configured"
                " than actual number of vms in pool: %s" %
                self.pool_name
            )


class TestCreatePoolSetNumberOfVmsPerUser(BaseVmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_create_max_user_vms'
    max_vms_per_user = 3

    @polarion("RHEVM3-9865")
    def test_create_pool_set_number_of_vms_per_user(self):
        _create_vm_pool(True, self.pool_name, self.pool_params)
        if not (
            self.max_vms_per_user == vm_pool_api.get_vm_pool_max_user_vms(
                self.pool_name
            )
        ):
            raise errors.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.new_max_user_vms,
                    self.max_vms_per_user
                )
            )


class TestCreatePoolSetInvalidNumberOfVmsPerUser(BaseVmPool):

    __test__ = True

    max_vms_per_user = -1
    pool_name = 'Virt_vmpool_create_invalid_max_user_vms'

    @polarion("RHEVM3-9864")
    def test_create_pool_set_invalid_number_of_vms_per_user(self):
        _create_vm_pool(False, self.pool_name, self.pool_params)


class TestUpdatePoolNumberOfVmsPerUser(VmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_update_max_user_vms'
    new_max_user_vms = 3

    @polarion("RHEVM3-9866")
    def test_update_pool_number_of_vms_per_user(self):
        if not vm_pool_api.updateVmPool(
            True,
            self.pool_name,
            max_user_vms=self.new_max_user_vms
        ):
            raise errors.VmPoolException(
                "Couldn't update vm pool: %s and "
                "set the max number of vms per user to %d" % (
                    self.pool_name,
                    self.new_max_user_vms
                )
            )
        if not (
            self.new_max_user_vms == vm_pool_api.get_vm_pool_max_user_vms(
                self.pool_name
            )
        ):
            raise errors.VmPoolException(
                "Expected max number of vms per user to be %d, got %d" % (
                    self.new_max_user_vms,
                    self.max_vms_per_user
                )
            )


class TestUpdatePoolWithInvalidNumberOfVmsPerUser(VmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_update_invalid_max_user_vms'
    new_max_user_vms = -1

    @polarion("RHEVM3-9867")
    def test_update_pool_with_invalid_number_of_vms_per_user(self):
        if not vm_pool_api.updateVmPool(
            False,
            self.pool_name,
            max_user_vms=self.new_max_user_vms
        ):
            raise errors.VmPoolException(
                "Updated vm pool: %s max number of vms per user with "
                "invalid value: %d" % (
                    self.pool_name,
                    self.new_max_user_vms
                )
            )


class TestAddVmsToPool(VmPool):

    __test__ = True

    pool_name = 'Virt_vmpool_add_to_pool'
    new_pool_size = 3

    @polarion("RHEVM3-9870")
    def test_add_vms_to_pool(self):
        if not vm_pool_api.updateVmPool(
            True,
            self.pool_name,
            size=self.new_pool_size
        ):
            raise errors.VmPoolException(
                "Failed to increase number of vms in pool from: %d to %d" % (
                    self.pool_size,
                    self.new_pool_size
                )
            )
        self.__class__.pool_size = self.new_pool_size
        vms_in_pool = helpers.generate_vms_name_list_from_pool(
            self.pool_name,
            self.new_pool_size
        )
        logger.info("Searching for new vm: %s", vms_in_pool[-1])
        vm_api.get_vm(vms_in_pool[-1])
        logger.info(
            "The new vm: %s was successfully added pool %s",
            vms_in_pool[-1],
            self.pool_name
        )
        if not vm_api.waitForVmsStates(
            True,
            vms_in_pool[-1],
            states=config.ENUMS["vm_state_down"]
        ):
            raise errors.VMException(
                "vm: %s has wrong status after creation. Expected: %s" %
                (vms_in_pool[-1], config.ENUMS["vm_state_down"])
            )