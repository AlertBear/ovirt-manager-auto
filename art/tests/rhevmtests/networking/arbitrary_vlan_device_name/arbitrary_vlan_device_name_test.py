"""
Test ArbitraryVlanDeviceName
Supporting vlan devices with names not in standard "dev.VLANID"
(e.g. eth0.10-fcoe, em1.myvlan10, vlan20, ...).
This job required password less ssh between the machine that run the job
and the host
"""

import logging
from art.rhevm_api.tests_lib.high_level.networks import(
    createAndAttachNetworkSN, remove_all_networks
)
from art.rhevm_api.tests_lib.low_level.hosts import get_host_name_from_engine
from helper import(
    check_if_nic_in_hostnics, add_bridge_on_host_and_virsh,
    delete_bridge_on_host_and_virsh, add_vlan_and_refresh_capabilities,
    check_if_nic_in_vdscaps, remove_vlan_and_refresh_capabilities,
    job_tear_down, VLAN_NAMES, BRIDGE_NAMES, VLAN_IDS
)
from art.test_handler.exceptions import NetworkException
from art.unittest_lib import attr
from art.unittest_lib import NetworkTest as TestCase
from art.test_handler.tools import tcms  # pylint: disable=E0611
from rhevmtests.networking import config

logger = logging.getLogger("ArbitraryVlanDeviceName_Cases")

HOST_NAME = None  # Filled in setup_module


def setup_module():
    """
    setup_module
    """
    global HOST_NAME
    HOST_NAME = get_host_name_from_engine(config.VDS_HOSTS[0].ip)


class TestArbitraryVlanDeviceNameTearDown(TestCase):
    """
    Tear down for ArbitraryVlanDeviceName
    This job create networks on host and we need to make sure that we clean
    the host from all VLANs and bridges
    """
    apis = set(["rest"])

    @classmethod
    def teardown_class(cls):
        job_tear_down()


@attr(tier=1)
class TestArbitraryVlanDeviceName01(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create VLAN entity with name on the host
    2. Check that the VLAN network exists on host via engine
    3. Attach the vlan to bridge
    4. Add the bridge with VLAN to virsh
    5. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN entity with name on the host
        """
        add_vlan_and_refresh_capabilities(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=VLAN_IDS[0],
            vlan_name=VLAN_NAMES[0]
        )

    @tcms(13961, 372421)
    def test_vlan_on_nic(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        check_if_nic_in_hostnics(nic=VLAN_NAMES[0], host=HOST_NAME)

        add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0],
            network=VLAN_NAMES[0]
        )
        check_if_nic_in_vdscaps(
            host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[0]
        )
        delete_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        try:
            remove_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[0]
            )
        except NetworkException:
            logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[0])
        super(TestArbitraryVlanDeviceName01, cls).teardown_class()


@attr(tier=1)
class TestArbitraryVlanDeviceName02(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create empty BOND
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create empty BOND via SetupNetworks
        Create VLAN entity with name on the host
        """
        local_dict = {None: {"nic": config.BOND[0], "slaves": [2, 3]}}
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0],
        ):
            raise NetworkException("Cannot create and attach network")

        add_vlan_and_refresh_capabilities(
            host_obj=config.VDS_HOSTS[0], nic=config.BOND[0],
            vlan_id=VLAN_IDS[0], vlan_name=VLAN_NAMES[0]
        )

    @tcms(13961, 372422)
    def test_vlan_on_bond(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        check_if_nic_in_hostnics(nic=VLAN_NAMES[0], host=HOST_NAME)

        add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0],
            network=VLAN_NAMES[0]
        )
        check_if_nic_in_vdscaps(
            host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[0]
        )
        delete_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        try:
            remove_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[0]
            )
        except NetworkException:
            logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[0])

        logger.info("Cleaning host interfaces")
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0]
        ):
            logger.error("Clean host interfaces failed")
        super(TestArbitraryVlanDeviceName02, cls).teardown_class()


@attr(tier=1)
class TestArbitraryVlanDeviceName03(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create 3 VLANs with name on the host
    2. For each VLAN check that the VLAN network exists on host via engine
    3. For each VLAN attach the vlan to bridge
    4. For each VLAN add the bridge with VLAN to virsh
    5. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN entity with name on the host
        """
        for i in range(3):
            add_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=VLAN_IDS[i],
                vlan_name=VLAN_NAMES[i]
            )

    @tcms(13961, 372423)
    def test_multiple_vlans_on_nic(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridges is in getVdsCaps
        """
        for i in range(3):
            check_if_nic_in_hostnics(nic=VLAN_NAMES[i], host=HOST_NAME)

        for i in range(3):
            add_bridge_on_host_and_virsh(
                host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[i],
                network=VLAN_NAMES[i]
            )

        for i in range(3):
            check_if_nic_in_vdscaps(
                host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[i]
            )

        for i in range(3):
            delete_bridge_on_host_and_virsh(
                host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[i]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        for i in range(3):
            try:
                remove_vlan_and_refresh_capabilities(
                    host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[i]
                )
            except NetworkException:
                logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[i])
        super(TestArbitraryVlanDeviceName03, cls).teardown_class()


@attr(tier=1)
class TestArbitraryVlanDeviceName04(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create empty BOND
    2. Create 3 VLANs with name on the host
    3. For each VLAN check that the VLAN network exists on host via engine
    4. For each VLAN attach the vlan to bridge
    5. For each VLAN add the bridge with VLAN to virsh
    6. For each VLAN remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create empty BOND
        Create VLAN entity with name on the host
        """
        logger.info("Create empty BOND")
        local_dict = {None: {
            "nic": config.BOND[0], "mode": 1, "slaves": [2, 3]}
        }
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0],
        ):
            raise NetworkException("Cannot create and attach network")

        for i in range(3):
            add_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], nic=config.BOND[0],
                vlan_id=VLAN_IDS[i], vlan_name=VLAN_NAMES[i]
            )

    @tcms(13961, 372424)
    def test_multiple_vlans_on_bond(self):
        """
        Create 3 VLANs on the host
        Check that all VLANs networks exists on host via engine
        Attach each vlan to bridge
        Add each bridge with VLAN to virsh
        Check that the bridges is in getVdsCaps
        """
        for i in range(3):
            check_if_nic_in_hostnics(nic=VLAN_NAMES[i], host=HOST_NAME)

        for i in range(3):
            add_bridge_on_host_and_virsh(
                host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[i],
                network=VLAN_NAMES[i]
            )

        for i in range(3):
            check_if_nic_in_vdscaps(
                host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[i]
            )

        for i in range(3):
            delete_bridge_on_host_and_virsh(
                host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[i]
            )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        for i in range(3):
            try:
                remove_vlan_and_refresh_capabilities(
                    host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[i]
                )
            except NetworkException:
                logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[i])

        logger.info("Cleaning host interfaces")
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0]
        ):
            logger.error("Clean host interfaces failed")
        super(TestArbitraryVlanDeviceName04, cls).teardown_class()


@attr(tier=1)
class TestArbitraryVlanDeviceName05(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create VLAN on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create VLAN on NIC via SetupNetworks
        Create VLAN entity with name on the host
        """
        logger.info(
            "Create and attach VLAN network on NIC to DC/Cluster and Host"
        )
        local_dict = {
            config.VLAN_NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "false",
            },
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1],
        ):
            raise NetworkException("Cannot create and attach network")

        add_vlan_and_refresh_capabilities(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=VLAN_IDS[0],
            vlan_name=VLAN_NAMES[0]
        )

    @tcms(13961, 373616)
    def test_mixed_vlan_types(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        check_if_nic_in_hostnics(nic=VLAN_NAMES[0], host=HOST_NAME)

        add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0],
            network=VLAN_NAMES[0]
        )
        check_if_nic_in_vdscaps(
            host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[0]
        )
        delete_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        try:
            remove_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[0]
            )
        except NetworkException:
            logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[0])

        logger.info("Removing all networks from %s", config.DC_NAME[0])
        if not remove_all_networks(
            datacenter=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove all networks from %s", config.DC_NAME[0])

        logger.info("Cleaning host interfaces")
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0]
        ):
            logger.error("Clean host interfaces failed")
        super(TestArbitraryVlanDeviceName05, cls).teardown_class()


@attr(tier=1)
class TestArbitraryVlanDeviceName06(TestArbitraryVlanDeviceNameTearDown):
    """
    1. Create Non-VM network on NIC via SetupNetworks
    2. Create VLAN entity with name on the host
    3. Check that the VLAN network exists on host via engine
    4. Attach the vlan to bridge
    5. Add the bridge with VLAN to virsh
    6. Remove the VLAN using setupNetwork
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create Non-VM network on NIC via SetupNetworks
        Create VLAN entity with name on the host
        """
        logger.info(
            "Create and attach VLAN network on NIC to DC/Cluster and Host"
        )
        local_dict = {
            config.NETWORKS[0]: {
                "vlan_id": config.VLAN_ID[0],
                "nic": 1,
                "required": "false",
                "usages": ""
            },
        }
        if not createAndAttachNetworkSN(
            data_center=config.DC_NAME[0], cluster=config.CLUSTER_NAME[0],
            host=config.VDS_HOSTS[0], network_dict=local_dict,
            auto_nics=[0, 1],
        ):
            raise NetworkException("Cannot create and attach network")

        add_vlan_and_refresh_capabilities(
            host_obj=config.VDS_HOSTS[0], nic=1, vlan_id=VLAN_IDS[0],
            vlan_name=VLAN_NAMES[0]
        )

    @tcms(13961, 373616)
    def test_vlan_with_non_vm(self):
        """
        Check that the VLAN network exists on host via engine
        Attach the vlan to bridge
        Add the bridge with VLAN to virsh
        Check that the bridge is in getVdsCaps
        """
        check_if_nic_in_hostnics(nic=VLAN_NAMES[0], host=HOST_NAME)

        add_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0],
            network=VLAN_NAMES[0]
        )
        check_if_nic_in_vdscaps(
            host_obj=config.VDS_HOSTS[0], nic=BRIDGE_NAMES[0]
        )
        delete_bridge_on_host_and_virsh(
            host_obj=config.VDS_HOSTS[0], bridge=BRIDGE_NAMES[0]
        )

    @classmethod
    def teardown_class(cls):
        """
        Remove the VLAN from the host
        """
        try:
            remove_vlan_and_refresh_capabilities(
                host_obj=config.VDS_HOSTS[0], vlan_name=VLAN_NAMES[0]
            )
        except NetworkException:
            logger.error("Coudn't remove VLAN %s from host", VLAN_NAMES[0])

        logger.info("Removing all networks from %s", config.DC_NAME[0])
        if not remove_all_networks(
            datacenter=config.DC_NAME[0], mgmt_network=config.MGMT_BRIDGE,
            cluster=config.CLUSTER_NAME[0]
        ):
            logger.error(
                "Failed to remove all networks from %s", config.DC_NAME[0])

        logger.info("Cleaning host interfaces")
        if not createAndAttachNetworkSN(
            host=config.VDS_HOSTS[0], network_dict={}, auto_nics=[0]
        ):
            logger.error("Clean host interfaces failed")
        super(TestArbitraryVlanDeviceName06, cls).teardown_class()
