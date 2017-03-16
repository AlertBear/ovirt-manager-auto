#! /usr/bin/python
# -*- coding: utf-8 -*-

import pytest
import copy

import rhevmtests.fixtures_helper as fixture_helper
from art.rhevm_api.tests_lib.low_level import (
    vms as ll_vms,
    vmpools as ll_vmpools,
    instance_types as ll_instance_types
)
from art.unittest_lib import testflow
import art.rhevm_api.tests_lib.high_level.storagedomains as hl_storagedomains
from rhevmtests.storage.helpers import (
    create_data_center, clean_dc, add_storage_domain
)
import config


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


@pytest.fixture()
def create_dc(request):
    """
    create data center with one host to the environment and a storage domain
    """
    comp_version = request.cls.comp_version
    host = config.HOSTS[request.cls.host_index]
    dc_name = "DC_%s" % comp_version.replace(".", "_")
    cluster_name = "Cluster_%s" % comp_version.replace(".", "_")
    sd_name = "SD_%s" % comp_version.replace(".", "_")

    def fin():
        """
        Clean DC- remove storage-domain & attach the host back to GE DC
        """
        testflow.setup("Clean DC and remove storage Domain")
        clean_dc(
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

    create_data_center(
        dc_name=dc_name,
        cluster_name=cluster_name,
        host_name=host,
        comp_version=comp_version
    )
    add_storage_domain(
        storage_domain=sd_name,
        data_center=dc_name,
        index=0,
        storage_type=config.STORAGE_TYPE_NFS
    )


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
    vm_parameters = copy.copy(
        getattr(request.node.cls, "vm_parameters", dict())
    )
    custom_params = fixture_helper.get_attr_helper(
        attribute='function.custom_vm_params.args',
        obj=request,
        default=None)
    if custom_params:
        vm_parameters.update(custom_params[0])
    vm_name = vm_parameters['name']
    assert ll_vms.addVm(True, **vm_parameters)

    def fin():
        """
        Remove created VM
        """
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)


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
