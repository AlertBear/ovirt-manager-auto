"""
Testing Import/Export feature.
2 DC, 2 Cluster, 2 Hosts, 1 export domain, 2 VM and 2 templates will be
created for testing.
"""
from art.rhevm_api.tests_lib.low_level.hosts import sendSNRequest
from rhevmtests.networking import config
import logging
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.rhevm_api.tests_lib.low_level.vms import startVm, removeNic, \
    importVm, removeVm, check_vnic_on_vm_nic, addVm
from art.rhevm_api.tests_lib.high_level.networks import removeNetFromSetup, \
    createAndAttachNetworkSN
from art.rhevm_api.tests_lib.low_level.templates import importTemplate, \
    removeTemplate, check_vnic_on_template_nic
from art.test_handler.tools import tcms
from art.test_handler.exceptions import NetworkException

logger = logging.getLogger(__name__)

########################################################################

########################################################################
#                             Test Cases                               #
########################################################################


@attr(tier=1)
class IECase01(TestCase):
    """
    Check that VM created in the previous version could be imported
    to the higher version DC with all the networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Import VM from lower version DC
        2) Import the same VM more than once
        """
        logger.info("Import VM to the DC with current version from the "
                    "previous version DC and import the same VM more then "
                    "once")
        for name in (None, config.IMP_MORE_THAN_ONCE_VM):
            log_vm = name if name is not None else config.VM_NAME[0]
            if not importVm(positive=True, vm=config.VM_NAME[0],
                            export_storagedomain=config.EXPORT_STORAGE_NAME,
                            import_storagedomain=config.STORAGE_NAME[1],
                            cluster=config.CLUSTER_NAME[1], name=name):
                raise NetworkException("Cannot import %s created in the same "
                                       "DC version" % log_vm)

    @tcms(6915, 194259)
    def test_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles from the lower
        version DC
        """
        logger.info("Check VM NICs VNIC profiles for VM imported from "
                    "previous version")

        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_vm_nic(vm=config.VM_NAME[0], nic=nic,
                                        vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       "for VM" % (vnic, nic))

    @tcms(6915, 194264)
    def test_import_vm_more_than_once(self):
        """
        Check that VM imported more than once keeps all it's VNIC profiles
        """
        logger.info("Check VM NICs VNIC profiles for VM imported more than "
                    "once")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_vm_nic(vm=config.IMP_MORE_THAN_ONCE_VM,
                                        nic=nic, vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       "for VM" % (vnic, nic))

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs imported from Export domain
        """
        logger.info("Removing VMs imported from Export domain")
        for vm in (config.VM_NAME[0], config.IMP_MORE_THAN_ONCE_VM):
            if not removeVm(positive=True, vm=vm):
                raise NetworkException("Couldn't remove imported VM %s" % vm)


@attr(tier=1)
class IECase02(TestCase):
    """
    Check that Template created in the previous version could be imported
    to the higher version DC with all the networks
    Check that Template imported more than once keeps all it's network
    configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Import template from lower version DC
        2) Import the same Template more than once
        """
        logger.info("Import Template to the DC with current version from the "
                    "previous version DC and import the same template more "
                    "then once")
        for name in (None, config.IMP_MORE_THAN_ONCE_TEMP):
            log_temp = name if name is not None else config.TEMPLATE_NAME[0]
            if not importTemplate(
                positive=True,
                template=config.TEMPLATE_NAME[0],
                export_storagedomain=config.EXPORT_STORAGE_NAME,
                import_storagedomain=config.STORAGE_NAME[1],
                cluster=config.CLUSTER_NAME[1], name=name
            ):
                raise NetworkException("Cannot import %s created in lower "
                                       "version" % log_temp)

    @tcms(6915, 194552)
    def test_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles from the
        lower version DC
        """
        logger.info("Check that NICs VNIC profiles for Template imported "
                    "more than once are kept")

        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_template_nic(template=config.TEMPLATE_NAME[0],
                                              nic=nic, vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for Template" % (vnic, nic))

    @tcms(6915, 194554)
    def test_import_more_than_once(self):
        """
        Check that Template imported more than once keeps all it's VNIC
        profiles
        """
        logger.info("Check that NICs VNIC profiles for Template imported "
                    "more than once are kept")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_template_nic(
                template=config.IMP_MORE_THAN_ONCE_TEMP,
                nic=nic,
                vnic=vnic
            ):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for Template" % (vnic, nic))

    @classmethod
    def teardown_class(cls):
        """
        Remove imported templates from Export domain
        """
        logger.info("Removing imported templates from Export domain")
        for template in (config.IMP_MORE_THAN_ONCE_TEMP,
                         config.TEMPLATE_NAME[0]):
            if not removeTemplate(positive=True,
                                  template=template):
                raise NetworkException("Couldn't remove imported Template")


@attr(tier=1)
class IECase03(TestCase):
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

        logger.info("Remove sw1 and sw2 from setup")
        if not removeNetFromSetup(host=config.HOSTS[1],
                                  auto_nics=[config.HOST_NICS[0]],
                                  network=config.NETWORKS[:2],
                                  data_center=config.DC_NAME[1]):
            raise NetworkException("Cannot remove network sw1 and sw2 from "
                                   "setup")

        logger.info("Remove sw3 from the host")
        if not sendSNRequest(positive=True, host=config.HOSTS[1],
                             auto_nics=[config.HOST_NICS[0]]):
            raise NetworkException("Failed to remove sw3 from %s" %
                                   config.HOSTS[1])

        logger.info("Import template with sw1, sw2 and sw3 to DC when sw1 "
                    "and sw2 don't exist there anymore and sw3 doesn't exist "
                    "on the hosts of that DC")
        if not importTemplate(positive=True,
                              template=config.TEMPLATE_NAME[0],
                              export_storagedomain=config.EXPORT_STORAGE_NAME,
                              import_storagedomain=config.STORAGE_NAME[1],
                              cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot import Template to the setup ")

        logger.info("Import VM with sw1, sw2 and sw3 to DC when sw1 and sw2 "
                    "don't exist there anymore and sw3 doesn't exist on the "
                    "hosts of that DC")
        if not importVm(positive=True, vm=config.VM_NAME[0],
                        export_storagedomain=config.EXPORT_STORAGE_NAME,
                        import_storagedomain=config.STORAGE_NAME[1],
                        cluster=config.CLUSTER_NAME[1]):
            raise NetworkException("Cannot import VM to the setup")

    @tcms(6915, 194247)
    def test_import_vm_vnic_profiles(self):
        """
        Check that the VNIC that had sw1 and sw2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """

        logger.info("Check VM NICs VNIC profiles when one of them is missing "
                    "in the target DC exist on the setup")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', None),
                            ('nic3', None),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_vm_nic(vm=config.VM_NAME[0],
                                        nic=nic, vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for VM" % (vnic, nic))

    @tcms(6915, 194553)
    def test_import_temp_vnicp_rofiles(self):
        """
        Check that the Template that had sw1 and sw2 on VM before import
        action, has an empty VNIC for that VNIC profiles after import
        completed
        """
        logger.info("Check VM NICs VNIC profiles for Template")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', None),
                            ('nic3', None),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_template_nic(
                template=config.TEMPLATE_NAME[0],
                nic=nic,
                vnic=vnic
            ):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for Template" % (vnic, nic))

    @tcms(6915, 378808)
    def test_start_vm(self):
        """
        1) Negative - Start VM when one of the networks attached to it doesn't
        reside on any host in the setup
        2) Positive - Start VM after removing network that doesn't reside on
        any host in the setup
        """
        logger.info("Try to start VM when one of the networks is not "
                    "attached to any host in the setup")
        if not startVm(positive=False, vm=config.VM_NAME[0]):
            raise NetworkException("Could start VM, when shouldn't")

        logger.info("Remove NIC with sw3 network not attached to any Host in "
                    "the setup")
        if not removeNic(positive=True, vm=config.VM_NAME[0], nic='nic4'):
            raise NetworkException("Couldn't remove nic from VM %s" %
                                   config.VM_NAME[0])

        logger.info("Start imported VM when all the networks of VM reside on "
                    "one of the hosts in the setup")
        if not startVm(positive=True, vm=config.VM_NAME[0],
                       wait_for_ip=True):
            raise NetworkException("Couldn't start VM %s , when should" %
                                   config.VM_NAME[0])

    @tcms(6915, 378809)
    def test_start_vm_from_template(self):
        """
        1) Create VM from imported template
        2) Negative - Start VM, created from template when one of the
        networks, attached to it doesn't reside on any host in the setup
        3) Positive - Start VM, created from template after removing network
        that doesn't reside on any host in the setup
        """
        logger.info("Create VM %s from imported template %s",
                    config.VM_NAME[1], config.TEMPLATE_NAME[0])
        if not addVm(True, name=config.VM_NAME[1],
                     cluster=config.CLUSTER_NAME[1],
                     template=config.TEMPLATE_NAME[0],
                     display_type=config.DISPLAY_TYPE):
            raise NetworkException("Cannot create VM %s from imported "
                                   "template %s" % (config.VM_NAME[1],
                                                    config.TEMPLATE_NAME[0]))

        logger.info("Try to start VM, created from template when one of the "
                    "networks is not attached to any host in the setup")
        if not startVm(positive=False, vm=config.VM_NAME[1]):
            raise NetworkException("Could start VM %s, when shouldn't" %
                                   config.VM_NAME[1])

        logger.info("Remove NIC with sw3 network not attached to any Host in "
                    "the setup")
        if not removeNic(positive=True, vm=config.VM_NAME[1], nic='nic4'):
            raise NetworkException("Couldn't remove nic from VM %s" %
                                   config.VM_NAME[1])

        logger.info("Start VM, created from template when all the networks "
                    "of VM reside on one of the hosts in the setup")
        if not startVm(positive=True, vm=config.VM_NAME[1], wait_for_ip=True):
            raise NetworkException("Couldn't start VM %s, when should" %
                                   config.VM_NAME[1])

    @classmethod
    def teardown_class(cls):
        """
        1) Remove VM imported from Export domain and VM created from template
        2) Remove Template imported from Export domain and VM created from
        that Template
        3) Put the networks sw1, sw2 and sw3 back to the DC/Cluster/Host
        """
        local_dict = {config.NETWORKS[0]: {'nic': config.HOST_NICS[1],
                                           'required': 'false'},
                      config.NETWORKS[1]: {'mtu': config.MTU[0],
                                           'nic': config.HOST_NICS[2],
                                           'required': 'false'}}

        logger.info("Remove VMs from setup")
        for i in range(2):
            if not removeVm(positive=True, vm=config.VM_NAME[i],
                            stopVM='true'):
                raise NetworkException("Couldn't remove imported VM %s" %
                                       config.VM_NAME[i])

        logger.info("Remove imported Template from setup")
        if not removeTemplate(positive=True,
                              template=config.TEMPLATE_NAME[0]):
            raise NetworkException("Couldn't remove imported Template")

        logger.info("Add networks to the DC/Cluster/Host")
        vlan_nic = ".".join([config.HOST_NICS[3], config.VLAN_ID[0]])
        if not createAndAttachNetworkSN(data_center=config.DC_NAME[1],
                                        cluster=config.CLUSTER_NAME[1],
                                        host=config.HOSTS[1],
                                        network_dict=local_dict,
                                        auto_nics=[config.HOST_NICS[0],
                                                   config.HOST_NICS[3],
                                                   vlan_nic]):
            raise NetworkException("Cannot create and attach networks to "
                                   "the setup")


@attr(tier=1)
class IECase04(TestCase):
    """
    Check that VM created in the same version could be imported with all the
    networks
    Check that VM imported more than once keeps all it's network configuration
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        1) Import VM from same DC version
        2) Import the same VM more than once
        """
        logger.info("Import VM to the DC with current version from the "
                    "same DC version and import the same VM more then once")
        for name in(None, config.IMP_MORE_THAN_ONCE_VM):
            log_vm = name if name is not None else config.VM_NAME[1]
            if not importVm(positive=True, vm=config.VM_NAME[1],
                            export_storagedomain=config.EXPORT_STORAGE_NAME,
                            import_storagedomain=config.STORAGE_NAME[1],
                            cluster=config.CLUSTER_NAME[1], name=name):
                raise NetworkException("Cannot import %s created in the same "
                                       "DC version" % log_vm)

    @tcms(6915, 194246)
    def test_imported_vm_vnics(self):
        """
        Check that the VM is imported with all VNIC profiles from the same
        DC version
        """
        logger.info("Check VM NICs VNIC profiles for VM imported from "
                    "same DC version")

        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_vm_nic(vm=config.VM_NAME[1], nic=nic,
                                        vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for VM" % (vnic, nic))

    @tcms(6915, 194253)
    def test_import_vm_more_than_once(self):
        """
        Check that VM imported more than once keeps all it's VNIC profiles
        """
        logger.info("Check VM NICs VNIC profiles for VM imported more than "
                    "once")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_vm_nic(vm=config.IMP_MORE_THAN_ONCE_VM,
                                        nic=nic, vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for VM" % (vnic, nic))

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs imported from Export domain
        """
        for vm in (config.VM_NAME[1], config.IMP_MORE_THAN_ONCE_VM):
            if not removeVm(positive=True, vm=vm):
                raise NetworkException("Couldn't remove imported VM %s" % vm)


@attr(tier=1)
class IECase05(TestCase):
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
        1) Import template from same DC version
        2) Import the same Template more than once
        """
        logger.info("Import Template to the DC with current version from the "
                    "same DC version and import the same template more then "
                    "once")
        for name in (None, config.IMP_MORE_THAN_ONCE_TEMP):
            log_temp = name if name is not None else config.TEMPLATE_NAME[1]
            if not importTemplate(
                positive=True,
                template=config.TEMPLATE_NAME[1],
                export_storagedomain=config.EXPORT_STORAGE_NAME,
                import_storagedomain=config.STORAGE_NAME[1],
                cluster=config.CLUSTER_NAME[1],
                name=name
            ):
                raise NetworkException("Cannot import %s created in lower "
                                       "version" % log_temp)

    @tcms(6915, 194552)
    def test_imported_temp_vnics(self):
        """
        Check that the Template is imported with all VNIC profiles from the
        lower version DC
        """
        logger.info("Check that NICs VNIC profiles for Template imported "
                    "more than once are kept")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_template_nic(template=config.TEMPLATE_NAME[1],
                                              nic=nic, vnic=vnic):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for Template" % (vnic, nic))

    @tcms(6915, 194554)
    def test_import_more_than_once(self):
        """
        Check that Template imported more than once keeps all it's VNIC
        profiles
        """
        logger.info("Check that NICs VNIC profiles for Template imported "
                    "more than once are kept")
        for (nic, vnic) in (('nic1', config.MGMT_BRIDGE),
                            ('nic2', config.NETWORKS[0]),
                            ('nic3', config.NETWORKS[1]),
                            ('nic4', config.NETWORKS[2])):
            if not check_vnic_on_template_nic(
                template=config.IMP_MORE_THAN_ONCE_TEMP,
                nic=nic,
                vnic=vnic
            ):
                raise NetworkException("No correct VNIC profile %s on VNIC %s"
                                       " for Template" % (vnic, nic))

    @classmethod
    def teardown_class(cls):
        """
        Remove VMs imported from Export domain
        """
        logger.info("Removing imported templates")
        for template in (config.IMP_MORE_THAN_ONCE_TEMP,
                         config.TEMPLATE_NAME[1]):
            if not removeTemplate(positive=True,
                                  template=template):
                raise NetworkException("Couldn't remove imported Template")
