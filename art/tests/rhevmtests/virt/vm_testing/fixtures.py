import re
import copy
import pytest
import logging
import config

from art.rhevm_api.tests_lib.low_level import vms as ll_vms
from art.unittest_lib import testflow


logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def test_description(request):
    """
    Reproduce test description on the screen and art_log.
    """
    test_descr = request.getfixturevalue("test_descr")
    description = test_descr.values()[0]
    msg = "Test description: {descr}".format(descr=description)
    logger.info(msg)
    testflow.setup(msg)


@pytest.fixture(scope="function")
def setup_vm(request, test_description):
    """
    Setup of VM for Edit_VM module.

    Setup:
        Create VMs according to scenario values.
    """

    setup_data = request.getfixturevalue("setup_data")

    for instance_type, instance_params in setup_data.iteritems():
        if re.search("VM", instance_type):
            new_values = copy.deepcopy(instance_params)
            new_values[0].update(new_values[1])
            if not ll_vms.does_vm_exist(new_values[0]["vmName"]):
                msg = (
                    "Was {status}able to create a VM: {vm}.".format(
                        status=("not " if new_values[0]['positive'] else ""),
                        vm=new_values[0]["vmName"]
                    )
                )
                assert ll_vms.createVm(**new_values[0]), msg
                config.VMS_CREATED.append(new_values[0]["vmName"])


@pytest.fixture(scope="function")
def remove_vms_func_scope(request):
    """
    Teardown procedure to remove test VMs on function level.
    """

    def fin():
        """
        Teardown:
            Safely remove VMs.
        """
        testflow.teardown(
            "Removing following VMS: {vm_list}".format(
                vm_list=config.VMS_CREATED
            )
        )
        if config.VMS_CREATED:
            assert ll_vms.safely_remove_vms(
                vms=config.VMS_CREATED
            ), "Failed to safelly remove {vm} as part of teardown.".format(
                vm=config.VMS_CREATED
            )
            for vm_name in config.VMS_CREATED:
                config.VMS_CREATED.remove(vm_name)

    request.addfinalizer(fin)
