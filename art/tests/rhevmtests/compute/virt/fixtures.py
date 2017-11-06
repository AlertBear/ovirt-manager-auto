#! /usr/bin/python
# -*- coding: utf-8 -*-

import copy

import pytest

import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
import config
import rhevmtests.fixtures_helper as fixture_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    instance_types as ll_instance_types
)
from art.unittest_lib import testflow
from rhevmtests.storage import helpers as storage_helper


@pytest.fixture(scope="class")
def remove_vm(request):
    """
    Remove vm safely
    """

    vm_name = request.cls.vm_name

    def fin():
        testflow.teardown("Remove vm %s", vm_name)
        ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def start_vms(request):
    """
    Start VM's
    """
    vms = request.node.cls.vm_name
    wait_for_vms_ip = getattr(request.node.cls, "wait_for_vms_ip", True)

    def fin():
        """
        Stop VM's
        """
        testflow.teardown("Stop vms %s", vms)
        ll_vms.stop_vms_safely(vms_list=[vms])
    request.addfinalizer(fin)

    testflow.setup("Start vms %s", vms)
    ll_vms.start_vms(vm_list=[vms], wait_for_ip=wait_for_vms_ip)


@pytest.fixture(scope="function")
def start_vms_function_scope(request):
    """
    Start VM's
    """
    vms = request.node.cls.vm_name
    wait_for_vms_ip = getattr(request.node.cls, "wait_for_vms_ip", True)

    def fin():
        """
        Stop VM's
        """
        testflow.teardown("Stop vms %s", vms)
        ll_vms.stop_vms_safely(vms_list=[vms])
    request.addfinalizer(fin)

    testflow.setup("Start vms %s", vms)
    ll_vms.start_vms(vm_list=[vms], wait_for_ip=wait_for_vms_ip)


@pytest.fixture(scope="class")
def create_dc(request):
    """
    Create Data Center with one host one NFS storage domain
    """
    comp_version = request.cls.dc_version_to_create
    host = config.HOSTS[2]
    dc_name = "DC_%s" % comp_version.replace(".", "_")
    cluster_name = "Cluster_%s" % comp_version.replace(".", "_")
    sd_name = "SD_%s" % comp_version.replace(".", "_")

    def fin():
        """
        Clean DC- remove storage-domain & attach the host back to GE DC
        """
        testflow.setup("Clean DC and remove storage Domain")
        storage_helper.clean_dc(
            dc_name=dc_name,
            cluster_name=cluster_name,
            dc_host=host, sd_name=sd_name
        )
        assert hl_storagedomains.remove_storage_domain(
            name=sd_name,
            datacenter=config.DC_NAME[0],
            host=host,
            engine=config.ENGINE,
            format_disk=True
        )

    request.addfinalizer(fin)
    testflow.setup(
        "Create Data Center %s with compatibility version: %s "
        "and storage domain %s",
        dc_name, comp_version, sd_name
    )

    storage_helper.create_data_center(
        dc_name=dc_name,
        cluster_name=cluster_name,
        host_name=host,
        comp_version=comp_version
    )

    assert hl_storagedomains.addNFSDomain(
            host=host,
            storage=sd_name,
            data_center=dc_name,
            address=config.UNUSED_DATA_DOMAIN_ADDRESSES[0],
            path=config.UNUSED_DATA_DOMAIN_PATHS[0],
            format=True,
        )


@pytest.fixture(scope="class")
def create_vm_class(request):
    """
    Create VM with teardown.
    VM parameters are taken from vm_parameters attribute of test class
    Parameters can be overriden with @pytest.mark.custom_vm_params decorator
    for instance:
    @pytest.mark.custom_vm_params({
        'memory': get_gb(4),
        'max_memory': get_gb(4),
    })
    """
    vm_parameters = init_parameters(request)
    vm_name = vm_parameters['name']

    def fin():
        """
        Remove created VM
        """
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)
    assert ll_vms.addVm(True, **vm_parameters)


@pytest.fixture(scope="function")
def create_vm(request):
    """
    Create VM with teardown.
    VM parameters are taken from vm_parameters attribute of test class
    Parameters can be overriden with @pytest.mark.custom_vm_params decorator
    for instance:
    @pytest.mark.custom_vm_params({
        'memory': get_gb(4),
        'max_memory': get_gb(4),
    })
    """
    vm_parameters = init_parameters(request)
    vm_name = vm_parameters['name']

    def fin():
        """
        Remove created VM
        """
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)
    assert ll_vms.addVm(True, **vm_parameters)


def init_parameters(request):
    vm_parameters = copy.copy(
        getattr(request.node.cls, "vm_parameters", dict())
    )
    custom_vm_marker = request.node.get_marker('custom_vm_params')
    custom_params = custom_vm_marker.kwargs if custom_vm_marker else (
        fixture_helper.get_fixture_val(
            request=request,
            attr_name='custom_vm_params',
            default_value=None
        )
    )
    if custom_params:
        vm_parameters.update(custom_params)
    return vm_parameters


@pytest.fixture()
def create_instance_type(request):
    """
    Create new instance type, delete on teardown
    Instance type parameters are taken from instance_type_parameters
    attribute of test class
    Parameters can be overriden with @pytest.mak.custom_instance_type_params
    decorator. Example:
    @pytest.mark.custom_instance_type_params({
        'instance_type_name': config.CUSTOM_INSTANCE_TYPE_NAME,
    })
    """
    instance_type_params = copy.copy(
        getattr(request.node.cls, "instance_type_params", dict())
    )
    custom_it_params = fixture_helper.get_attr_helper(
        attribute='function.custom_instance_type_params.args',
        obj=request,
        default=None)
    if custom_it_params:
        instance_type_params.update(custom_it_params[0])
    assert ll_instance_types.create_instance_type(**instance_type_params)

    def fin():
        """
        Remove created instance type
        """
        assert ll_instance_types.remove_instance_type(
            instance_type_params['instance_type_name'])

    request.addfinalizer(fin)


@pytest.fixture()
def create_vm_pool(request):
    pool_config = copy.copy(
        getattr(request.node.cls, "vm_pool_config", dict())
    )
    assert ll_vmpools.addVmPool(positive=True, wait=True, **pool_config)
    pool_obj = ll_vmpools.get_vm_pool_object(pool_config['name'])

    def fin():
        assert ll_vmpools.removeVmPool(True, pool_config['name'], wait=True)

    request.addfinalizer(fin)
    return pool_obj


@pytest.fixture(scope="class")
def edit_instance_types(request):
    """
    Edit instance types, restore on teardown
    """
    instance_types = getattr(request.node.cls, "instance_types", dict())
    instance_type_params = getattr(
        request.node.cls,
        "instance_type_params",
        dict()
    )
    default = dict()
    testflow.setup('Edit instance types {} with parameters: {}'.format(
        instance_types, instance_type_params)
    )
    for it in instance_types:
        default[it] = dict()
        it_obj = ll_instance_types.get_instance_type_object(it)
        for val in instance_type_params:
            if val == 'max_memory':
                default[it][val] = it_obj.memory_policy.max
                continue
            elif val == 'memory_guaranteed':
                default[it][val] = it_obj.memory_policy.guaranteed
                continue
            default[it][val] = getattr(it_obj, val)
        assert ll_instance_types.update_instance_type(
            instance_type_name=it,
            **instance_type_params)

    def fin():
        """
        Return instance types to their default values
        """
        for it in instance_types:
            testflow.teardown(
                'Return instance type {} to default'.format(it)
            )
            assert ll_instance_types.update_instance_type(it, **default[it])

    request.addfinalizer(fin)


@pytest.fixture()
def remove_created_vms(request):
    """
    Remove vm safely
    """
    reg_vms = getattr(request.node.cls, "reg_vms", [])

    def fin():
        """
        Remove all created vms safely if any
        """
        assert ll_vms.safely_remove_vms(reg_vms)

    request.addfinalizer(fin)


@pytest.fixture()
def start_vm_with_parameters(request):
    """
    Start vm with parameters
    """
    vm_name = request.node.cls.vm_name
    start_vm_parameters = request.node.cls.start_vm_parameters

    testflow.setup(
        "Start VM %s with parameters %s", vm_name, start_vm_parameters
    )
    assert ll_vms.startVm(
        positive=True, vm=vm_name, **start_vm_parameters
    ), "Failed to start vm"


@pytest.fixture()
def update_vm(request):
    """
    Update VM
    """
    vm_name = request.node.cls.vm_name
    update_vm_params = request.node.cls.update_vm_params
    testflow.setup(
        "Update VM %s with %s", vm_name, update_vm_params
    )
    assert ll_vms.updateVm(
        positive=True, vm=vm_name, **update_vm_params
    ), "Failed to update vm with params %s" % update_vm_params


@pytest.fixture(scope="class")
def update_vm_to_default_parameters(request):
    vm_name = request.node.cls.vm_name

    def fin():
        """
        Update VM's to default parameters
        """
        testflow.teardown(
            "Update the VM %s to default parameters", vm_name
        )
        ll_vms.updateVm(
            positive=True, vm=vm_name, **config.DEFAULT_VM_PARAMETERS
        )
    request.addfinalizer(fin)
