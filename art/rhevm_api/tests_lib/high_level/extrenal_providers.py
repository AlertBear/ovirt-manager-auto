#!/usr/bin/env python
# Copyright (C) 2018 Red Hat, Inc.
#
# This is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA, or see the FSF site: http://www.fsf.org.

from keystoneauth1 import identity, session
from neutronclient.common.exceptions import BadRequest
from neutronclient.v2_0 import client

from art.rhevm_api.tests_lib.low_level import general as ll_general


class OvnProvider(client.Client):
    """
    Manage OVN provider
    """
    def __init__(self, username, password, auth_url):
        """
        Initialized connection to the provider.

        Args:
            username (str): Provider username
            password (str): Provider password
            auth_url (str): Provider authentication URL
        """
        auth = identity.Password(
            auth_url=auth_url, username=username, password=password
        )
        sess = session.Session(auth=auth, verify=False)
        super(OvnProvider, self).__init__(session=sess)

    @ll_general.generate_logs(step=True)
    def get_all_networks(self):
        """
        Get all networks

        Returns:
            list: List of all networks
        """
        return self.list_networks().get("networks")

    @ll_general.generate_logs(step=True)
    def get_all_subnets(self):
        """
        Get all networks

        Returns:
            list: List of all networks
        """
        return self.list_subnets().get("subnets")

    @ll_general.generate_logs()
    def get_id_by_name(self, name, collection):
        """
        Get object ID by name from collection

        Args:
            name (str): Name to search for
            collection (list): List of objects

        Returns:
            str: ID if name found, else empty string
        """
        id_ = [
            col.get("id") for col in collection if col.get("name") == name
        ]
        return id_[0] if id_ else ""

    @ll_general.generate_logs(step=True)
    def add_network(self, network):
        """
        Create network

        Args:
            network (dict): Network dict to create

        Returns:
            str: Network ID or empty string
        """
        network_name = network.get("name")
        try:
            self.create_network({"network": network})
        except BadRequest:
            return ""

        return self.get_network_id(network=network_name)

    @ll_general.generate_logs(step=True)
    def add_subnet(self, subnet, network=None):
        """
        Create subnet

        Args:
            subnet (dict): Subnet dict to create
            network (str): Network name for the subnet

        Returns:
            str: Subnet ID or empty string
        """
        subnet_name = subnet.get("name")
        network_id = self.get_network_id(network=network)

        if not network_id:
            return ""

        subnet["network_id"] = network_id
        try:
            self.create_subnet({"subnet": subnet})
        except BadRequest:
            return ""

        return self.get_subnet_id(subnet=subnet_name)

    @ll_general.generate_logs(step=True)
    def get_network_id(self, network):
        """
        Get network ID

        Args:
            network (str): Network name

        Returns:
            str: Network ID
        """
        networks = self.get_all_networks()
        return self.get_id_by_name(name=network, collection=networks)

    @ll_general.generate_logs(step=True)
    def get_subnet_id(self, subnet):
        """
        Get subnet ID

        Args:
            subnet (str): Subnet name

        Returns:
            str: Subnet ID
        """
        subnets = self.get_all_subnets()
        return self.get_id_by_name(name=subnet, collection=subnets)
