#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Fixtures for template test module
"""
import pytest
import config as conf
from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms,
    mla as ll_mla,
    users as ll_users,
    datacenters as ll_dcs,
    clusters as ll_clusters,
    storagedomains as ll_sds
)
from art.test_handler import exceptions


def create_base_vms():
    """
    Creates 2 vms to serve as base vms for the templates
    """
    for vm, vm_params in conf.BASE_VM_MAP.iteritems():
        if not ll_vms.addVm(True, name=vm, **vm_params):
            raise exceptions.VMException()


def remove_base_vms():
    """
    Removes the 2 base vm used to create templates in the module
    """
    for vm in conf.BASE_VM_LIST:
        if ll_vms.get_vm(vm).get_delete_protected() is conf.DELETE_PROTECTED:
            ll_vms.updateVm(
                True, vm=vm, protected=not conf.DELETE_PROTECTED
            )
    ll_vms.safely_remove_vms(conf.BASE_VM_LIST)


def remove_no_disk_vms():
    """
    Removes the 2 vms creates without disks by templates
    """
    vms_to_delete = [conf.VM_NO_DISK_1, conf.VM_NO_DISK_2]
    for vm in [conf.VM_NO_DISK_1, conf.VM_NO_DISK_2]:
        if not ll_vms.does_vm_exist(vm):
            vms_to_delete.remove(vm)
            continue
        if ll_vms.get_vm(vm).get_delete_protected() is conf.DELETE_PROTECTED:
            ll_vms.updateVm(
                True, vm, protected=not conf.DELETE_PROTECTED
            )
    ll_vms.safely_remove_vms(vms_to_delete)


def remove_base_templates():
    """
    Removes the templates creates in the test
    """
    for template, versions in conf.TEMPLATE_NAMES.iteritems():
        for version in reversed(versions):
            template_object = ll_templates.get_template_obj(
                template, version=version
            )
            if not template_object:
                continue
            if template_object.get_delete_protected() is (
                conf.DELETE_PROTECTED
            ):
                ll_templates.updateTemplate(
                    True, template, version,
                    protected=not conf.DELETE_PROTECTED
                )
            ll_templates.remove_template(True, template, version)


@pytest.fixture()
def remove_existing_templates(request):
    """
    Fixture for test_01 - used as teardown
    """
    def fin1():
        """
        Remove base templates
        """
        remove_base_templates()
    request.addfinalizer(fin1)


@pytest.fixture()
def restore_base_template_configurations(request):
    """
    Fixture for test_03 - used as teardown
    """
    def fin1():
        """
        Revert to template's original parameters values
        """
        ll_templates.updateTemplate(
            True, conf.TEMPLATE_LIST[0],
            **conf.BASE_VM_1_PARAMETERS
        )
    request.addfinalizer(fin1)


@pytest.fixture()
def supply_base_templates(request):
    """
    Fixture for tests 03-15, test_19, test_21 - used as setup
    """
    marker = request.node.get_marker("template_marker")
    versions = marker.kwargs.get("template_versions")
    for version in versions:
        if not ll_templates.validateTemplate(
            True, conf.TEMPLATE_LIST[0], version
        ):
            assert ll_templates.createTemplate(
                positive=True, name=conf.TEMPLATE_LIST[0],
                new_version=True, vm=conf.BASE_VM_LIST[version-1],
            )


@pytest.fixture()
def supply_vm(request):
    """
    Fixture for tests 10-12 - used as setup
    """
    marker = request.node.get_marker("vm_marker")
    vm = marker.kwargs.get("vm_name")
    template_version = marker.kwargs.get("template_version")
    if not ll_vms.does_vm_exist(vm):
        assert ll_vms.addVm(
            True, name=vm, template=conf.TEMPLATE_LIST[0],
            template_version=template_version, cluster=conf.CLUSTER_NAME[0]
        )


@pytest.fixture()
def remove_vm(request):
    """
    Fixture for test_14 - used as setup
    """
    marker = request.node.get_marker("vm_marker")
    vm = marker.kwargs.get("vm_name")
    if ll_vms.does_vm_exist(vm):
        assert ll_vms.safely_remove_vms([vm])


@pytest.fixture()
def add_user_role_permission_for_base_vm(request):
    """
    Fixture for test_02 - includes setup and teardown
    """
    def fin():
        """
        Remove userRole permission from base vm
        """
        ll_mla.removeUserPermissionsFromVm(
            True, conf.BASE_VM_1, conf.USER
        )
    request.addfinalizer(fin)
    assert ll_mla.addVMPermissionsToUser(
        True, conf.USER, conf.BASE_VM_1, conf.USER_ROLE
    )


@pytest.fixture()
def add_user_role_permission_for_template(request):
    """
    Fixture for test_14 - includes setup and teardown
    """
    marker = request.node.get_marker("template_marker")
    version = marker.kwargs.get("template_versions")[0]
    template_object = ll_templates.get_template_obj(
        conf.TEMPLATE_LIST[0], version=version
    )

    def fin():
        """
        Remove userRole permission from base template
        """
        ll_mla.removeUserRoleFromObject(
            True, template_object, conf.USER, conf.USER_ROLE
        )
    request.addfinalizer(fin)
    assert ll_mla.addUserPermitsForObj(
        True, conf.USER, conf.USER_ROLE, template_object
    )


@pytest.fixture()
def remove_template_admin_role_from_group(request):
    """
    Fixture for test_19 - used as teardown
    """
    template_object = ll_templates.get_template_obj(conf.TEMPLATE_LIST[0])

    def fin():
        """
        Removes templateAdmin role from group - Everyone
        """
        ll_mla.removeUserRoleFromObject(
            True, template_object, conf.GROUP_EVERYONE, conf.TEMPLATE_ROLE
        )
    request.addfinalizer(fin)


@pytest.fixture()
def remove_dummy_template(request):
    """
    Fixture for test_18 - used as teardown
    """
    def fin():
        """
        Remove dummy template
        """
        ll_templates.remove_template(True, conf.TEMPLATE_LIST[1])
    request.addfinalizer(fin)


@pytest.fixture()
def supply_dummy_template(request, remove_dummy_template):
    """
    Fixture for test_16, test_20 - used as setup
    """
    assert ll_templates.createTemplate(
        True, vm=conf.BASE_VM_2, name=conf.TEMPLATE_LIST[1]
    )


@pytest.fixture()
def supply_dummy_dc_cluster(request):
    """
    Fixture for test_17 - includes setup and teardown
    """
    def fin1():
        """
        Delete dummy DC and cluster
        """
        ll_dcs.remove_datacenter(True, conf.DUMMY_DC)
        ll_clusters.removeCluster(True, conf.DUMMY_CLUSTER)
    request.addfinalizer(fin1)
    assert ll_dcs.addDataCenter(
        True, name=conf.DUMMY_DC, local=False, version=conf.COMP_VERSION
    )
    assert ll_clusters.addCluster(
        True, name=conf.DUMMY_CLUSTER, version=conf.COMP_VERSION,
        data_center=conf.DUMMY_DC, cpu=conf.CPU_NAME
    )


@pytest.fixture(scope="module", autouse=True)
def init_module(request):
    """
    Fixture for the template test module, includes setup and teardwon steps.
    """
    def fin1():
        """
        Removes user1 from engine
        """
        ll_users.removeUser(True, conf.USER, conf.USER_DOMAIN)

    def fin2():
        """
        Removes templates from engine
        """
        remove_base_templates()

    def fin3():
        """
        Removes base vms from engine
        """
        remove_base_vms()

    def fin4():
        """
        Removes created by template with no disk from engine
        """
        remove_no_disk_vms()

    conf.TEMPLATE_LIST = conf.TEMPLATE_NAMES.keys()
    conf.TEMPLATE_LIST.sort()
    conf.NON_MASTER_DOMAIN = ll_sds.findNonMasterStorageDomains(
        True, conf.DC_NAME[0]
    )[1]['nonMasterDomains'][0]
    request.addfinalizer(fin1)
    request.addfinalizer(fin2)
    request.addfinalizer(fin3)
    request.addfinalizer(fin4)
    create_base_vms()
    assert ll_users.addExternalUser(
        True, user_name=conf.USER, domain=conf.USER_DOMAIN
    )
