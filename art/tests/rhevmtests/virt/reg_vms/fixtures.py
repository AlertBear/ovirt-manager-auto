#! /usr/bin/python
# -*- coding: utf-8 -*-


import logging
import pytest
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import config
import rhevmtests.virt.helper as virt_helper

logger = logging.getLogger("reg_vm_fixture")


class RegVmBase(object):
    """
    Class reg vm base
    """
    master_domain, export_domain, non_master_domain = (
        virt_helper.get_storage_domains()
    )

    @classmethod
    def remove_vm_from_storage_domain(cls, vm_name):
        """
        Remove the VM from export storage

        :param vm_name: name of the vm
        :type vm_name: str
        """

        if ll_vms.export_domain_vm_exist(vm_name, cls.export_domain):
            assert ll_vms.remove_vm_from_export_domain(
                True, vm_name, config.DC_NAME[0], cls.export_domain
            )

    @classmethod
    def remove_stateless_vm(cls, vm_name):
        """
        1. Stop stateless vm and check that snapshot is removed
        2. Remove vm

        :param vm_name: name of the vm
        :type vm_name: str
        """
        assert hl_vms.stop_stateless_vm(vm_name)
        assert ll_vms.safely_remove_vms([vm_name])


@pytest.fixture()
def basic_teardown_fixture(request):
    """
    Remove vm safely
    """

    vm_name = request.cls.vm_name

    def fin():
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)


@pytest.fixture()
def add_vm_fixture(request):
    """
    Create vm, remove it in fin
    vm name is taken from class member
    """

    vm_name = request.cls.vm_name
    add_disk = request.cls.add_disk

    def fin():
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    assert virt_helper.create_base_vm(vm_name=vm_name, add_disk=add_disk)


@pytest.fixture()
def stateless_vm_test_fixture(request):
    """
    Fixture for stateless test:
    1. Create stateless vm
    2. Remove it in fin
    """
    vm_name = request.cls.vm_name
    vm_parameters = request.cls.vm_parameters

    base = RegVmBase

    def fin():
        base.remove_stateless_vm()

    request.addfinalizer(fin)

    assert virt_helper.create_vm_from_template(
        vm_name=vm_name,
        template=config.template_name,
        vm_parameters=vm_parameters
    )

    assert ll_vms.startVm(positive=True, vm=vm_name)


@pytest.fixture()
def add_template_fixture(request):
    """
    1. Create vm and from this vm create template
    2. Remove vm and template

    """
    vm_name = 'tmp_vm'
    template_base = 'template_virt'

    def fin():
        assert ll_vms.safely_remove_vms([vm_name])
        assert ll_templates.removeTemplate(True, template_base)

    request.addfinalizer(fin)

    assert virt_helper.create_base_vm(vm_name=vm_name, add_disk=True)
    assert ll_templates.createTemplate(True, vm=vm_name, name=template_base)


@pytest.fixture()
def test_snapshot_and_import_export_fixture(request):
    """
    Fixture for snapshot and import export tests:
    1. Create test vm
    2. fin1: Remove vm from export domain
    3. fin2: Remove vm

    """
    vm_name = request.cls.vm_name

    base = RegVmBase

    def fin1():
        base.remove_vm_from_storage_domain(vm_name=vm_name)

    request.addfinalizer(fin1)

    def fin2():
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin2)

    assert virt_helper.create_base_vm(vm_name=vm_name, add_disk=True)


@pytest.fixture()
def add_vm_from_template_fixture(request):
    """
    Create vm from template with parameters, remove it in fin
    vm name is taken from class member
    """

    vm_name = request.cls.vm_name
    cluster_name = request.cls.cluster_name
    template_name = request.cls.template_name
    vm_parameters = request.cls.vm_parameters

    def fin():
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    assert virt_helper.create_vm_from_template(
        vm_name=vm_name,
        cluster=cluster_name,
        template=template_name,
        vm_parameters=vm_parameters
    )


@pytest.fixture(scope="class")
def vm_display_fixture(request):
    """
    Create two new vms, one with vnc type display and
    second with spice type display
    """
    vm_names = request.cls.vm_names
    display_types = request.cls.display_types

    def fin():
        assert ll_vms.safely_remove_vms(vm_names)

    request.addfinalizer(fin)

    for display_type in display_types:
        vm_name = '%s_vm' % display_type
        assert virt_helper.create_base_vm(
            vm_name=vm_name,
            display_type=display_type,
            add_disk=True
        )
        assert ll_vms.startVm(True, vm_name)
