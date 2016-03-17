
"""
Import Export Init
https://polarion.engineering.redhat.com/polarion/#/project/RHEVM3/wiki/
Network/3_1_Network_Export_ImportVM
"""
import helper
import logging
import config as conf
from rhevmtests import networking
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import rhevmtests.networking.helper as networking_helper
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storagedomains

logger = logging.getLogger("Import_Export_Init")


def setup_package():
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


def teardown_package():
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
