#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Module that handles SRIOV NICs
"""

import logging
from art.core_api import apis_utils
from art.test_handler import exceptions
from art.rhevm_api.utils import test_utils
import art.rhevm_api.tests_lib.low_level.hosts as ll_hosts
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
import art.rhevm_api.tests_lib.low_level.general as ll_general

PF_LABEL_API = test_utils.get_api(
    "network_label", "virtualfunctionallowedlabels"
)
PF_NETWORK_API = test_utils.get_api(
    "network", "virtualfunctionallowednetworks"
)
DUMMY_NIC = "dummy"

logger = logging.getLogger("art.ll_lib.sriov")


class SriovHostNics(object):
    """
    Class handles SR-IOV capable Host NICs
    """

    def __init__(self, host):
        """
        Initializes object of class for SR-IOV capable host NICs

        Args:
            host (str): Host name
        """
        self.host = host
        self.host_nics = self.get_host_nics()

    def get_host_nics(self):
        """
        List of network interfaces which were recognized on host

        Returns:
            list: Host NICs
        """
        host_obj = ll_hosts.get_host_object(host_name=self.host)
        host_nics = ll_hosts.get_host_nics_list(
            host=host_obj, all_content=True
        )
        return filter(
            lambda x: (DUMMY_NIC or "dpdk") not in x.name, host_nics
        )

    def get_all_pf_nics_objects(self):
        """
        Get all PF host NICs objects

        Return:
            list: List of all PF objects
        """
        pfs_nics = list()
        logger.info(
            "Get all SR-IOV NICs objects (PFs) from host %s", self.host
        )
        for nic in self.host_nics:
            nic_name = nic.get_name()
            try:
                SriovNicPF(host=self.host, nic=nic_name)
                pfs_nics.append(nic)
            except exceptions.SriovException:
                continue

        if not pfs_nics:
            raise exceptions.SriovException(
                "Host %s doesn't have SR-IOV NICs" % self.host
            )
        return pfs_nics

    def get_all_vf_nics_objects(self):
        """
        Get all VF host NICs objects

        Returns:
            list: List of all VF objects
        """
        vfs_nics = list()
        logger.info(
            "Get all SR-IOV NICs objects (VFs) from host %s", self.host
        )
        for nic in self.host_nics:
            nic_name = nic.get_name()
            try:
                SriovNicVF(host=self.host, nic=nic_name)
                vfs_nics.append(nic)
            except exceptions.SriovException:
                continue

        return vfs_nics

    def get_all_pf_nics_names(self):
        """
        Get all PF nics names

        Returns:
            list: List of all PF names
        """
        return sorted(
            [pf.get_name() for pf in self.get_all_pf_nics_objects()]
        )

    def get_all_vf_nics_names(self):
        """
        Get all VF nics names

        Returns:
            list: List of all VF names
        """
        return sorted(
            [vf.get_name() for vf in self.get_all_vf_nics_objects()]
        )


class SriovNic(object):
    """
    Class handles SR-IOV capable NIC
    """
    update_vf_action = "updatevirtualfunctionsconfiguration"
    vf_allowed_labels_api = "virtualfunctionallowedlabels"
    vf_allowed_networks_api = "virtualfunctionallowednetworks"

    def __init__(self, host, nic):
        """
        Initializes object of class for SR-IOV capable NIC

        Args:
            host (str): Host name
            nic (str): NIC name
        """
        self.update_nic = False
        self.host = host
        self.nic_name = nic
        self.host_obj = ll_hosts.get_host_object(host_name=self.host)
        self.nic_obj = ll_hosts.get_host_nic(
            host=self.host_obj, nic=self.nic_name, all_content=True
        )
        self.vf_config = self.nic_obj.get_virtual_functions_configuration()
        self.vf = self._is_nic_vf()
        self.pf = self._is_nic_pf()

    def _is_nic_pf(self):
        """
        Check if NIC is PF

        Returns:
            bool: True if NIC is PF else False
        """
        return bool(self.vf_config)

    def _is_nic_vf(self):
        """
        Check if NIC is VF

        Returns:
            bool: True if NIC is VF else False
        """
        return bool(self.nic_obj.get_physical_function())


class SriovNicVF(SriovNic):
    """
    Class handles SR-IOV capable VF NICs
    """
    def __init__(self, host, nic):
        """
        Args:
            host (str): Host name
            nic (str): NIC name
        """
        super(SriovNicVF, self).__init__(host, nic)
        if not self.vf:
            raise exceptions.SriovException(
                "NIC %s is not VF" % self.nic_name
            )

    def get_pf_of_vf(self):
        """
        Get the PF of the VF

        Returns:
            HostNic: PF NIC object
        """
        logger.info("Get PF for %s", self.nic_name)
        return self.nic_obj.get_physical_function()


class SriovNicPF(SriovNic):
    """
    Class handles SR-IOV capable PF NICs
    """
    def __init__(self, host, nic):
        """
        Args:
            host (str): Host name
            nic (str): NIC name
        """
        super(SriovNicPF, self).__init__(host, nic)
        if not self.pf:
            raise exceptions.SriovException(
                "NIC %s is not PF" % self.nic_name
            )
        self.vf_label_href = (
            "%s/%s" % (self.nic_obj.href, self.vf_allowed_labels_api)
        )
        self.vf_network_href = (
            "%s/%s" % (self.nic_obj.href, self.vf_allowed_networks_api)
        )

    def _update_nic_obj(self):
        """
        Update HostNic object if HostNic had changed
        """
        if self.update_nic:
            self.nic_obj = ll_hosts.get_host_nic(
                host=self.host_obj, nic=self.nic_name, all_content=True
            )
            self.vf_config = self.nic_obj.get_virtual_functions_configuration()
        return self.update_nic

    def _get_label_obj_by_id(self, label_id):
        """
        Get label_id object by ID

        Args:
            label_id (str): Label ID

        Returns:
            Label: Label object

        Raises:
            SriovException: If label not found
        """
        try:
            return filter(
                lambda x: x.id == label_id, self.get_allowed_labels_obj()
            )[0]
        except IndexError:
            raise exceptions.SriovException(
                "%s is not found among %s allowed labels" %
                (label_id, self.host)
            )

    def _get_network_obj_by_name(self, network_name):
        """
        Get network object by name

        Args:
            network_name (str): Network name

        Returns:
            Network: Network object

        Raises:
            SriovException: If network not found
        """
        try:
            return filter(
                lambda x: ll_general.get_object_name_by_id(
                    ll_networks.NET_API, x.id
                ) == network_name, self.get_allowed_networks_obj()
            )[0]
        except IndexError:
            raise exceptions.SriovException(
                "%s is not found among %s allowed networks" %
                (network_name, self.host)
            )

    def get_all_vf_objects(self):
        """
        Get all VF objects for PF

        Returns:
            list: List of all VF objects for PF
        """
        all_vfs = SriovHostNics(host=self.host).get_all_vf_nics_objects()
        all_nic_vfs = list()
        for vf in all_vfs:
            vf_pf = vf.get_physical_function()
            if vf_pf and vf and vf_pf.get_id() == self.nic_obj.get_id():
                all_nic_vfs.append(vf)
        return all_nic_vfs

    def get_all_vf_names(self):
        """
        Get all VF names for PF

        Returns:
            list: List of all  VF names for PF
        """
        return [vf.get_name() for vf in self.get_all_vf_objects()]

    def set_sriov_host_nic_params(self, **kwargs):
        """
        Update host NIC with SR-IOV params

        Args:
            kwargs (dict): SR-IOV params

        Keyword arguments:
            number_of_virtual_functions (int): Set number of virtual functions
            all_networks_allowed (bool): Set all networks allowed

        Returns:
            bool: True if operation succeed False otherwise

        """
        vf_obj = apis_utils.data_st.HostNicVirtualFunctionsConfiguration()
        for k, v in kwargs.iteritems():
            setattr(vf_obj, k, v)

        logger.info("Set %s to %s on %s", kwargs, self.nic_name, self.host)
        self.update_nic = bool(
            ll_networks.HOST_NICS_API.syncAction(
                entity=self.nic_obj, action=self.update_vf_action,
                positive=True, virtual_functions_configuration=vf_obj
            )
        )
        if not self.update_nic:
            logger.error(
                "Failed to set %s to %s on %s", kwargs, self.nic_name,
                self.host
            )
        return self._update_nic_obj()

    def get_max_number_of_vf(self):
        """
        Get max number of virtual functions

        Returns:
            int: Max number of virtual functions
        """
        logger.info("Get max number of VF on %s", self.nic_name)
        return self.vf_config.get_max_number_of_virtual_functions()

    def get_number_of_vf(self):
        """
        Get number of virtual functions

        Returns:
            int: Number of virtual functions
        """
        logger.info("Get number of VF on %s", self.nic_name)
        return self.vf_config.get_number_of_virtual_functions()

    def get_all_networks_allowed(self):
        """
        Get all_networks_allowed flag
        If all_networks_allowed is True all networks are allowed to use this vf

        Returns:
            bool: True if operation succeed False otherwise
        """
        logger.info("Get all_networks_allowed property for %s", self.nic_name)
        return self.vf_config.get_all_networks_allowed()

    def set_number_of_vf(self, num_of_vf):
        """
        Set number of virtual functions

        Args:
            num_of_vf (int): Number of virtual functions

        Returns:
            bool: True if operation succeed False otherwise
        """
        kwargs = {
            "number_of_virtual_functions": num_of_vf
        }
        return self.set_sriov_host_nic_params(**kwargs)

    def set_all_networks_allowed(self, enable):
        """
        Set all_networks_allowed flag

        Args:
            enable (bool): True to enable, False otherwise

        Returns:
            bool: True if operation succeed False otherwise
        """
        kwargs = {
            "all_networks_allowed": enable
        }
        return self.set_sriov_host_nic_params(**kwargs)

    def delete_allowed_label(self, label_id):
        """
        Delete label_id from allowed PF

        Args:
            label_id (str): Label name to delete

        Returns:
            True if operation succeed False otherwise
        """
        label_obj = self._get_label_obj_by_id(label_id=label_id)
        logger.info("Delete label from allowed labels for %s", self.nic_name)
        self.update_nic = PF_LABEL_API.delete(entity=label_obj, positive=True)
        return self._update_nic_obj()

    def delete_allowed_network(self, network):
        """
        Delete network from allowed PF

        Args:
            network (str): Network name to delete

        Returns:
            True if operation succeed False otherwise
        """
        network_obj = self._get_network_obj_by_name(network_name=network)
        logger.info(
            "Delete network from allowed networks for %s", self.nic_name
        )
        self.update_nic = PF_NETWORK_API.delete(
            entity=network_obj, positive=True
        )
        return self._update_nic_obj()

    def add_label_to_allowed_labels(self, label):
        """
        Add label to allowed labels on PF

        Args:
            label (str): Label name

        Returns:
            True if operation succeed False otherwise

        Raises:
            SriovException: If all_networks_allowed is not enabled
        """
        if self.get_all_networks_allowed():
            raise exceptions.SriovException(
                "all_networks_allowed must be False in order to add a label "
                "to allowed labels"
            )
        label_obj = ll_networks.create_label(label=label)
        logger.info("Add label to allowed labels for %s", self.nic_name)
        self.update_nic = PF_LABEL_API.create(
            entity=label_obj, positive=True, collection=self.vf_label_href,
            coll_elm_name="network_label", async=True
        )
        return self._update_nic_obj()

    def add_network_to_allowed_networks(self, network, data_center=None):
        """
        Add network to allowed networks on PF

        Args:
            network (str): Network name
            data_center (str): DC name where the network is

        Returns:
            True if operation succeed False otherwise

        Raises:
            SriovException: If all_networks_allowed is not enabled
        """
        if self.get_all_networks_allowed():
            raise exceptions.SriovException(
                "all_networks_allowed must be False in order to add a network "
                "to allowed networks"
            )
        network_obj = ll_networks.find_network(
            network=network, data_center=data_center
        )
        logger.info("Add network to allowed networks for %s", self.nic_name)
        self.update_nic = PF_NETWORK_API.create(
            entity=network_obj, positive=True, collection=self.vf_network_href,
            coll_elm_name="network", async=True
        )
        return self._update_nic_obj()

    def get_allowed_networks_obj(self):
        """
        Get PF allowed networks objects

        Returns:
            list: Allowed networks objects
        """
        logger.info("Get all allowed networks objects for %s", self.nic_name)
        return ll_networks.HOST_NICS_API.getElemFromLink(
            elm=self.nic_obj, link_name=self.vf_allowed_networks_api,
            attr="network"
        )

    def get_allowed_networks(self):
        """
        Get PF allowed networks names

        Returns:
            list: Allowed networks names
        """
        logger.info("Get all allowed networks for %s", self.nic_name)
        return [
            ll_general.get_object_name_by_id(
                ll_networks.NET_API, net.id
            ) for net in self.get_allowed_networks_obj()
            ]

    def get_allowed_labels(self):
        """
        Get PF allowed labels IDs

        Returns:
            list: Allowed labels IDs
        """
        logger.info("Get all allowed labels for %s", self.nic_name)
        return [lb.id for lb in self.get_allowed_labels_obj()]

    def get_allowed_labels_obj(self):
        """
        Get PF allowed labels objects

        Returns:
            list: Allowed labels objects
        """
        logger.info("Get all allowed labels objects for %s", self.nic_name)
        return ll_networks.HOST_NICS_API.getElemFromLink(
            elm=self.nic_obj, link_name=self.vf_allowed_labels_api,
            attr="network_label"
        )
