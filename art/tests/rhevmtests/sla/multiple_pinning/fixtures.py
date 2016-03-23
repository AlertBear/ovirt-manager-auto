"""
Multiple pinning fixtures
"""
import logging

import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import config as conf
import helpers as pinning_helpers
from rhevmtests.sla.fixtures import *  # flake8: noqa


logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def update_class_cpu_pinning(request):
    """
    1) Update CPU pinning class variable
    """
    vcpu_pinning = [
        {"0": "%s" % pinning_helpers.get_the_same_cpus_from_resources()}
    ]
    request.node.cls.vms_to_params[
        conf.VM_NAME[0]
    ][conf.VM_CPU_PINNING] = vcpu_pinning


@pytest.fixture(scope="class")
def numa_pinning(request):
    """
    1) Add NUMA node to VM
    2) Pin VNUMA node to PNUMA
    """
    def fin():
        """
        1) Remove NUMA node from VM
        """
        ll_vms.remove_numa_node_from_vm(
            vm_name=conf.VM_NAME[0], numa_node_index=0
        )
    request.addfinalizer(fin)

    pinning_helpers.add_one_numa_node_to_vm()


@pytest.fixture(scope="class")
def attach_host_device(request):
    """
    1) Attach host device to VM
    """
    host_device_name = ll_hosts.get_host_devices(
        host_name=conf.HOSTS[0]
    )[0].get_name()

    def fin():
        """
        1) Remove host device from VM
        """
        if ll_vms.get_vm_host_devices(vm_name=conf.VM_NAME[0]):
            ll_vms.remove_vm_host_device(
                vm_name=conf.VM_NAME[0], device_name=host_device_name
            )
    request.addfinalizer(fin)

    assert ll_vms.add_vm_host_device(
        vm_name=conf.VM_NAME[0],
        device_name=host_device_name,
        host_name=conf.HOSTS[0]
    )


@pytest.fixture(scope="class")
def create_vm_for_export_and_template_checks(request):
    """
    1) Create VM that pinned to two hosts
    """
    def fin():
        """
        1) Remove VM
        """
        ll_vms.safely_remove_vms([conf.VM_IMPORT_EXPORT_TEMPLATE])
    request.addfinalizer(fin)

    assert ll_vms.addVm(
        positive=True,
        name=conf.VM_IMPORT_EXPORT_TEMPLATE,
        cluster=conf.CLUSTER_NAME[0],
        template=conf.BLANK_TEMPlATE,
        placement_hosts=conf.HOSTS[:2]
    )


@pytest.fixture()
def export_vm(request):
    """
    1) Export VM
    """
    def fin():
        """
        1) Remove VM from export domain
        """
        ll_vms.remove_vm_from_export_domain(
            positive=True,
            vm=conf.VM_IMPORT_EXPORT_TEMPLATE,
            datacenter=conf.DC_NAME[0],
            export_storagedomain=conf.EXPORT_DOMAIN_NAME
        )
    request.addfinalizer(fin)

    assert ll_vms.exportVm(
        positive=True,
        vm=conf.VM_IMPORT_EXPORT_TEMPLATE,
        storagedomain=conf.EXPORT_DOMAIN_NAME
    )


@pytest.fixture()
def import_vm(request):
    """
    1) Import VM
    """
    def fin():
        """
        1) Remove imported VM
        """
        ll_vms.removeVm(positive=True, vm=conf.VM_IMPORTED)
    request.addfinalizer(fin)

    assert ll_vms.importVm(
        positive=True,
        vm=conf.VM_IMPORT_EXPORT_TEMPLATE,
        export_storagedomain=conf.EXPORT_DOMAIN_NAME,
        import_storagedomain=conf.STORAGE_NAME[0],
        cluster=conf.CLUSTER_NAME[0],
        name=conf.VM_IMPORTED
    )


@pytest.fixture()
def make_template_from_vm(request):
    """
    1) Make template from VM
    """
    def fin():
        """
        1) Remove template
        """
        ll_templates.removeTemplate(
            positive=True, template=conf.VM_IMPORT_EXPORT_TEMPLATE
        )
    request.addfinalizer(fin)

    assert ll_templates.createTemplate(
        positive=True,
        vm=conf.VM_IMPORT_EXPORT_TEMPLATE,
        name=conf.VM_IMPORT_EXPORT_TEMPLATE,
        cluster=conf.CLUSTER_NAME[0],
        storagedomain=conf.STORAGE_NAME[0]
    )


@pytest.fixture()
def make_vm_from_template(request):
    """
    1) Make VM from template
    """
    def fin():
        """
        1) Remove VM
        """
        ll_vms.removeVm(positive=True, vm=conf.VM_FROM_TEMPLATE)
    request.addfinalizer(fin)

    assert ll_vms.addVm(
        positive=True,
        cluster=conf.CLUSTER_NAME[0],
        name=conf.VM_FROM_TEMPLATE,
        template=conf.VM_IMPORT_EXPORT_TEMPLATE
    )
