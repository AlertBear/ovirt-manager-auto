#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Testing Import/Export feature.
1 DC, 1 Cluster, 1 Hosts, 1 export domain, 1 VM and 1 templates will be
created for testing.
"""
import helper
import logging
import config as conf
from rhevmtests import networking
from art.unittest_lib import attr, NetworkTest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as networking_helper
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
from art.test_handler.tools import polarion  # pylint: disable=E0611
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains

logger = logging.getLogger("Import_Export_Cases")


def setup_module():
    """
    Prepare environment
    Create a new vm (IE_VM)
    Create new template (IE_TEMPLATE)
    Attach bridged, MTU and VLAN networks to host
    Attach 4 NICs to new VM and Template
    Export IE_TEMPLATE and IE_VM to export domain
    Remove IE_TEMPLATE and IE_VM from setup
    """
    networking.network_cleanup()
    conf.HOST_0_NAME = conf.HOSTS[0]
    conf.SD_NAME = ll_storagedomains.getStorageDomainNamesForType(
        datacenter_name=conf.DC_0, storage_type=conf.STORAGE_TYPE
    )[0]

    if not ll_vms.createVm(
        positive=True, vmName=conf.IE_VM, vmDescription="",
        cluster=conf.CL_0, storageDomainName=conf.SD_NAME,
        size=conf.VM_DISK_SIZE
    ):
        raise conf.NET_EXCEPTION()

    if not hl_networks.createAndAttachNetworkSN(
        data_center=conf.DC_0, cluster=conf.CL_0,
        host=conf.VDS_HOSTS[0], network_dict=conf.local_dict, auto_nics=[0, 3]
    ):
        raise conf.NET_EXCEPTION()

    net_list = [conf.MGMT_BRIDGE] + conf.NETS[:3] + [None]
    helper.add_nics_to_vm(net_list=net_list)

    if not ll_templates.createTemplate(
        True, vm=conf.IE_VM, cluster=conf.CL_0, name=conf.IE_TEMPLATE
    ):
        raise conf.NET_EXCEPTION()

    if not ll_templates.exportTemplate(
        positive=True, template=conf.IE_TEMPLATE,
        storagedomain=conf.EXPORT_DOMAIN_NAME
    ):
        raise conf.NET_EXCEPTION()

    if not ll_vms.exportVm(
        positive=True, vm=conf.IE_VM,
        storagedomain=conf.EXPORT_DOMAIN_NAME
    ):
        raise conf.NET_EXCEPTION()

    if not ll_vms.removeVm(positive=True, vm=conf.IE_VM, stopVM="true"):
        raise conf.NET_EXCEPTION()

    if not ll_templates.removeTemplate(
        positive=True, template=conf.IE_TEMPLATE
    ):
        raise conf.NET_EXCEPTION()


def teardown_module():
    """
    Cleans the environment
    Remove IE_VM and IE_TEMPLATE from export domain
    Remove networks from setup
    """
    ll_vms.remove_vm_from_export_domain(
        positive=True, vm=conf.IE_VM, datacenter=conf.DC_0,
        export_storagedomain=conf.EXPORT_DOMAIN_NAME
    )

    ll_templates.removeTemplateFromExportDomain(
        positive=True, template=conf.IE_TEMPLATE, datacenter=conf.DC_0,
        export_storagedomain=conf.EXPORT_DOMAIN_NAME
    )

    networking_helper.remove_networks_from_setup(hosts=conf.HOST_0_NAME)


@attr(tier=2)
class TestIECase01(NetworkTest):
    """
    Check that VM could be imported with all the networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True
    vms_list = [conf.IE_VM, conf.IMP_MORE_THAN_ONCE_VM]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]

    @classmethod
    def setup_class(cls):
        """
        1) Import VM from export domain
        2) Import the same VM more than once
        """
        for name in (None, cls.vms_list[1]):
            if not ll_vms.importVm(
                positive=True, vm=conf.IE_VM,
                export_storagedomain=conf.EXPORT_DOMAIN_NAME,
                import_storagedomain=conf.SD_NAME, cluster=conf.CL_0,
                name=name
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3760")
    def test_01_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles
        """
        helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, vm=self.vms_list[0]
        )

    @polarion("RHEVM3-3769")
    def test_02_import_vm_more_than_once(self):
        """
        Check that VM imported more than once keeps all it's VNIC profiles
        """
        helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, vm=self.vms_list[1]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs
        """
        ll_vms.safely_remove_vms(vms=cls.vms_list)


@attr(tier=2)
class TestIECase02(NetworkTest):
    """
    Check that Template could be imported with all the networks
    Check that Template imported more than once keeps all it's network
    configuration
    """
    __test__ = True
    template_list = [conf.IMP_MORE_THAN_ONCE_TEMP, conf.IE_TEMPLATE]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]

    @classmethod
    def setup_class(cls):
        """
        1) Import template form export domain
        2) Import the same Template more than once
        """
        for name in (None, cls.template_list[0]):
            if not ll_templates.import_template(
                positive=True, template=conf.IE_TEMPLATE,
                source_storage_domain=conf.EXPORT_DOMAIN_NAME,
                destination_storage_domain=conf.SD_NAME,
                cluster=conf.CL_0, name=name
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3766")
    def test_01_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles
        """
        helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, template=self.template_list[1]
        )

    @polarion("RHEVM3-3764")
    def test_02_import_more_than_once(self):
        """
        Check that Template imported more than once keeps all its VNIC
        profiles
        """
        helper.check_imported_vm_or_templates(
            net1=self.net1, net2=self.net2, template=self.template_list[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove templates
        """
        if not ll_templates.removeTemplates(
            positive=True, templates=cls.template_list
        ):
            logger.error(
                "Couldn't remove imported Templates %s", cls.template_list
            )


@attr(tier=2)
class TestIECase03(NetworkTest):
    """
    Check for the VM and template:
    1) Check that the VNIC that had net1 and net2 on VM before import
       action, has an empty VNIC for that VNIC profiles after import completed
    2) Check that the Template that had net1 and net2 on VM before import
       action, has an empty VNIC for that VNIC profiles after import completed
    3) Start VM should fail when one of the networks attached to it doesn't
       reside on any host in the setup.
       Start VM after removing network that doesn't reside on any host
       in the setup should succeed.
    4) Create VM from imported template should succeed,
       Start VM should fail if nic4 with net3 exist on VM,
       Start VM should succeed after remove of nic 4 from VM.
    """
    __test__ = True
    vms_list = [conf.IE_VM, "IE_VM_2"]
    nic_name = conf.NIC_NAME[3]
    net1 = conf.NETS[0]
    net2 = conf.NETS[1]
    net_list = conf.NETS

    @classmethod
    def setup_class(cls):
        """
        Remove net1 and net2 from setup
        Remove network net3 from the host
        Import VM and template with net1, net2 and net3 to the setup you just
        removed the networks from
        net1 and net2 should be empty.
        net3 should be with network.
        """
        if not hl_host_network.remove_networks_from_host(
            host_name=conf.HOSTS[0], networks=cls.net_list[:3]
        ):
            raise conf.NET_EXCEPTION()

        if not hl_networks.remove_networks(
            positive=True, networks=cls.net_list[:2]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_templates.import_template(
            positive=True, template=conf.IE_TEMPLATE,
            source_storage_domain=conf.EXPORT_DOMAIN_NAME,
            destination_storage_domain=conf.SD_NAME,
            cluster=conf.CL_0
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.importVm(
            positive=True, vm=cls.vms_list[0],
            export_storagedomain=conf.EXPORT_DOMAIN_NAME,
            import_storagedomain=conf.SD_NAME, cluster=conf.CL_0
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3771")
    def test_01_import_vm_vnic_profiles(self):
        """
        Check that the VNIC that had net1 and net2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        helper.check_imported_vm_or_templates(
            net1=None, net2=None, vm=self.vms_list[0]
        )

    @polarion("RHEVM3-3765")
    def test_02_import_temp_vnic_profiles(self):
        """
        Check that the Template that had net1 and net2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        helper.check_imported_vm_or_templates(
            net1=None, net2=None, template=conf.IE_TEMPLATE
        )

    @polarion("RHEVM3-3761")
    def test_03_start_vm(self):
        """
        1) Negative - Start VM when one of the networks attached to it doesn't
        reside on any host in the setup
        2) Positive - Start VM after removing network that doesn't reside on
        any host in the setup
        """

        if not ll_vms.startVm(positive=False, vm=self.vms_list[0]):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(
            positive=True, vm=self.vms_list[0], nic=self.nic_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.startVm(
            positive=True, vm=self.vms_list[0], wait_for_status="up"
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-3772")
    def test_04_start_vm_from_template(self):
        """
        1) Create VM from imported template
        2) Negative - Start VM, created from template when one of the
        networks, attached to it doesn't reside on any host in the setup
        3) Positive - Start VM, created from template after removing network
        that doesn't reside on any host in the setup
        """

        if not ll_vms.addVm(
            positive=True, name=self.vms_list[1], cluster=conf.CL_0,
            template=conf.IE_TEMPLATE, display_type=conf.DISPLAY_TYPE
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.startVm(positive=False, vm=self.vms_list[1]):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(
            positive=True, vm=self.vms_list[1], nic=self.nic_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.startVm(
            positive=True, vm=self.vms_list[1], wait_for_status="up"
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VM imported from Export domain and VM created from template
        2) Remove Template imported from Export domain and VM created from
        that Template
        3) Put the networks net1, net2 and net3 back to the DC/Cluster/Host
        """
        dc_dict1 = {
            cls.net1: {
                "nic": 1,
                "required": "false"
            },
            cls.net2: {
                "mtu": conf.MTU[0],
                "nic": 2,
                "required": "false"
            }
        }

        ll_vms.safely_remove_vms(vms=cls.vms_list)
        ll_templates.removeTemplate(positive=True, template=conf.IE_TEMPLATE)
        networking_helper.prepare_networks_on_setup(
            networks_dict=dc_dict1, dc=conf.DC_0,
            cluster=conf.CL_0
        )

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS[0], network_dict=conf.local_dict,
            auto_nics=[0, 3]
        ):
            raise conf.NET_EXCEPTION()
