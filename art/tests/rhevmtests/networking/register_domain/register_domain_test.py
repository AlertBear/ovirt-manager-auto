#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Register domain network test
"""

import pytest

from art.rhevm_api.tests_lib.low_level import (
    storagedomains as ll_storage,
    vms as ll_vms
)
from art.rhevm_api.tests_lib.high_level import templates as hl_templates
import config as register_domain_conf
import helper
from rhevmtests import helpers
import rhevmtests.networking.config as conf
from art.test_handler.tools import polarion, bz
from fixtures import (  # noqa: F401
    prepare_setup,
    import_vm_from_data_domain,
    import_templates_from_data_domain,
    set_allow_duplicate_mac_pool,
    manage_mac_pool_range,
    make_sure_no_mac_in_pool,
)
from art.unittest_lib import (
    NetworkTest,
    testflow,
    tier2,
)


@pytest.mark.usefixtures(
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain01(NetworkTest):
    """
    Import VM from storage data domain with same MAC pool range and network
    exists on datacenter
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[1][0]
    reassessing_mac = False

    @tier2
    @polarion("RHEVM-17152")
    def test_mac_pool_in_mac_range(self):
        """
        Check that MAC of imported VM is from the MAC pool
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the MAC of imported VM %s is from the MAC pool", self.vm
        )
        assert helper.check_mac_in_mac_range(vm=self.vm, nic=nic)

    @tier2
    @polarion("RHEVM-17161")
    def test_network_in_dc(self):
        """
        Check that network of imported VM stay the same
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the network %s of imported VM %s stay the same",
            network, self.vm
        )
        assert ll_vms.check_vnic_on_vm_nic(vm=self.vm, nic=nic, vnic=network)


@pytest.mark.usefixtures(
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain02(NetworkTest):
    """
    Import VM from storage data domain when MAC is not from pool and network
    not is datacenter and reassessing MAC is checked and mapping the network
    in the import process
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[2][0]
    src_net = register_domain_conf.NETS[2][0]
    dst_net = register_domain_conf.NETS[2][1]
    network_mappings = [{
        "source_network_profile_name": src_net,
        "source_network_name": src_net,
        "target_network": dst_net,
        "target_vnic_profile": dst_net
    }]

    @tier2
    @polarion("RHEVM-16998")
    def test_mac_pool_not_in_mac_range_with_reassign(self):
        """
        Check that MAC of imported VM is from the MAC pool
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the MAC of imported VM %s is from the MAC pool", self.vm
        )
        assert helper.check_mac_in_mac_range(vm=self.vm, nic=nic)

    @tier2
    @polarion("RHEVM-17163")
    def test_network_not_in_dc_with_mapping(self):
        """
        Check that network of imported VM was mapped to new network
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the network %s of imported VM %s changed to %s",
            network, self.vm, self.dst_net
        )
        assert ll_vms.check_vnic_on_vm_nic(
            vm=self.vm, nic=nic, vnic=self.dst_net
        )


@pytest.mark.usefixtures(
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain03(NetworkTest):
    """
    Import VM from storage data domain when MAC is not from pool and network
    not is datacenter and reassessing MAC is not checked and without mapping
    the network in the import process
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[3][0]
    net = register_domain_conf.NETS[3][0]
    reassessing_mac = False

    @tier2
    @polarion("RHEVM-16997")
    def test_mac_pool_not_in_mac_range_without_reassign(self):
        """
        Check that MAC of imported VM is not from the MAC pool
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the MAC of imported VM %s is not from the MAC pool", self.vm
        )
        assert not helper.check_mac_in_mac_range(vm=self.vm, nic=nic)
        vm_mac = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=nic)
        testflow.step(
            "Check the MAC of imported VM %s is %s", self.vm, mac
        )
        assert vm_mac == mac

    @tier2
    @polarion("RHEVM-17162")
    def test_network_not_in_dc_without_mapping(self):
        """
        Check that imported VM have empty vNIC profile
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the imported VM %s have empty vNIC profile", self.vm
        )
        assert ll_vms.check_vnic_on_vm_nic(vm=self.vm, nic=nic, vnic=None)


@pytest.mark.usefixtures(
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain04(NetworkTest):
    """
    Import VM from storage data domain when MAC is already exists on another VM
    with reassessing MAC flag
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[4][0]

    @tier2
    @polarion("RHEVM-17153")
    def test_mac_pool_not_in_mac_range_already_exists_with_reassign(self):
        """
        Check that MAC of imported VM is from the MAC pool
        Check that the VM vNIC is plugged after import
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step(
            "Check the MAC of imported VM %s is from the MAC pool", self.vm
        )
        assert helper.check_mac_in_mac_range(vm=self.vm, nic=nic)
        testflow.step("Check that VM vNIC %s is plugged", nic)
        assert ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic)


class TestRegisterDomain05(NetworkTest):
    """
    Import VM from storage data domain when MAC is already exists on another VM
    without reassessing MAC flag
    """
    # General params
    vm = register_domain_conf.VM_NAMES[5][0]

    @tier2
    @polarion("RHEVM-16896")
    def test_mac_pool_not_in_mac_range_already_exists_without_reassign(self):
        """
        Check that import VM fail when MAC is already exists in engine
        """
        unregistered_vms = ll_storage.get_unregistered_vms(
            storage_domain=register_domain_conf.EXTRA_SD_NAME
        )
        vm_to_import = [i for i in unregistered_vms if i.name == self.vm]
        assert vm_to_import
        testflow.step(
            "Check that import VM %s from data domain %s fail with: "
            "reassessing_mac=False when MAC is duplicate",
            self.vm, register_domain_conf.EXTRA_SD_NAME
        )
        assert not ll_storage.register_object(
            obj=vm_to_import[0], cluster=conf.CL_0, reassign_bad_macs=False
        )


@pytest.mark.usefixtures(
    set_allow_duplicate_mac_pool.__name__,
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain06(NetworkTest):
    """
    Import VM from storage data domain when MAC is already exists on another VM
    without reassessing MAC flag and allow duplicate flag in MAC pool
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[6][0]
    reassessing_mac = False

    @tier2
    @polarion("RHEVM-17143")
    def test_mac_pool_not_in_mac_range_already_exists_without_reassign(self):
        """
        Check that MAC of imported VM is not from the MAC pool
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        vm_mac = ll_vms.get_vm_nic_mac_address(vm=self.vm, nic=nic)
        testflow.step(
            "Check the MAC of imported VM %s is %s", self.vm, mac
        )
        assert mac == vm_mac
        testflow.step("Check that VM vNIC %s is plugged", nic)
        assert ll_vms.get_vm_nic_plugged(vm=self.vm, nic=nic)


@pytest.mark.usefixtures(
    manage_mac_pool_range.__name__,
    make_sure_no_mac_in_pool.__name__
)
class TestRegisterDomain07(NetworkTest):
    """
    Import VM from storage data domain when not MACs left in the pool
    with reassessing MAC flag
    """
    # make_sure_no_mac_in_pool params
    vm = register_domain_conf.VM_NAMES[7][0]

    @tier2
    @polarion("RHEVM-17144")
    def test_no_mac_left_in_pool_with_reassign(self):
        """
        Check that the VM fail to import when no MACs left in the pool
        """
        unregistered_vms = ll_storage.get_unregistered_vms(
            storage_domain=register_domain_conf.EXTRA_SD_NAME
        )
        vm_to_import = [i for i in unregistered_vms if i.name == self.vm]
        assert vm_to_import
        testflow.step(
            "Check that import VM %s from data domain %s fail with: "
            "reassessing_mac=True when no MACs left in the pool",
            self.vm, register_domain_conf.EXTRA_SD_NAME
        )
        assert not ll_storage.register_object(
            obj=vm_to_import[0], cluster=conf.CL_0, reassign_bad_macs=True
        )


@pytest.mark.usefixtures(
    import_vm_from_data_domain.__name__
)
class TestRegisterDomain08(NetworkTest):
    """
    Import VM from storage data domain while the network exists on
    datacenter but force to import with empty vNIC
    """
    # import_vm_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME
    vm = register_domain_conf.VM_NAMES[8][0]
    reassessing_mac = False
    net = register_domain_conf.NETS[8][0]
    network_mappings = [{
        "source_network_profile_name": net,
        "source_network_name": net,
        "target_network": None,
        "target_vnic_profile": None
    }]

    @tier2
    @bz({"1522799": {}})
    @polarion("RHEVM-17164")
    def test_network_in_dc_force_empty_vnic(self):
        """
        Check that VM imported with empty vNIC
        """
        mac, network, nic = helper.get_vm_params(vm=self.vm)
        testflow.step("Check that VM %s imported with empty vNIC", self.vm)
        assert ll_vms.check_vnic_on_vm_nic(vm=self.vm, nic=nic, vnic=None)


@pytest.mark.usefixtures(
    import_templates_from_data_domain.__name__
)
class TestRegisterDomain09(NetworkTest):
    """
    Import template from storage data domain network exists on data-center
    """
    # import_template_from_data_domain params
    data_domain_name = register_domain_conf.EXTRA_SD_NAME

    # General params
    templates = register_domain_conf.TEMPLATES_DICT.keys()

    # Params: [Template name, vNIC name, Network mapping]
    # For vNIC name:
    #   when vNIC is '' then use the original vNIC from template

    # Import-template-without-network-mapping params
    test_1_params = [templates[0], "", []]

    # "Import-template-when-network-is-missing-on-dc params
    test_2_params = [templates[1], None, []]

    # Import-template-with-network-mapping params
    with_map_src_net = register_domain_conf.NETS[3][0]
    with_map_dst_net = register_domain_conf.NETS[2][1]
    test_3_mapping = [{
        "source_network_profile_name": with_map_src_net,
        "source_network_name": with_map_src_net,
        "target_network": with_map_dst_net,
        "target_vnic_profile": with_map_dst_net
    }]
    test_3_params = [templates[2], with_map_dst_net, test_3_mapping]

    # Import-template-with-mapping-to-empty-vNIC-profile
    empty_map_src_net = register_domain_conf.NETS[2][0]
    test_4_mapping = [{
        "source_network_profile_name": empty_map_src_net,
        "source_network_name": empty_map_src_net,
        "target_network": None,
        "target_vnic_profile": None
    }]
    test_4_params = [templates[3], None, test_4_mapping]

    @tier2
    @pytest.mark.parametrize(
        ("template", "vnic", "mappings"),
        [
            pytest.param(*test_1_params, marks=(polarion("RHEVM-24355"))),
            pytest.param(*test_2_params, marks=(polarion("RHEVM-24352"))),
            pytest.param(*test_3_params, marks=(polarion("RHEVM-24353"))),
            pytest.param(
                *test_4_params, marks=(
                        polarion("RHEVM-24354"), bz({"1522799": {}}))
            ),
        ],
        ids=[
            "Import-template-without-network-mapping",
            "Import-template-when-network-is-missing-on-dc",
            "Import-template-with-network-mapping",
            "Import-template-with-network-mapping-to-empty-vNIC-profile"
        ]
    )
    def test_import_template_from_domain(self, template, vnic, mappings):
        """
        1. Check that network of created VM imported from template stay the
            same
        2. Check that network of created VM imported from template have empty
            vNIC profile
        3. Check that network of created VM imported from template was mapped
            to new network
        4. Check that network of created VM imported from template was mapped
            to empty network
        """
        _id = helpers.get_test_parametrize_ids(
            item=self.test_import_template_from_domain.parametrize,
            params=[template, vnic, mappings]
        )
        testflow.step(_id)
        network, nic = helper.get_template_params(template=template)
        vnic = network if vnic == "" else None or vnic
        assert hl_templates.check_vnic_on_template_nic(
            template=template, vnic=vnic, nic=nic
        )
