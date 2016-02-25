"""
Testing Import/Export feature.
2 DC, 2 Cluster, 2 Hosts, 1 export domain, 2 VM and 2 templates will be
created for testing.
"""
import logging
from art.unittest_lib import attr
from rhevmtests.networking import config
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import NetworkTest as TestCase
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
from art.test_handler.exceptions import NetworkException
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.low_level.storagedomains as ll_storage
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("Import_Export_Cases")

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=2)
class TestIECase01(TestCase):
    """
    Check that VM could be imported with all the networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Import VM from same DC version
        2) Import the same VM more than once
        """
        logger.info(
            "Import VM from Export Domain"
            "Import the same VM more than once"
        )
        sd_name = ll_storage.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE
        )[0]
        for name in (None, config.IMP_MORE_THAN_ONCE_VM):
            log_vm = name if name is not None else config.IE_VM
            if not ll_vms.importVm(
                positive=True, vm=config.IE_VM,
                export_storagedomain=config.EXPORT_DOMAIN_NAME,
                import_storagedomain=sd_name,
                cluster=config.CLUSTER_NAME[0], name=name
            ):
                raise NetworkException(
                    "Cannot import %s created in the same DC version" % log_vm
                )

    @polarion("RHEVM3-3760")
    def test_01_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles from the same
        DC version
        """
        logger.info(
            "Check VM NICs VNIC profiles for VM imported from same DC version"
        )
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], config.NETWORKS[0]),
            (config.NIC_NAME[2], config.NETWORKS[1]),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_vms.check_vnic_on_vm_nic(
                vm=config.IE_VM, nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for VM" %
                    (vnic, nic)
                )

    @polarion("RHEVM3-3769")
    def test_02_import_vm_more_than_once(self):
        """
        Check that VM imported more than once keeps all it's VNIC profiles
        """
        logger.info(
            "Check VM NICs VNIC profiles for VM imported more than once"
        )
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], config.NETWORKS[0]),
            (config.NIC_NAME[2], config.NETWORKS[1]),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_vms.check_vnic_on_vm_nic(
                    vm=config.IMP_MORE_THAN_ONCE_VM, nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for VM" %
                    (vnic, nic)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs imported from Export domain
        """
        for vm in (config.IE_VM, config.IMP_MORE_THAN_ONCE_VM):
            if not ll_vms.removeVm(positive=True, vm=vm):
                logger.error("Couldn't remove imported VM %s", vm)


@attr(tier=2)
class TestIECase02(TestCase):
    """
    Check that Template created in the same DC version could be imported with
    all the networks
    Check that Template imported more than once keeps all it's network
    configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Import template form Export Domain
        2) Import the same Template more than once
        """
        logger.info(
            "Import Template from Export Domain"
            "Import the same template more than once"
        )
        sd_name = ll_storage.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE
        )[0]
        for name in (None, config.IMP_MORE_THAN_ONCE_TEMP):
            log_temp = name if name is not None else config.IE_TEMPLATE
            if not ll_templates.import_template(
                positive=True, template=config.IE_TEMPLATE,
                source_storage_domain=config.EXPORT_DOMAIN_NAME,
                destination_storage_domain=sd_name,
                cluster=config.CLUSTER_NAME[0],
                name=name
            ):
                raise NetworkException(
                    "Cannot import %s created in lower version" % log_temp
                )

    @polarion("RHEVM3-3766")
    def test_01_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles from the
        same version DC
        """
        logger.info(
            "Check that NICs VNIC profiles for Template imported more than "
            "once are kept"
        )
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], config.NETWORKS[0]),
            (config.NIC_NAME[2], config.NETWORKS[1]),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_templates.check_vnic_on_template_nic(
                    template=config.IE_TEMPLATE, nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for Template" %
                    (vnic, nic)
                )

    @polarion("RHEVM3-3764")
    def test_02_import_more_than_once(self):
        """
        Check that Template imported more than once keeps all its VNIC
        profiles
        """
        logger.info(
            "Check that NICs VNIC profiles for Template imported more than "
            "once are kept"
        )
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], config.NETWORKS[0]),
            (config.NIC_NAME[2], config.NETWORKS[1]),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_templates.check_vnic_on_template_nic(
                template=config.IMP_MORE_THAN_ONCE_TEMP,
                nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for Template" %
                    (vnic, nic)
                )

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs imported from Export domain
        """
        logger.info("Removing imported templates")
        for template in (
            config.IMP_MORE_THAN_ONCE_TEMP, config.IE_TEMPLATE
        ):
            if not ll_templates.removeTemplate(
                positive=True, template=template
            ):
                logger.error("Couldn't remove imported Template %s", template)


@attr(tier=2)
class TestIECase03(TestCase):
    """
    Check for the VM and template:
    1) For network with VNIC profile, existing on the imported DC, Cluster
    and Host the VNIC is imported as is
    2) For network not existing in the DC, Cluster and Host, NIC with empty
    VNIC profile will appear for that Network
    3) For network with VNIC profile, existing only on the imported DC and
    Cluster the VNIC is imported as is
    4) Start of such VM should fail as there is no Host (3) that the sw3
    network resides on the imported setup
    5) After remove of the NIC in (4) the start of VM should succeed
    6) Creating of VM from template should succeed
    7) Start of VM should fail if nic4 with sw3 exist on VM
    8) Start of VM from template should succeed after remove of nic 4 from VM
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Remove sw1 and sw2 from setup
        Remove network sw3 from the host
        Import VM and template with sw1, sw2 and sw3 to the setup you just
        removed the networks from
        sw1 and sw2 should be empty.
        sw3 should be with network.
        """
        logger.info("Remove sw1 and sw2 from setup and sw3 from host only")
        if not hl_host_network.remove_networks_from_host(
            host_name=config.HOSTS[0], networks=config.NETWORKS[:3]
        ):
            raise NetworkException(
                "Failed to remove %s from %s" %
                (config.NETWORKS[:3], config.HOSTS[0])
            )

        if not hl_networks.remove_networks(
            positive=True, networks=config.NETWORKS[:2]
        ):
            raise NetworkException()

        logger.info(
            "Import template with sw1, sw2 and sw3 to DC when sw1 and sw2 "
            "don't exist there anymore and sw3 doesn't exist on the hosts "
            "of that DC"
        )
        sd_name = ll_storage.getStorageDomainNamesForType(
            datacenter_name=config.DC_NAME[0],
            storage_type=config.STORAGE_TYPE
        )[0]
        if not ll_templates.import_template(
            positive=True, template=config.IE_TEMPLATE,
            source_storage_domain=config.EXPORT_DOMAIN_NAME,
            destination_storage_domain=sd_name,
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException("Cannot import Template to the setup ")

        logger.info(
            "Import VM with sw1, sw2 and sw3 to DC when sw1 and sw2 don't "
            "exist there anymore and sw3 doesn't exist on the hosts of that DC"
        )
        if not ll_vms.importVm(
            positive=True, vm=config.IE_VM,
            export_storagedomain=config.EXPORT_DOMAIN_NAME,
            import_storagedomain=sd_name,
            cluster=config.CLUSTER_NAME[0]
        ):
            raise NetworkException("Cannot import VM to the setup")

    @polarion("RHEVM3-3771")
    def test_01_import_vm_vnic_profiles(self):
        """
        Check that the VNIC that had sw1 and sw2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        logger.info(
            "Check VM NICs VNIC profiles when one of them is missing in the "
            "target DC exist on the setup"
        )
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], None),
            (config.NIC_NAME[2], None),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_vms.check_vnic_on_vm_nic(
                vm=config.IE_VM, nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for VM" % (
                        vnic, nic)
                )

    @polarion("RHEVM3-3765")
    def test_02_import_temp_vnicp_rofiles(self):
        """
        Check that the Template that had sw1 and sw2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        logger.info("Check VM NICs VNIC profiles for Template")
        for (nic, vnic) in (
            (config.NIC_NAME[0], config.MGMT_BRIDGE),
            (config.NIC_NAME[1], None),
            (config.NIC_NAME[2], None),
            (config.NIC_NAME[3], config.NETWORKS[2])
        ):
            if not ll_templates.check_vnic_on_template_nic(
                template=config.IE_TEMPLATE, nic=nic, vnic=vnic
            ):
                raise NetworkException(
                    "No correct VNIC profile %s on VNIC %s for Template" %
                    (vnic, nic)
                )

    @polarion("RHEVM3-3761")
    def test_03_start_vm(self):
        """
        1) Negative - Start VM when one of the networks attached to it doesn't
        reside on any host in the setup
        2) Positive - Start VM after removing network that doesn't reside on
        any host in the setup
        """
        logger.info(
            "Try to start VM when one of the networks is not attached to any "
            "host in the setup"
        )
        if not ll_vms.startVm(positive=False, vm=config.IE_VM):
            raise NetworkException("Could start VM, when shouldn't")

        logger.info(
            "Remove NIC with sw3 network not attached to any Host in the setup"
        )
        if not ll_vms.removeNic(
            positive=True, vm=config.IE_VM, nic=config.NIC_NAME[3]
        ):
            raise NetworkException(
                "Couldn't remove nic from VM %s" % config.IE_VM
            )

        logger.info(
            "Start imported VM when all the networks of VM reside on one of "
            "the hosts in the setup"
        )
        if not ll_vms.startVm(
            positive=True, vm=config.IE_VM, wait_for_ip=True
        ):
            raise NetworkException(
                "Couldn't start VM %s, when should" % config.IE_VM
            )

    @polarion("RHEVM3-3772")
    def test_04_start_vm_from_template(self):
        """
        1) Create VM from imported template
        2) Negative - Start VM, created from template when one of the
        networks, attached to it doesn't reside on any host in the setup
        3) Positive - Start VM, created from template after removing network
        that doesn't reside on any host in the setup
        """
        logger.info(
            "Create VM %s from imported template %s", config.VM_NAME[1],
            config.IE_TEMPLATE
        )
        if not ll_vms.addVm(
            True, name="IE_VM_2", cluster=config.CLUSTER_NAME[0],
            template=config.IE_TEMPLATE,
            display_type=config.DISPLAY_TYPE
        ):
            raise NetworkException(
                "Cannot create VM %s from imported template %s" %
                ("IE_VM_2", config.IE_TEMPLATE)
            )

        logger.info(
            "Try to start VM, created from template when one of the networks "
            "is not attached to any host in the setup"
        )
        if not ll_vms.startVm(positive=False, vm="IE_VM_2"):
            raise NetworkException(
                "Could start VM %s, when shouldn't" % "IE_VM_2"
            )

        logger.info(
            "Remove NIC with sw3 network not attached to any Host in the setup"
        )
        if not ll_vms.removeNic(
            positive=True, vm="IE_VM_2", nic=config.NIC_NAME[3]
        ):
            raise NetworkException(
                "Couldn't remove nic from VM %s" % "IE_VM_2")

        logger.info(
            "Start VM, created from template when all the networks of VM "
            "reside on one of the hosts in the setup"
        )
        if not ll_vms.startVm(positive=True, vm="IE_VM_2", wait_for_ip=True):
            raise NetworkException(
                "Couldn't start VM %s, when should IE_VM_2"
            )

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VM imported from Export domain and VM created from template
        2) Remove Template imported from Export domain and VM created from
        that Template
        3) Put the networks sw1, sw2 and sw3 back to the DC/Cluster/Host
        """
        dc_dict1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"},
            config.NETWORKS[1]: {
                "mtu": config.MTU[0], "nic": 2, "required": "false"
            }
        }
        local_dict1 = {
            config.NETWORKS[0]: {"nic": 1, "required": "false"},
            config.NETWORKS[1]: {
                "mtu": config.MTU[0], "nic": 2, "required": "false"
            },
            config.NETWORKS[2]: {
                "vlan_id": config.VLAN_ID[0], "nic": 3, "required": "false"
            }
        }

        logger.info("Remove VMs from setup")
        for vm in (config.IE_VM, "IE_VM_2"):
            if not ll_vms.removeVm(positive=True, vm=vm, stopVM="true"):
                logger.error("Couldn't remove imported VM %s", vm)

        logger.info("Remove imported Template from setup")
        if not ll_templates.removeTemplate(
            positive=True, template=config.IE_TEMPLATE
        ):
            logger.error(
                "Couldn't remove imported Template %s", config.IE_TEMPLATE
            )

        logger.info("Add networks to the DC/Cluster")
        if not hl_networks.createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            network_dict=dc_dict1
        ):
            logger.error(
                "Cannot create and attach networks to the DC/Cluster"
            )

        logger.info("Add networks to the Host")
        if not hl_networks.createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict1,
            auto_nics=[0, 3]
        ):
            logger.error(
                "Cannot create and attach networks to the Host"
            )
