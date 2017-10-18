#! /usr/bin/python
# -*- coding: utf-8 -*-

import time
import pytest
from art.rhevm_api.utils import test_utils
from art.rhevm_api.tests_lib.low_level import (
    disks as ll_disks,
    templates as ll_templates,
    vms as ll_vms,
    storagedomains as ll_sd,
)
from art.rhevm_api.tests_lib.high_level import (
    disks as hl_disks,
    vms as hl_vms
)
import rhevmtests.helpers as gen_helper
import rhevmtests.virt.helper as helper
import config
from art.unittest_lib import testflow


class RegVmBase(object):
    """
    Class reg vm base
    """
    master_domain, export_domain, non_master_domain = (
        helper.get_storage_domains()
    )

    @classmethod
    def remove_vm_from_storage_domain(cls, vm_name):
        """
        Remove the VM from export storage

        :param vm_name: name of the vm
        :type vm_name: str
        """

        if ll_vms.is_vm_exists_in_export_domain(
            vm_name, cls.export_domain
        ):
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

    def fin():
        testflow.teardown("Remove all vms in list: %s", config.REG_VMS_LIST)
        ll_vms.safely_remove_vms(config.REG_VMS_LIST)

    request.addfinalizer(fin)


@pytest.fixture()
def add_vm_fixture(request):
    """
    Create vm, remove it in fin
    vm name is taken from class member
    """

    vm_name = request.cls.vm_name
    add_disk = getattr(request.cls, "add_disk", False)

    def fin():
        testflow.teardown("Remove vm %s", vm_name)
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    testflow.setup("Create vm %s with disk %s", vm_name, str(add_disk))
    assert helper.create_base_vm(vm_name=vm_name, add_disk=add_disk)


@pytest.fixture()
def start_stop_fixture(request):
    """
    Start vm
    """

    vm_name = getattr(request.cls, "vm_name", config.BASE_VM_VIRT)

    def fin():
        """
        Stop vm
        """
        testflow.teardown("Stop vm %s", vm_name)
        assert ll_vms.stop_vms_safely(vms_list=[vm_name])

    request.addfinalizer(fin)

    testflow.setup("Start vm %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_ip=False,
        wait_for_status=config.VM_UP
    )


@pytest.fixture()
def stateless_vm_test_fixture(request):
    """
    Fixture for stateless test:
    1. Create stateless vm
    2. Remove it in fin
    """
    vm_name = request.cls.vm_name
    vm_parameters = request.cls.vm_parameters

    def fin():
        testflow.teardown("Remove stateless vm %s", vm_name)
        RegVmBase.remove_stateless_vm(vm_name)

    request.addfinalizer(fin)

    testflow.setup(
        "Create vm %s from template %s", vm_name, config.template_name
    )
    assert helper.create_vm_from_template(
        vm_name=vm_name,
        template=config.template_name,
        vm_parameters=vm_parameters
    )
    testflow.setup("Start vm %s", vm_name)
    assert ll_vms.startVm(positive=True, vm=vm_name)


@pytest.fixture(scope="class")
def create_vm_and_template_with_small_disk(request):
    """
    1. Create base vm with 1 GB disk
    2. Create template (base_template)
    3. Create new vm from base_template
    """
    base_vm = config.BASE_VM
    base_template = config.BASE_TEMPLATE
    cluster_name = config.CLUSTER_NAME[0]
    vm_from_template = config.VM_FROM_BASE_TEMPLATE
    test_vm_name = request.node.cls.vm_name
    vm_parameters = request.node.cls.vm_parameters

    def fin():
        """
        Remove vms and template
        """
        vms_list = [base_vm, test_vm_name, vm_from_template]
        testflow.teardown("Remove vms %s", vms_list)
        assert ll_vms.safely_remove_vms(vms=vms_list)
        testflow.teardown("Remove template %s", base_template)
        assert ll_templates.remove_template(True, template=base_template)

    request.addfinalizer(fin)

    testflow.setup("Create vm %s with disk %s", base_vm, str(True))
    assert helper.create_base_vm(vm_name=base_vm, add_disk=True)
    testflow.setup("create template %s from vm %s", base_template, base_vm)
    assert ll_templates.createTemplate(
        positive=True, vm=base_vm, name=base_template,
        cluster=cluster_name
    )
    testflow.setup(
        "Create new vm %s from template %s", vm_from_template, base_template
    )
    assert helper.create_vm_from_template(
        vm_name=vm_from_template,
        template=base_template,
        vm_parameters=vm_parameters
    )


@pytest.fixture()
def remove_vm_from_export_domain(request):
    """
    Fixture to remove vm from export domain
    """
    vm_name = request.cls.vm_name

    def fin():
        """
        Remove vm from export domain
        """
        testflow.teardown("Remove vm %s from export domain", vm_name)
        RegVmBase.remove_vm_from_storage_domain(vm_name=vm_name)

    request.addfinalizer(fin)


@pytest.fixture()
def test_snapshot_and_import_export_fixture(
    request, remove_vm_from_export_domain
):
    """
    Fixture for snapshot and import export tests:
    1. Create test vm
    2. Remove vms from export domain
    3. fin: Remove vm
    """
    vm_name = request.cls.vm_name

    def fin():
        """
        Remove vm
        """
        testflow.teardown("Remove vm %s", vm_name)
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    testflow.setup("Create vm %s ", vm_name)
    assert helper.create_base_vm(vm_name=vm_name, add_disk=True)
    export_domain_vms = ll_vms.get_vms_from_storage_domain(
        RegVmBase.export_domain
    )
    testflow.setup("Remove vms from export domain")
    for vm in export_domain_vms:
        RegVmBase.remove_vm_from_storage_domain(vm_name=vm)


@pytest.fixture(scope="class")
def add_vm_from_template_fixture(request):
    """
    Create vm from template with parameters
    """

    vm_name = request.cls.base_vm_name
    cluster_name = request.cls.cluster_name
    template_name = request.cls.template_name
    vm_parameters = getattr(
        request.cls, "vm_parameters", config.DEFAULT_VM_PARAMETERS
    )

    def fin():
        """
        Stop and remove vm
        """
        testflow.teardown("Stop and remove vm %s ", vm_name)
        assert ll_vms.safely_remove_vms([vm_name])

    request.addfinalizer(fin)

    testflow.setup("Create vm %s from template", vm_name)
    assert helper.create_vm_from_template(
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

    def fin():
        testflow.teardown("remove vms %s", vm_names.values)
        assert ll_vms.safely_remove_vms(vm_names.values())

    request.addfinalizer(fin)

    testflow.setup("Create vms with different display types %s", vm_names.keys)
    for display_type, vm_name in vm_names.iteritems():
        assert helper.create_base_vm(
            vm_name=vm_name,
            display_type=display_type,
            add_disk=True
        )
        assert ll_vms.startVm(True, vm_name)


@pytest.fixture()
def add_vm_with_disks(request):
    """
    Create VM from GE template and add different disks.
    """

    base_vm_name = config.BASE_VM_VIRT
    cow_disk = config.DISK_FORMAT_COW
    disk_interfaces = config.INTERFACE_VIRTIO

    def fin():
        """
        Remove vm
        """
        vms = [base_vm_name, config.TEST_CLONE_WITH_2_DISKS]
        testflow.teardown("Remove VMs: %s", vms)
        assert ll_vms.safely_remove_vms(vms=vms)

    request.addfinalizer(fin)
    master_domain = (
        ll_sd.get_master_storage_domain_name(datacenter_name=config.DC_NAME[0])
    )
    testflow.setup("Create VM %s from GE template", base_vm_name)
    assert helper.create_vm_from_template(vm_name=base_vm_name)
    first_disk_id = ll_disks.getObjDisks(
        name=base_vm_name, get_href=False
    )[0].id
    assert ll_disks.updateDisk(
        positive=True,
        vmName=base_vm_name,
        id=first_disk_id,
        bootable=True
    )
    testflow.setup("add 2 more disks on master storage domain")
    for x in xrange(0, 2):
        assert ll_vms.addDisk(
            positive=True,
            vm=base_vm_name,
            provisioned_size=config.GB,
            storagedomain=master_domain,
            interface=disk_interfaces,
            format=cow_disk
        ), "Failed to add disk to vm on master domain"


@pytest.fixture(scope="class")
def create_file_on_vm(request):
    """
    Start VM, Create empty file on vm, Stop VM
    """
    vm_name = request.cls.base_vm_name

    testflow.setup("Start VM %s", vm_name)
    ll_vms.start_vms(
        vm_list=[vm_name],
        wait_for_ip=True,
        wait_for_status=config.VM_UP
    )
    vm_resource = gen_helper.get_vm_resource(vm_name)
    testflow.setup("Creating a file in vm: %s", vm_name)
    helper.create_file_in_vm(vm_name, vm_resource, path='/home/')
    helper.check_if_file_exist(True, vm_name, vm_resource, path='/home/')
    assert vm_resource.run_command(['sync'])[0] == 0
    testflow.setup("Stop VM %s", vm_name)
    ll_vms.stop_vms_safely(vms_list=[vm_name])


@pytest.fixture()
def remove_locked_vm(request):
    """
    Remove locked VM
    """
    vm_name = request.cls.base_vm_name

    def fin():
        testflow.teardown("Remove locked VM")
        assert ll_vms.remove_locked_vm(
            vm_name=vm_name,
            vdc=config.VDC_HOST,
            vdc_pass=config.VDC_ROOT_PASSWORD
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def unlock_disks(request):
    """
    Update locked disk status to 'OK'
    """
    def fin1():
        testflow.teardown("unlock disks")
        hl_disks.unlock_disks(engine=config.ENGINE)
        test_utils.wait_for_tasks(config.ENGINE, config.DC_NAME[0])
        time.sleep(20)
        testflow.teardown("Check there are no disks in locked status")
        assert hl_disks.check_no_locked_disks(engine=config.ENGINE)

    def fin2():
        testflow.teardown("Remove vms")
        for vm_name in [config.BASE_VM_VIRT, config.CLONE_VM_TEST]:
            assert ll_vms.remove_locked_vm(
                vm_name=vm_name,
                vdc=config.VDC_HOST,
                vdc_pass=config.VDC_ROOT_PASSWORD
            )

    request.addfinalizer(fin2)
    request.addfinalizer(fin1)


@pytest.fixture()
def change_cpu_limitations(request):
    """
    Change the engine cpu limitation
    """

    if request.getfixturevalue("change_limitation"):
        comp_version = request.getfixturevalue("comp_version")
        if comp_version == config.COMP_VERSION:
            value = config.VCPU_FROM_41_AND_UP
        elif comp_version == "4.0":
            value = config.VCPU_4_0

        def fin():
            testflow.teardown("Return CPU limitations to default")
            param = "MaxNumOfVmCpus=%s" % value
            assert config.ENGINE.engine_config(
                action='set', param=param, version=comp_version
            ).get('results'), "Failed to configure %s" % param

        request.addfinalizer(fin)

        testflow.setup("Change CPU limitations to 10")
        param = "MaxNumOfVmCpus=10"
        assert config.ENGINE.engine_config(
            action='set', param=param, version=comp_version
        ).get('results'), "Failed to configure %s" % param


@pytest.fixture()
def default_cpu_settings(request):
    """
    cleanup for vcpu test cases
    """
    comp_version = request.getfixturevalue('comp_version')
    vm_name = (
        config.VM_NAME[0] if comp_version is config.COMP_VERSION
        else config.VCPU_4_0_VM
    )

    def fin():
        testflow.teardown("Update VM %s cpu to 1", vm_name)
        assert ll_vms.updateVm(
            positive=True,
            vm=vm_name,
            cpu_cores=1,
            cpu_socket=1,
            cpu_threads=1
        )
    request.addfinalizer(fin)


@pytest.fixture(scope="class")
def create_vm_for_vcpu(request):
    """
    Create VM for Vcpu test,
    The test requires a new vm in 4.0 cluster
    """
    def fin():
        testflow.teardown("Remove VM %s", config.VCPU_4_0_VM)
        assert ll_vms.safely_remove_vms([config.VCPU_4_0_VM])
    request.addfinalizer(fin)

    testflow.setup(
        "Create VM %s for on cluster %s",
        config.VCPU_4_0_VM, config.VCPU_4_0_CLUSTER
    )
    assert ll_vms.addVm(
        positive=True,
        name=config.VCPU_4_0_VM,
        cluster=config.VCPU_4_0_CLUSTER,
        os_type=config.VM_OS_TYPE,
        display_type=config.VM_DISPLAY_TYPE,

    )
