"""
Testing MultiHost feature.
1 DC, 1 Cluster, 2 Hosts and 2 VMs will be used for testing.
MultiHost will be tested for untagged, tagged, MTU, VM/non-VM and bond
scenarios.
"""

import time
import helper
import logging
import config as conf
from art.core_api import apis_utils
from art.rhevm_api.utils import test_utils
from art.test_handler.tools import polarion  # pylint: disable=E0611
from art.unittest_lib import attr, NetworkTest
import art.rhevm_api.tests_lib.low_level.vms as ll_vms
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.clusters as ll_clusters
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.high_level.networks as hl_networks
import art.rhevm_api.tests_lib.low_level.templates as ll_templates
import art.rhevm_api.tests_lib.high_level.host_network as hl_host_network

logger = logging.getLogger("MultiHost_Cases")


@attr(tier=2)
class TestMultiHostTestCaseBase(NetworkTest):
    """
    base class which provides teardown class method for each test case
    """
    net = None
    mtu_1500 = None
    restore_mtu = False

    @classmethod
    def teardown_class(cls):
        """
        Remove networks from the setup.
        Restore MTU if needed
        """
        if cls.restore_mtu:
            try:
                helper.update_network_and_check_changes(
                    net=cls.net, mtu=cls.mtu_1500,
                    hosts=conf.HOSTS_LIST, vds_hosts=conf.VDS_HOSTS_LIST
                )
            except conf.NET_EXCEPTION as e:
                logger.error(e)

        # lines 37-44: Temp WA till we refactor all cases
        all_nets = [
            net.name for net in ll_networks.get_networks_in_datacenter(
                datacenter=conf.DC_NAME[0]
            )
        ]
        nets_to_keep = [conf.MGMT_BRIDGE]
        nets_to_keep.extend(conf.NETS_DICT.keys())
        nets_to_remove = [i for i in all_nets if i not in nets_to_keep]
        hl_networks.remove_net_from_setup(
            host=conf.HOSTS_LIST, data_center=conf.DC_NAME_0,
            network=nets_to_remove
        )


class TestMultiHostCase01(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN
    Update tagged network with another VLAN
    Update tagged network to be untagged
    """
    __test__ = True
    net = conf.NETS[1][0]
    vlan_1 = conf.VLAN_IDS[0]
    vlan_2 = conf.VLAN_IDS[1]

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        """
        local_dict = {
            cls.net: {
                "nic": 1,
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4067")
    def test_update_with_vlan(self):
        """
        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        5) Update network with VLAN 163 to be untagged
        6) Check that the Host was updated as well
        """
        helper.update_network_and_check_changes(
            net=self.net, vlan_id=self.vlan_1
        )
        helper.update_network_and_check_changes(
            net=self.net, vlan_id=self.vlan_2
        )


class TestMultiHostCase02(TestMultiHostTestCaseBase):
    """
    Update network with the default MTU to the MTU of 9000
    Update network to have default MTU value
    """
    __test__ = True
    net = conf.NETS[2][0]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        dict_dc1 = {
            cls.net: {
                "nic": 1,
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=dict_dc1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4080")
    def test_update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        helper.update_network_and_check_changes(
            net=self.net, mtu=self.mtu_9000
        )
        helper.update_network_and_check_changes(
            net=self.net, mtu=self.mtu_1500
        )


class TestMultiHostCase03(TestMultiHostTestCaseBase):
    """
    Update VM network to be non-VM network
    Update non-VM network to be VM network
    """
    __test__ = True
    net = conf.NETS[3][0]

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        dict_dc1 = {
            cls.net: {
                "nic": 1
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0,  network_dict=dict_dc1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4072")
    def test_update_with_non_vm_nonvm(self):
        """
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        helper.update_network_and_check_changes(
            net=self.net, bridge=False
        )
        helper.update_network_and_check_changes(
            net=self.net, bridge=True
        )


class TestMultiHostCase04(TestMultiHostTestCaseBase):
    """
    Update network name:
    1) Negative when host is using it
    2) Negative when VM is using it (even non-running one)
    3) Negative when template is using it
    4) Positive when only DC/Cluster are using it
    Update non-VM network to be VM network
    """
    __test__ = True
    net = conf.NETS[4][0]
    new_net_name = "multihost_net"
    vnic_2_name = conf.NIC_NAME[1]

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        dict_dc1 = {
            cls.net: {
                "nic": 1
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=dict_dc1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4079")
    def test_update_net_name(self):
        """
        1) Try to update network name when the network resides on the Host
        2) Try to update network name when the network resides on VM
        3) Try to update network name when the network resides on Template
        All cases should fail being negative cases
        4) Update network name when the network resides only on DC and Cluster
        Test should succeed
        """
        if not ll_networks.updateNetwork(
            positive=False, network=self.net,
            data_center=conf.DC_NAME_0, name=self.new_net_name
        ):
            raise conf.NET_EXCEPTION()

        if not hl_host_network.clean_host_interfaces(
            host_name=conf.HOST_NAME_0
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.addNic(
            positive=True, vm=conf.VM_NAME_1, name=self.vnic_2_name,
            network=self.net
        ):
            raise conf.NET_EXCEPTION("Cannot add vNIC to VM")

        logger.info(
            "Negative: Try to update network name when network resides on VM"
        )
        if not ll_networks.updateNetwork(
            positive=False, network=self.net, data_center=conf.DC_NAME_0,
            name=self.new_net_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_vms.removeNic(
            positive=True, vm=conf.VM_NAME_1, nic=self.vnic_2_name
        ):
            raise conf.NET_EXCEPTION("Cannot remove NIC from VM")

        if not ll_templates.addTemplateNic(
            positive=True, template=conf.TEMPLATE_NAME_0,
            name=self.vnic_2_name, data_center=conf.DC_NAME_0, network=self.net
        ):
            raise conf.NET_EXCEPTION()

        logger.info(
            "Negative: Try to update network name when network resides "
            "on Template"
        )
        if not ll_networks.updateNetwork(
            positive=False, network=self.net, data_center=conf.DC_NAME_0,
            name=self.vnic_2_name
        ):
            raise conf.NET_EXCEPTION()

        if not ll_templates.removeTemplateNic(
            positive=True, template=conf.TEMPLATE_NAME_0, nic=self.vnic_2_name
        ):
            raise conf.NET_EXCEPTION()

        logger.info(
            "Update network name when network resides only on DC and Cluster"
        )
        if not ll_networks.updateNetwork(
            positive=True, network=self.net, data_center=conf.DC_NAME_0,
            name=self.new_net_name
        ):
            raise conf.NET_EXCEPTION()


class TestMultiHostCase05(TestMultiHostTestCaseBase):
    """
    Update network on running/non-running VM:
    1) Positive: Change MTU on net when running VM is using it
    2) Positive: Change VLAN on net when running VM is using it
    3) Positive: Change MTU on net when non-running VM is using it
    4) Positive: Change VLAN on net when non-running VM is using it
    5) Negative: Update non-VM network to be VM network used by non-running VM
    """
    __test__ = True
    net = conf.NETS[5][0]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = conf.VLAN_IDS[2]
    vm_nic = conf.NIC_NAME[1]

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster,Host, running and
        non-running VMs
        """
        dict_dc1 = {
            cls.net: {
                "nic": 1
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=dict_dc1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

        for i in range(2):
            if not ll_vms.addNic(
                positive=True, vm=conf.VM_NAME[i], name=cls.vm_nic,
                network=cls.net
            ):
                raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4074")
    def test_update_net_on_vm(self):
        """
        1) Positive: Change MTU on net when running VM is using it
        2) Positive: Change VLAN on net when running VM is using it
        3) Positive: Change MTU on net when non-running VM is using it
        4) Positive: Change VLAN on net when non-running VM is using it
        5) Negative: Update non-VM network to be VM network used by
        non-running VM
        """
        helper.update_network_and_check_changes(
            net=self.net, mtu=self.mtu_9000
        )
        helper.update_network_and_check_changes(
            net=self.net, vlan_id=self.vlan
        )

        if not ll_networks.updateNetwork(
            positive=False, network=self.net, data_center=conf.DC_NAME_0,
            usages=""
        ):
            raise conf.NET_EXCEPTION()

        logger.info(conf.UPDATE_CHANGES_HOST)
        if not ll_networks.is_host_network_is_vm(
            vds_resource=conf.VDS_HOST_0, net_name=self.net
        ):
            raise conf.NET_EXCEPTION()

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default
        Remove Network from VMs
        Remove network from Host
        """
        TestMultiHostTestCaseBase.net = cls.net
        TestMultiHostTestCaseBase.mtu_1500 = cls.mtu_1500
        cls.restore_mtu = True
        if not ll_vms.updateNic(
            positive=True, vm=conf.VM_NAME[0], nic=cls.vm_nic, plugged="false"
        ):
            raise conf.NET_EXCEPTION("Couldn't unplug NIC")

        for i in range(2):
            if not ll_vms.removeNic(
                positive=True, vm=conf.VM_NAME[i], nic=cls.vm_nic
            ):
                logger.error(
                    "Cannot remove NIC from VM %s ", conf.VM_NAME[i]
                )
        super(TestMultiHostCase05, cls).teardown_class()


class TestMultiHostCase06(TestMultiHostTestCaseBase):
    """
    Update network when template is using it:
    1) Negative: Try to update network from VM to non-VM
    2) Positive: Try to change MTU on net when template is using it
    3) Positive: Try to change VLAN on net when template is using it
    """
    __test__ = True
    net = conf.NETS[6][0]
    vm_nic = conf.NIC_NAME[1]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = conf.VLAN_IDS[3]

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster,Host and Template
        """
        dict_dc1 = {
            cls.net: {
                "nic": 1
            }
        }

        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOST_0, network_dict=dict_dc1, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

        if not ll_templates.addTemplateNic(
            positive=True, template=conf.TEMPLATE_NAME_0, name=cls.vm_nic,
            data_center=conf.DC_NAME_0, network=cls.net
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4073")
    def test_update_net_on_template(self):
        """
        1) Negative: Try to update network from VM to non-VM
        2) Positive: Try to change MTU on net when template is using it
        3) Positive: Try to change VLAN on net when template is using it
        """
        if not ll_networks.updateNetwork(
            positive=False, network=self.net, data_center=conf.DC_NAME_0,
            usages=""
        ):
            raise conf.NET_EXCEPTION()

        helper.update_network_and_check_changes(
            net=self.net, mtu=self.mtu_9000
        )
        helper.update_network_and_check_changes(
            net=self.net, vlan_id=self.vlan
        )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default
        Remove NIC from Template
        Remove network from the setup.
        """
        cls.restore_mtu = True
        ll_templates.removeTemplateNic(
            positive=True, template=conf.TEMPLATE_NAME_0, nic=cls.vm_nic
        )
        super(TestMultiHostCase06, cls).teardown_class()


class TestMultiHostCase07(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC/Cluster
    Make sure all the changes exist on both Hosts
    """
    __test__ = True
    net = conf.NETS[7][0]
    mtu_9000 = conf.MTU[0]
    mtu_1500 = conf.MTU[-1]
    vlan = conf.VLAN_IDS[4]

    @classmethod
    def setup_class(cls):
        """
        Create network on DC/Cluster/Hosts
        """
        local_dict = {
            cls.net: {
                "nic": 1
            }
        }
        if not hl_networks.createAndAttachNetworkSN(
            host=conf.VDS_HOSTS[:2], network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION()

    @polarion("RHEVM3-4078")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """
        helper.update_network_and_check_changes(
            net=self.net, vlan_id=self.vlan,
            mtu=self.mtu_9000, hosts=conf.HOSTS_LIST,
            vds_hosts=conf.VDS_HOSTS_LIST, matches=2
        )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default on both Hosts
        Remove network from the setup.
        """
        cls.restore_mtu = True


class TestMultiHostCase08(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN and MTU when several hosts reside under
    the same DC, but under different Clusters of the same DC
    Make sure all the changes exist on both Hosts
    """
    __test__ = True
    cl_name2 = "new_CL_case08"

    @classmethod
    def setup_class(cls):
        """
        Move the second Host to different Cluster under the same DC
        Create network on DC/Clusters/Hosts
        """

        logger.info(
            "Add additional Cluster %s under DC %s ",
            cls.cl_name2, conf.DC_NAME_0
        )
        if not ll_clusters.addCluster(
            positive=True, name=cls.cl_name2, cpu=conf.CPU_NAME,
            data_center=conf.DC_NAME_0, version=conf.COMP_VERSION
        ):
            raise conf.NET_EXCEPTION(
                "Cannot add Cluster %s under DC %s " %
                (cls.cl_name2, conf.DC_NAME_0)
            )

        logger.info(
            "Deactivate host %s, move it to Cluster %s and reactivate it",
            conf.HOSTS[1], cls.cl_name2
        )
        if not ll_hosts.deactivateHost(True, host=conf.HOSTS[1]):
            raise conf.NET_EXCEPTION(
                "Cannot deactivate host %s" % conf.HOSTS[1]
            )
        if not ll_hosts.updateHost(
            True, host=conf.HOSTS[1], cluster=cls.cl_name2
        ):
            raise conf.NET_EXCEPTION(
                "Cannot move host %s to Cluster %s" %
                (conf.HOSTS[1], cls.cl_name2)
            )
        if not ll_hosts.activateHost(True, host=conf.HOSTS[1]):
            raise conf.NET_EXCEPTION(
                "Cannot activate host %s" % conf.HOSTS[1]
            )

        local_dict = {
            conf.VLAN_NETWORKS[0]:
                {"nic": 1,
                 "required": "false"
                 }
        }
        logger.info(
            "Attach network %s to DC %s, Cluster %s, host %s and %s",
            conf.VLAN_NETWORKS[0], conf.DC_NAME_0,
            conf.CLUSTER_NAME_0, conf.VDS_HOST_0, conf.VDS_HOSTS[1]
        )
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_0, cluster=conf.CLUSTER_NAME_0,
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create and attach network %s to host %s" %
                (conf.VLAN_NETWORKS[0], conf.VDS_HOST_0)
            )
        if not hl_networks.createAndAttachNetworkSN(
            cluster=cls.cl_name2, host=conf.VDS_HOSTS[1],
            network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot create and attach network %s to host %s" %
                (conf.VLAN_NETWORKS[0], conf.VDS_HOSTS[1])
            )

    @polarion("RHEVM3-4077")
    def test_update_with_vlan_mtu(self):
        """
        1) Update network with VLAN 162
        3) Update network with MTU 9000
        4) Check that the both Hosts were updated with VLAN 162 and MTU 9000
        """
        mtu_dict1 = {"mtu": conf.MTU[0]}
        sample1 = []

        logger.info(
            "Update network with VLAN %s and MTU %s ",
            conf.VLAN_ID[0], conf.MTU[0]
        )
        if not ll_networks.updateNetwork(
            True, network=conf.VLAN_NETWORKS[0],
            data_center=conf.DC_NAME_0, vlan_id=conf.VLAN_ID[0],
            mtu=conf.MTU[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update network to be tagged and to have MTU in "
                "one action"
            )

        logger.info(
            "Check that both Hosts are updated with correct MTU value"
        )
        for host, nic in zip(
            conf.HOSTS[:2], (conf.HOST_0_NICS[1], conf.HOST_1_NICS[1])
        ):
            sample1.append(
                apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=hl_networks.check_host_nic_params,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                raise conf.NET_EXCEPTION("Couldn't get correct MTU on host")

        logger.info("Check that the MTU change is reflected to both Hosts")
        for vds_host in conf.VDS_HOSTS_LIST:
            nic = vds_host.nics[1]
            logger.info(
                "Checking logical layer of bridged network %s on host %s",
                conf.VLAN_NETWORKS[0], vds_host.fqdn
            )
            if not test_utils.check_mtu(
                vds_resource=vds_host, mtu=conf.MTU[0],
                physical_layer=False, network=conf.VLAN_NETWORKS[0], nic=nic
            ):
                raise conf.NET_EXCEPTION(
                    "Logical layer: MTU should be %s" % conf.MTU[0]
                )

            logger.info(
                "Checking physical layer of bridged network %s on host %s",
                conf.NETWORKS[0], vds_host.fqdn
            )
            if not test_utils.check_mtu(
                vds_resource=vds_host, mtu=conf.MTU[0], nic=nic
            ):
                raise conf.NET_EXCEPTION(
                    "Physical layer: MTU should be %s" % conf.MTU[0]
                )

            logger.info(
                "Check that the VLAN change is reflected to both Hosts"
            )
            if not ll_networks.is_vlan_on_host_network(
                vds_resource=vds_host, interface=nic, vlan=conf.VLAN_ID[0]
            ):
                raise conf.NET_EXCEPTION(
                    "Host %s was not updated with correct VLAN %s" %
                    (vds_host.fqdn, conf.VLAN_ID[0])
                )

    @classmethod
    def teardown_class(cls):
        """
        Update MTU to default on both Hosts
        Remove network from the setup.
        Return Host to original Cluster
        Remove Cluster
        """

        mtu_dict1 = {"mtu": conf.MTU[-1]}
        sample1 = []

        logger.info(
            "Update network %s with MTU %s", conf.VLAN_NETWORKS[0],
            conf.MTU[-1]
        )
        if not ll_networks.updateNetwork(
            True, network=conf.VLAN_NETWORKS[0],
            data_center=conf.DC_NAME_0, mtu=conf.MTU[-1]
        ):
            logger.error(
                "Couldn't update  network with MTU %s ", conf.MTU[-1]
            )

        logger.info("Check correct MTU on both Hosts")
        for host, nic in zip(
            conf.HOSTS[:2], (conf.HOST_0_NICS[1], conf.HOST_1_NICS[1])
        ):
            sample1.append(
                apis_utils.TimeoutingSampler(
                    timeout=conf.SAMPLER_TIMEOUT,
                    sleep=1,
                    func=hl_networks.check_host_nic_params,
                    host=host,
                    nic=nic,
                    **mtu_dict1
                )
            )
        for i in range(2):
            if not sample1[i].waitForFuncStatus(result=True):
                logger.error(
                    "Couldn't get correct MTU (%s) on host %s and %s",
                    conf.MTU[-1], conf.HOST_NAME_0, conf.HOSTS[1])

        logger.info("Remove network %s from setup", conf.VLAN_NETWORKS[0])
        if not hl_networks.remove_net_from_setup(
            host=conf.HOSTS[:2], network=[conf.VLAN_NETWORKS[0]]
        ):
            logger.error(
                "Cannot remove network %s from setup", conf.VLAN_NETWORKS[0]
            )
        logger.info(
            "Deactivate host %s, move it to its original cluster %s and "
            "reactivate it", conf.HOSTS[1], conf.CLUSTER_NAME_0
        )
        if not ll_hosts.deactivateHost(True, host=conf.HOSTS[1]):
            logger.error(
                "Cannot deactivate host %s", conf.HOSTS[1]
            )

        if not ll_hosts.updateHost(
                True, host=conf.HOSTS[1], cluster=conf.CLUSTER_NAME_0):
                logger.error(
                    "Cannot move host %s to Cluster %s",
                    conf.HOSTS[1], conf.CLUSTER_NAME_0
                )
        if not ll_hosts.activateHost(True, host=conf.HOSTS[1]):
            logger.error(
                "Cannot activate host %s in cluster %s",
                conf.HOSTS[1], conf.CLUSTER_NAME_0)

        if not ll_clusters.removeCluster(True, cls.cl_name2):
            logger.error(
                "Cannot remove cluster %s from setup", cls.cl_name2
            )


class TestMultiHostCase09(TestMultiHostTestCaseBase):
    """
    Update untagged network with VLAN when that network is attached to
    the Host bond
    Update tagged network with another VLAN when that network is attached to
    the Host bond
    Update tagged network to be untagged when that network is attached to
    the Host bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create untagged network on DC/Cluster/Host
        """
        local_dict = {
            conf.VLAN_NETWORKS[0]: {
                "nic": conf.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster and bond on Host")
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_0, cluster=conf.CLUSTER_NAME_0,
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION("Cannot create and attach network")

    @polarion("RHEVM3-4069")
    def test_update_with_vlan(self):
        """
        There is a bz for updating network to be tagged - 1081489

        1) Update network with VLAN 162
        2) Check that the Host was updated with VLAN 162
        3) Update network with VLAN 163
        4) Check that the Host was updated with VLAN 163
        5) Update network with VLAN 163 to be untagged
        6) Check that the Host was updated as well
        """
        vlan_dict1 = {"vlan_id": conf.VLAN_ID[0]}
        vlan_dict2 = {"vlan_id": conf.VLAN_ID[1]}

        logger.info("Update network with VLAN %s", conf.VLAN_ID[0])
        if not ll_networks.updateNetwork(
            True, network=conf.VLAN_NETWORKS[0],
            data_center=conf.DC_NAME_0, vlan_id=conf.VLAN_ID[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update network to be tagged with VLAN %s" %
                conf.VLAN_ID[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **vlan_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not ll_networks.is_vlan_on_host_network(
            vds_resource=conf.VDS_HOST_0, interface=conf.BOND[0],
            vlan=conf.VLAN_ID[0]
        ):
            raise conf.NET_EXCEPTION(
                "Host %s was not updated with correct VLAN %s" %
                (conf.HOST_NAME_0, conf.VLAN_ID[0])
            )

        logger.info("Update network with VLAN %s", conf.VLAN_ID[1])
        if not ll_networks.updateNetwork(
            True, network=conf.VLAN_NETWORKS[0],
            data_center=conf.DC_NAME_0, vlan_id=conf.VLAN_ID[1]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update network to be tagged with VLAN %s" %
                conf.VLAN_ID[1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample2 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **vlan_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Couldn't get correct VLAN interface on host"
            )

        logger.info("Check that the change is reflected to Host")
        if not ll_networks.is_vlan_on_host_network(
            vds_resource=conf.VDS_HOST_0, interface=conf.BOND[0],
            vlan=conf.VLAN_ID[1]
        ):
            raise conf.NET_EXCEPTION(
                "Host %s was not updated with correct VLAN %s" %
                (conf.HOST_NAME_0, conf.VLAN_ID[1])
            )

        logger.info("Update network to be untagged")
        if not ll_networks.updateNetwork(
            True, network=conf.VLAN_NETWORKS[0],
            data_center=conf.DC_NAME_0, vlan_id=None
        ):
            raise conf.NET_EXCEPTION("Cannot update network to be untagged")

        logger.info("Wait till the Host is updated with the change")
        if not sample2.waitForFuncStatus(result=False):
            raise conf.NET_EXCEPTION(
                "Could get VLAN interface on host but shouldn't"
            )

        logger.info("Check that the change is reflected to Host")
        if ll_networks.is_vlan_on_host_network(
            vds_resource=conf.VDS_HOST_0, interface=conf.BOND[0],
            vlan=conf.VLAN_ID[1]
        ):
            raise conf.NET_EXCEPTION(
                "Network on Host %s was not updated to be untagged" %
                conf.HOST_NAME_0
            )


class TestMultiHostCase10(TestMultiHostTestCaseBase):
    """
    Update network with the default MTU to the new MTU when that network
    is attached to the Host bond
    Update network with another MTU value when that network is attached to
    the Host bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """
        local_dict = {
            conf.NETWORKS[0]: {
                "nic": conf.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_0, cluster=conf.CLUSTER_NAME_0,
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION("Cannot create and attach network")

    @polarion("RHEVM3-4068")
    def test_update_with_mtu(self):
        """
        1) Update network with MTU 9000
        2) Check that the Host was updated with MTU 9000
        3) Update network with MTU 1500
        4) Check that the Host was updated with MTU 1500
        """
        mtu_dict1 = {"mtu": conf.MTU[0]}
        mtu_dict2 = {"mtu": conf.MTU[-1]}

        logger.info("Update network with MTU %s", conf.MTU[0])
        if not ll_networks.updateNetwork(
            True, network=conf.NETWORKS[0], data_center=conf.DC_NAME_0,
            mtu=conf.MTU[0]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update  network with  MTU %s" % conf.MTU[0]
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **mtu_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s"
            % (conf.NETWORKS[0], conf.HOST_NAME_0)
        )
        if not test_utils.check_mtu(
            vds_resource=conf.VDS_HOST_0, mtu=conf.MTU[0],
            physical_layer=False, network=conf.NETWORKS[0],
            nic=conf.BOND[0]
        ):
            raise conf.NET_EXCEPTION(
                "Logical layer: MTU should be %s" % conf.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s"
            % (conf.NETWORKS[0], conf.HOST_NAME_0)
        )
        if not test_utils.check_mtu(
            vds_resource=conf.VDS_HOST_0, mtu=conf.MTU[0],
            nic=conf.BOND[0]
        ):
            raise conf.NET_EXCEPTION(
                "Physical layer: MTU should be %s" % conf.MTU[0]
            )

        logger.info("Update MTU network with MTU %s", conf.MTU[-1])
        if not ll_networks.updateNetwork(
            True, network=conf.NETWORKS[0], data_center=conf.DC_NAME_0,
            mtu=conf.MTU[-1]
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update network with MTU %s" % conf.MTU[-1]
            )

        logger.info("Wait till the Host is updated with the change")
        sample2 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **mtu_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION("Couldn't get correct MTU on host")

        logger.info("Check that the change is reflected to Host")
        logger.info(
            "Checking logical layer of bridged network %s on host %s"
            % (conf.NETWORKS[0], conf.HOST_NAME_0)
        )
        if not test_utils.check_mtu(
            vds_resource=conf.VDS_HOST_0, mtu=conf.MTU[-1],
            physical_layer=False, network=conf.NETWORKS[0],
            nic=conf.BOND[0]
        ):
            raise conf.NET_EXCEPTION(
                "Logical layer: MTU should be %s" % conf.MTU[0]
            )

        logger.info(
            "Checking physical layer of bridged network %s on host %s"
            % (conf.NETWORKS[0], conf.HOST_NAME_0)
        )
        if not test_utils.check_mtu(
            vds_resource=conf.VDS_HOST_0, mtu=conf.MTU[-1],
            nic=conf.BOND[0]
        ):
            raise conf.NET_EXCEPTION(
                "Physical layer: MTU should be %s" % conf.MTU[0]
            )


class TestMultiHostCase11(TestMultiHostTestCaseBase):
    """
    Update VM network to be non-VM network when that network is attached to
    the Host bond
    Update non-VM network to be VM network when that network is attached to
    the Host bond
    """
    __test__ = True

    @classmethod
    def setup_class(cls):
        """
        Create and attach network on DC, Cluster and the host
        """

        local_dict = {
            conf.NETWORKS[0]: {
                "nic": conf.BOND[0], "slaves": [2, 3], "required": "false"
            }
        }

        logger.info("Attach network to DC/Cluster/Host")
        if not hl_networks.createAndAttachNetworkSN(
            data_center=conf.DC_NAME_0, cluster=conf.CLUSTER_NAME_0,
            host=conf.VDS_HOST_0, network_dict=local_dict, auto_nics=[0]
        ):
            raise conf.NET_EXCEPTION("Cannot create and attach network")

    @polarion("RHEVM3-4081")
    def test_update_with_non_vm_nonvm(self):
        """
        Fails due to existing bug - 1082275
        1) Update network to be non-VM network
        2) Check that the Host was updated accordingly
        3) Update network to be VM network
        4) Check that the Host was updated accordingly
        """
        bridge_dict1 = {"bridge": False}
        bridge_dict2 = {"bridge": True}

        logger.info(
            "Update network %s to be non-VM network", conf.NETWORKS[0]
        )
        if not ll_networks.updateNetwork(
            True, network=conf.NETWORKS[0], data_center=conf.DC_NAME_0,
            usages=""
        ):
            raise conf.NET_EXCEPTION(
                "Cannot update network to be non-VM net"
            )

        logger.info("Wait till the Host is updated with the change")
        sample1 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **bridge_dict1
        )
        if not sample1.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Network is VM network and should be Non-VM"
            )

        logger.info("Check that the change is reflected to Host")
        if ll_networks.is_host_network_is_vm(
            vds_resource=conf.VDS_HOST_0, net_name=conf.NETWORKS[0]
        ):
            raise conf.NET_EXCEPTION(
                "Network on host %s was not updated to be non-VM network" %
                conf.HOST_NAME_0
            )

        logger.info("Update network %s to be VM network", conf.NETWORKS[0])
        time.sleep(conf.SLEEP)
        if not ll_networks.updateNetwork(
            True, network=conf.NETWORKS[0], data_center=conf.DC_NAME_0,
            usages="vm"
        ):
            raise conf.NET_EXCEPTION("Cannot update network to be VM net")

        logger.info("Wait till the Host is updated with the change")
        sample2 = apis_utils.TimeoutingSampler(
            timeout=conf.SAMPLER_TIMEOUT,
            sleep=1,
            func=hl_networks.check_host_nic_params,
            host=conf.HOST_NAME_0,
            nic=conf.BOND[0],
            **bridge_dict2
        )
        if not sample2.waitForFuncStatus(result=True):
            raise conf.NET_EXCEPTION(
                "Network is not a VM network but should be"
            )

        logger.info("Check that the change is reflected to Host")
        if not ll_networks.is_host_network_is_vm(
            vds_resource=conf.VDS_HOST_0, net_name=conf.NETWORKS[0]
        ):
            raise conf.NET_EXCEPTION(
                "Network on host %s was not updated to be VM network" %
                conf.HOST_NAME_0
            )
