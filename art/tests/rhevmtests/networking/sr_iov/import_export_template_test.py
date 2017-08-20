#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
SR_IOV cases with import/export and templates
"""

import pytest

from art.rhevm_api.tests_lib.low_level import (
    templates as ll_templates,
    vms as ll_vms,
)
import art.rhevm_api.tests_lib.high_level.vms as hl_vms
import config as sriov_conf
import rhevmtests.networking.config as conf
import rhevmtests.helpers as global_helper
from art.test_handler.tools import bz, polarion
from fixtures import (  # noqa: F401
    create_template_fixture,
    reset_host_sriov_params,
    remove_vm_fixture,
    create_vm_fixture,
    add_vnics_to_vm,
    set_num_of_vfs,
    sr_iov_init
)
from art.unittest_lib import (
    tier2,
    NetworkTest,
    testflow,
)
from rhevmtests.fixtures import start_vm
from rhevmtests.networking.fixtures import (  # noqa: F401
    create_and_attach_networks,
    clean_host_interfaces,
    remove_all_networks,
    update_vnic_profiles
)

pytestmark = pytest.mark.skipif(
    conf.NO_FULL_SRIOV_SUPPORT,
    reason=conf.NO_FULL_SRIOV_SUPPORT_SKIP_MSG
)


@pytest.fixture(scope="class", autouse=True)
def prepare_setup_import_export(request):
    """
    Prepare networks for Import/Export cases
    """

    result = list()
    dc = request.node.cls.dc
    vm = request.node.cls.vm
    export_domain = request.node.cls.export_domain
    export_template_name = request.node.cls.export_template_name

    def fin3():
        """
        Check if one of the finalizers failed.
        """
        global_helper.raise_if_false_in_list(results=result)
    request.addfinalizer(fin3)

    def fin2():
        """
        Remove template from export domain
        """
        testflow.teardown(
            "Remove template %s from export domain", export_template_name
        )
        result.append(
            (
                ll_templates.removeTemplateFromExportDomain(
                    positive=True, template=export_template_name,
                    export_storagedomain=export_domain
                ), "fin4: ll_templates.removeTemplateFromExportDomain"
            )
        )
    request.addfinalizer(fin2)

    def fin1():
        """
        Remove VM from export domain
        """
        testflow.teardown("Remove VM %s from export domain", vm)
        result.append(
            (
                ll_vms.remove_vm_from_export_domain(
                    positive=True, vm=vm, datacenter=dc,
                    export_storagedomain=export_domain
                ), "fin2: ll_vms.remove_vm_from_export_domain"
            )
        )
    request.addfinalizer(fin1)


@pytest.mark.usefixtures(
    sr_iov_init.__name__,
    create_and_attach_networks.__name__,
    update_vnic_profiles.__name__,
    create_vm_fixture.__name__,
    add_vnics_to_vm.__name__,
    create_template_fixture.__name__,
    remove_vm_fixture.__name__,
    set_num_of_vfs.__name__,
    reset_host_sriov_params.__name__,
    clean_host_interfaces.__name__,
    prepare_setup_import_export.__name__,
    start_vm.__name__
)
class TestSriovImportExport01(NetworkTest):
    """
    Cases for Import/Export with VM and VFs
    """

    # General
    dc = conf.DC_0
    cluster = conf.CL_0
    vm_nic_1 = sriov_conf.TEMPLATE_TEST_VNICS[1][0]
    vm_nic_2 = sriov_conf.TEMPLATE_TEST_VNICS[1][1]
    net_1 = sriov_conf.IMPORT_EXPORT_NETS[1][0]
    net_2 = sriov_conf.IMPORT_EXPORT_NETS[1][1]
    import_vm_name = "sriov_import_vm"
    import_template_name = "sriov_import_template"
    vm_from_template = "sriov_from_template"

    # prepare_setup_import_export
    net_list = [net_1, net_2]
    vm = "sriov_export_vm"
    vm_nic_list = [vm_nic_1, vm_nic_2]
    export_template_name = "sriov_export_template"
    templates_list = [import_template_name, export_template_name]
    export_domain = conf.EXPORT_DOMAIN_NAME
    vms_list = [import_vm_name, vm, vm_from_template]

    # clean_host_interfaces
    hosts_nets_nic_dict = {
        0: {}
    }

    # stop VM
    vms_to_stop = vms_list

    # create_and_attach_networks params
    create_networks = {
        "1": {
            "data_center": dc,
            "clusters": [cluster],
            "networks": sriov_conf.CASE_01_IMPORT_EXPORT_NETS
        }
    }

    # remove_all_networks params
    remove_dcs_networks = [dc]

    # update_vnic_profiles params
    update_vnics_profiles = {
        net_1: {
            "pass_through": True,
            "network_filter": "None"
        },
        net_2: {
            "pass_through": True,
            "network_filter": "None"
        },
    }

    # add_vnics_to_vm
    pass_through_vnic = [True]
    profiles = net_list
    nets = net_list
    nics = vm_nic_list
    vms = [vm]
    remove_vnics = False

    # set_num_of_vfs
    num_of_vfs = 4

    @tier2
    @polarion("RHEVM3-10676")
    def test_01_export_vm_with_vf(self):
        """
        Export VM with VF to export domain
        """
        testflow.step("Export VM with VF to export domain")
        assert ll_vms.exportVm(
            positive=True, vm=self.vm, storagedomain=self.export_domain
        )

    @tier2
    @bz({"1479484": {}})
    @polarion("RHEVM3-14733")
    def test_02_import_vm_with_vf(self):
        """
        Import VM with VF from export domain
        Start VM
        """
        testflow.step("Import VM with VF from export domain")
        assert ll_vms.importVm(
            positive=True, vm=self.vm, export_storagedomain=self.export_domain,
            import_storagedomain=sriov_conf.SD_NAME, cluster=self.cluster,
            name=self.import_vm_name
        )
        testflow.step("Start VM")
        assert hl_vms.run_vm_once_specific_host(
            vm=self.import_vm_name, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        )

    @tier2
    @polarion("RHEVM3-14734")
    def test_03_export_template_with_vf(self):
        """
        Export template with VF to export domain
        """
        testflow.step("Export template with VF to export domain")
        assert ll_templates.exportTemplate(
            positive=True, template=self.export_template_name,
            storagedomain=self.export_domain
        )

    @tier2
    @bz({"1479484": {}})
    @polarion("RHEVM3-10409")
    def test_04_import_template_with_vf(self):
        """
        Import template with VF from export domain
        Create VM from template
        Start VM
        """
        testflow.step("Import template with VF from export domain")
        assert ll_templates.import_template(
            positive=True, template=self.export_template_name,
            source_storage_domain=self.export_domain,
            destination_storage_domain=sriov_conf.SD_NAME,
            cluster=self.cluster, name=self.import_template_name
        )
        testflow.step("Create VM from template")
        assert ll_vms.createVm(
            positive=True, vmName=self.vm_from_template, vmDescription="",
            cluster=self.cluster, storageDomainName=sriov_conf.SD_NAME,
            provisioned_size=conf.VM_DISK_SIZE,
            template=self.import_template_name
        )
        testflow.step("Start VM")
        assert hl_vms.run_vm_once_specific_host(
            vm=self.vm_from_template, host=conf.HOST_0_NAME,
            wait_for_up_status=True
        )
