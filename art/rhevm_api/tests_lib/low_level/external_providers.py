#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External network providers
"""

import logging

import requests

import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
import art.rhevm_api.tests_lib.low_level.general as ll_general
import art.rhevm_api.tests_lib.low_level.networks as ll_networks
from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api

CEPH = 'ceph'
AUTH_KEY = 'authenticationkey'
logger = logging.getLogger(__name__)


class OpenStackProvider(object):
    """
    Base class for Open Stack external providers
    """
    def __init__(
        self, provider_api_element_name, name, url, requires_authentication,
        username=None, password=None, authentication_url=None,
        tenant_name=None
    ):
        """
        OpenStackProvider class

        Args:
            provider_api_element_name (str): API element name
            name (str): Provider name
            url (str): Provider URL address
            requires_authentication (bool): True if to enable authentication
                with given username and password
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name

        """
        self._name = name
        self._url = url
        self._requires_authentication = requires_authentication
        self._username = username
        self._password = password
        self._authentication_url = authentication_url
        self._tenant_name = tenant_name

        # provider_name will be generated from child class name, it should be
        # same as in generated DS for specific provider
        self.provider_name = self.__class__.__name__
        self.open_stack_provider = getDS(self.provider_name)
        self._api = get_api(
            provider_api_element_name, self.provider_name.lower() + 's'
        )
        self.osp_obj = None
        self._is_connected = False

    def add(self):
        self._init()
        try:
            self.osp_obj, self._is_connected = self._api.create(
                self.osp_obj, positive=True
            )
        except TypeError:
            self._api.logger.warning("Unable to add %s", self.name)

        return self._is_connected

    def set_osp_obj(self):
        """
        Set External Provider object
        """
        self.osp_obj = self.find(openstack_ep=self.name)

    def find(self, openstack_ep, key='name'):
        """
        Get openstack ep object from engine by name or id

        :param openstack_ep: the openstack ep name/id
        :type openstack_ep: str
        :param key: key to look for ep, it can be name or id
        :type key: str
        :return: openstack ep object
        :raise: EntityNotFound
        """
        return self._api.find(openstack_ep, attribute=key)

    def get_openstack_ep_objects(self):
        """
        Get openstack ep objects from engine.

        :return: list of openstack ep objects
        """
        return self._api.get(absLink=False)

    def remove(self, openstack_ep, key='name'):
        """
        Remove openstack ep object from engine by name or id

        :param openstack_ep: the openstack ep name/id
        :type openstack_ep: str
        :param key: key to look for ep, it can be name or id
        :type key: str
        :return: True if ep was removed properly, False otherwise
        :rtype: bool
        :raise: EntityNotFound
        """
        log_info, log_error = ll_general.get_log_msg(
            log_action="Remove", obj_type=self.provider_name,
            obj_name=openstack_ep
        )
        logger.info(log_info)
        ep_obj = self.find(openstack_ep)
        res = self._api.delete(ep_obj, True)
        if not res:
            logger.error(log_error)
        return res

    def _init(self):
        self.osp_obj = self.open_stack_provider()
        self.osp_obj.set_name(self.name)
        self.osp_obj.set_url(self.url)
        self.osp_obj.set_requires_authentication(
            self.requires_authentication
        )
        self.osp_obj.set_username(self.username)
        self.osp_obj.set_password(self.password)
        self.osp_obj.set_authentication_url(
            self.authentication_url
        )
        self.osp_obj.set_tenant_name(self.tenant_name)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url):
        self._url = url

    @property
    def requires_authentication(self):
        return self._requires_authentication

    @requires_authentication.setter
    def requires_authentication(self, requires_authentication):
        self._requires_authentication = requires_authentication

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, username):
        self._username = username

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = password

    @property
    def authentication_url(self):
        return self._authentication_url

    @authentication_url.setter
    def authentication_url(self, authentication_url):
        self._authentication_url = authentication_url

    @property
    def tenant_name(self):
        return self._tenant_name

    @tenant_name.setter
    def tenant_name(self, tenant_name):
        self._tenant_name = tenant_name


class OpenStackImageProvider(OpenStackProvider):
    provider_api_element_name = 'openstack_image_provider'

    def __init__(
        self, name=None, url=None, requires_authentication=None, username=None,
        password=None, authentication_url=None, tenant_name=None
    ):
        """
        :param name: name
        :type name: str
        :param url: url of ep
        :type url: str
        :param requires_authentication: True if requires auth, False otherwise
        :type requires_authentication: bool
        :param username: username for auth
        :type username: str
        :param password: password for auth
        :type password: str
        :param authentication_url: auth URL
        :type authentication_url: str
        :param tenant_name: tenant name
        :type tenant_name: str
        """

        super(OpenStackImageProvider, self).__init__(
            self.provider_api_element_name, name, url, requires_authentication,
            username, password, authentication_url, tenant_name,
        )


class OpenStackVolumeProvider(OpenStackProvider):
    provider_api_element_name = 'openstack_volume_provider'
    cinder_key_ds = getDS('OpenstackVolumeAuthenticationKey')
    cinder_key_coll_name = 'openstack_volume_authentication_key'

    def __init__(
            self,
            name=None, url=None, requires_authentication=None, username=None,
            password=None, authentication_url=None, tenant_name=None,
            data_center=None, key_uuid=None, key_value=None
    ):
        """
        :param name: name
        :type name: str
        :param url: url of ep
        :type url: str
        :param requires_authentication: True if requires auth, False otherwise
        :type requires_authentication: bool
        :param username: username for auth
        :type username: str
        :param password: password for auth
        :type password: str
        :param authentication_url: auth URL
        :type authentication_url: str
        :param tenant_name: tenant name
        :type tenant_name: str
        :param data_center: data centrum
        :type data_center: DC object
        :param key_uuid: auth key uuid
        :type key_uuid: str
        :param key_value: auth key value
        :type key_value: str
        """

        super(OpenStackVolumeProvider, self).__init__(
            self.provider_api_element_name, name, url, requires_authentication,
            username, password, authentication_url, tenant_name,
        )
        self._data_center = data_center
        self.key_obj = None
        self.key_uuid = key_uuid
        self.key_value = key_value

    @property
    def data_center(self):
        return self._data_center

    @data_center.setter
    def data_center(self, data_center):
        self._data_center = data_center

    def _init(self):
        super(OpenStackVolumeProvider, self)._init()
        self.osp_obj.set_data_center(self.data_center)

    def add_ceph_auth_key(self, uuid, value, usage_type=CEPH):
        key_obj = self.cinder_key_ds()
        key_obj.set_uuid(uuid)
        key_obj.set_value(value)
        key_obj.set_usage_type(usage_type)

        key_collection = self._api.getElemFromLink(
            self.osp_obj, link_name=AUTH_KEY+'s', attr=AUTH_KEY, get_href=True
        )
        self.key_obj, created_success = self._api.create(
            key_obj, positive=True, collection=key_collection,
            coll_elm_name=self.cinder_key_coll_name, expectedEntity=key_obj
        )

        return created_success

    def add(self):
        if super(OpenStackVolumeProvider, self).add():
            if self.key_uuid and self.key_value:
                self.add_ceph_auth_key(self.key_uuid, self.key_value)
        return self._is_connected


def get_glance_ep_obj(glance_ep, key='name'):
    """
    Get glance ep object from engine by name or id

    :param glance_ep: the openstack ep name/id
    :type glance_ep: str
    :param key: key to look for ep, it can be name or id
    :type key: str
    :return: glance ep object
    :raise: EntityNotFound
    """
    osip = OpenStackImageProvider()
    return osip.find(glance_ep, key)


def get_glance_ep_objs():
    """
    Get glance ep objects from engine.

    :return: list of glance ep objects
    """
    osip = OpenStackImageProvider()
    return osip.get_openstack_ep_objects()


def get_glance_ep_objs_names():
    """
    Get glance ep objects names from engine.

    :return: list of glance ep objects names
    """
    return [ep.name for ep in get_glance_ep_objs()]


def remove_glance_ep(glance_ep, key='name'):
    """
    Remove glance ep object from engine by name or id

    :param glance_ep: the glance ep name/id
    :type glance_ep: str
    :param key: key to look for glance ep, it can be name or id
    :type key: str
    :return: True if glance ep was removed properly, False otherwise
    :rtype: bool
    :raise: EntityNotFound
    """
    osip = OpenStackImageProvider()
    return osip.remove(glance_ep, key)


def get_cinder_ep_obj(cinder_ep, key='name'):
    """
    Get cinder ep object from engine by name or id

    :param cinder_ep: the openstack ep name/id
    :type cinder_ep: str
    :param key: key to look for ep, it can be name or id
    :type key: str
    :return: cinder ep object
    :raise: EntityNotFound
    """
    osvp = OpenStackVolumeProvider()
    return osvp.find(cinder_ep, key)


def get_cinder_ep_objs():
    """
    Get cinder ep objects from engine.

    :return: list of cinder ep objects
    """
    osvp = OpenStackVolumeProvider()
    return osvp.get_openstack_ep_objects()


def get_cinder_ep_objs_names():
    """
    Get cinder ep objects names from engine.

    :return: list of cinder ep objects names
    """
    return [ep.name for ep in get_cinder_ep_objs()]


def remove_cinder_ep(cinder_ep, key='name'):
    """
    Remove cinder ep object from engine by name or id

    :param cinder_ep: the cinder ep name/id
    :type cinder_ep: str
    :param key: key to look for cinder ep, it can be name or id
    :type key: str
    :return: True if cinder ep was removed properly, False otherwise
    :rtype: bool
    :raise: EntityNotFound
    """
    osvp = OpenStackVolumeProvider()
    return osvp.remove(cinder_ep, key)


class ExternalNetworkProvider(OpenStackProvider):
    """
    External Network Provider
    """
    provider_api_element_name = "external_network_provider"

    def __init__(
        self, provider_api_element_name, name, url, requires_authentication,
        username=None, password=None, authentication_url=None,
        tenant_name=None, read_only=True, api_url=None
    ):
        """
        ExternalNetworkProvider class

        Args:
            provider_api_element_name (str): API element name
            name (str): Provider name
            url (str): Provider URL address
            requires_authentication (bool): True if to enable authentication
                with given username and password
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name
            read_only (bool): True (default) to enable provider
                read-only mode, False to enable read/write mode
            api_url (str): Provider API URL

        """
        if provider_api_element_name:
            self.provider_api_element_name = provider_api_element_name

        # Override class name to in order use OpenStackNetworkProvider DS,
        # since ExternalNetworkProvider isn't supported in REST DS namespace
        self.__class__.__name__ = "OpenStackNetworkProvider"

        super(ExternalNetworkProvider, self).__init__(
            provider_api_element_name=self.provider_api_element_name,
            name=name, url=url,
            requires_authentication=requires_authentication,
            username=username, password=password,
            authentication_url=authentication_url, tenant_name=tenant_name
        )
        self._read_only = read_only

        if api_url:
            self.api_url_networks = "%s/networks" % api_url
            self.api_url_subnets = "%s/subnets" % api_url
            self.api_requests = requests.session()

    @property
    def read_only(self):
        """Set external provider read_only or read_write access"""
        return self._read_only

    @read_only.setter
    def read_only(self, read_only):
        self._read_only = read_only

    def _init(self):
        super(ExternalNetworkProvider, self)._init()
        self.osp_obj.set_type("external")
        self.osp_obj.set_read_only(self.read_only)

    def get_all_networks(self):
        """
        Get all networks from external provider

        Returns:
            list: All networks objects

        """
        logger.info(
            "Get all networks from External Network Provider %s",
            self.osp_obj.name
        )
        return self._api.get(
            "{href}/networks".format(href=self.osp_obj.href)
        ).get_openstack_network()

    def get_network(self, network):
        """
        Get network from external provider

        Args:
            network (str): Network name

        Returns:
            OpenStackNetwork: Network object

        """
        network_obj = [
            net for net in self.get_all_networks() if net.name == network
        ]
        logger.info(
            "Get network %s from External Network Provider %s",
            network, self.osp_obj.name
        )
        if not network_obj:
            logger.error(
                "Network %s not found on External Network Provider %s",
                network, self.osp_obj.name
            )
            return None
        return network_obj[0]

    def import_network(self, network, datacenter, cluster=None):
        """
        Import network from external provider

        Args:
            network (str): Network name
            datacenter (str): Datacenter name to import the network into
            cluster (str): Cluster to import the network into

        Returns:
            bool: True if network imported, False otherwise

        """
        network_obj = self.get_network(network=network)
        if not network_obj:
            return False

        logger.info(
            "Import network %s from External Network Provider %s",
            network, self.osp_obj.name
        )
        datacenter_obj = ll_datacenters.get_data_center(datacenter=datacenter)
        if not datacenter_obj:
            logger.error("Datacenter %s not found", datacenter)
            return False

        if not self._api.syncAction(
            network_obj, "import", True, data_center=datacenter_obj
        ):
            logger.error(
                "Failed to import network %s from External Network Provider "
                "%s", network, self.osp_obj.name
            )
            return False

        if cluster:
            logger.info(
                "Attaching network: %s to cluster: %s on Data-Center: %s",
                network, cluster, datacenter
            )
            if not ll_networks.add_network_to_cluster(
                positive=True, network=network, required=False, cluster=cluster
            ):
                logger.error(
                    "Failed to attach network: %s to cluster: %s",
                    network, cluster
                )
                return False

        return True

    # All methods below provide support for interacting with the provider
    # server directly (not through the REST API)

    def __api_request(self, request, url, json=None, timeout=30):
        """
        Handler for provider http server requests

        Args:
            request (str): Server request type: "get", post" or "delete"
            url (str): Server URL address
            json (dict): JSON request to be used in conjunction with post
                request
            timeout (int): Timeout in seconds to wait for server response

        Returns:
            tuple: Tuple (server request return code, json response),
                or (None, None) in case of error

        """
        req = getattr(self.api_requests, request)
        if not req:
            return None, None

        try:
            ret = req(url=url, timeout=timeout, json=json)
        except requests.ConnectionError as conn_err:
            logger.error(
                "Server connection error has occurred: %s", conn_err
            )
            return None, None

        try:
            json_response = ret.json() if request != "delete" else ""
        except ValueError as val_err:
            logger.error(
                "Failed to parse external provider response: %s error: %s",
                ret.text, val_err
            )
            return None, None

        return ret.status_code, json_response

    def get_networks_list_from_provider_server(self):
        """
        Get all networks

        Returns:
            list: A list of dicts that contains networks properties, empty list
                will be returned in case no networks found, or error has
                occurred

        """
        logger.info("Getting network list from external provider")
        ret_code, response = self.__api_request(
            request="get", url=self.api_url_networks
        )

        if ret_code != requests.codes.ok:
            logger.error(
                "External provider returned unexpected error: %s", ret_code
            )
            return list()

        nets = response.get("networks", list())
        logger.debug("External provider returned networks: %s", nets)

        return nets

    def get_network_id(self, network_name):
        """
        Get network ID

        Args:
            network_name (str): Network name

        Returns:
            str: Network ID, or empty string if network not found

        """
        nets = self.get_networks_list_from_provider_server()
        net_id = [
            net.get("id") for net in nets if net.get("name") == network_name
        ]

        return net_id[0] if net_id else ""

    def add_network(self, network_name, subnet_dict=None, admin_state_up=True):
        """
        Add network with optional subnet

        Args:
            network_name (str): Network name
            subnet_dict (dict): Subnet definition dict, or None if no subnet
            admin_state_up (bool): Network administratively state, True for up
                or False for down

        Returns:
            str: Network ID of the created network, or empty string if error
                has occurred

        Example:

            subnet = {
                "name": "subnet_name",
                "cidr": "192.168.1.0/24",
                "enable_dhcp": True,
                "network_id": None,
                "dns_nameservers": "8.8.8.8",
                "ip_version": 4,
                "gateway_ip": "192.168.1.254"
            }

            The network_id value should be set to None, it gets filled at
            runtime

        """
        payload = {
            "network": {
                "name": network_name,
                "admin_state_up": admin_state_up,
                "tenant_id": self.tenant_name
            }
        }

        logger.info("Adding network: %s to provider", network_name)
        ret_code, response = self.__api_request(
            request="post", url=self.api_url_networks, json=payload
        )

        if ret_code != requests.codes.ok:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return ""

        if "network" not in response or "id" not in response.get("network"):
            logger.error("Provider returned unexpected response: %s", response)
            return ""

        net_id = response.get("network", dict()).get("id")

        if subnet_dict:
            subnet_dict.update({"network_id": net_id})
            if self.create_subnet(subnet=subnet_dict):
                return net_id

        return net_id

    def remove_network(self, network_name):
        """
        Remove network

        Args:
            network_name (str): Network name

        Returns:
            bool: True if network removed successfully, False otherwise

        """
        net_id = self.get_network_id(network_name=network_name)
        if not net_id:
            logger.error(
                "Network: %s does not exist in provider", network_name
            )
            return False

        logger.info("Removing network: %s from provider", network_name)
        ret_code, response = self.__api_request(
            request="delete", url="{url}/{net_id}".format(
                url=self.api_url_networks, net_id=net_id
            )
        )

        if ret_code != requests.codes.no_content:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return False

        return True

    def get_subnets_list(self):
        """
        Get subnets list

        Returns:
            list: A list of dicts that contains subnet properties, empty list
                will be returned in case no subnets found, or error has
                occurred

        """
        logger.info("Getting list of network subnets from the provider")
        ret_code, response = self.__api_request(
            request="get", url=self.api_url_subnets
        )

        if ret_code != requests.codes.ok:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return list()

        subnets = response.get("subnets", list())
        logger.debug("Provider returned subnets: %s", subnets)

        return subnets

    def get_subnet_id(self, network_id=None, subnet_name=None):
        """
        Get subnet ID by network ID or subnet name

        Args:
            network_id (str):  Network ID
            subnet_name (str): Subnet name

        Returns:
            str: Subnet ID, or empty string if not found, or error has occurred

        """
        subnets = self.get_subnets_list()
        if not subnets:
            logger.error("There are no subnets in the provider")
            return ""

        prop = "network_id" if network_id else "name"
        val = network_id or subnet_name

        subnet_id = [s.get('id') for s in subnets if s.get(prop) == val]

        return subnet_id[0] if subnet_id else ""

    def create_subnet(self, subnet):
        """
        Create network subnet

        Args:
            subnet (dict): Subnet definition dict

        Returns:
            str: Subnet ID or empty string in case of error

        Example:

            subnet = {
                "name": "subnet_name",
                "cidr": "192.168.1.0/24",
                "enable_dhcp": True,
                "network_id": None,
                "dns_nameservers": "8.8.8.8",
                "ip_version": 4,
                "gateway_ip": "192.168.1.254"
            }

            The network_id value should be set to None, it gets filled at
            runtime

        """
        payload = {
            "subnet": subnet
        }

        logger.info("Adding subnet: %s to provider", subnet.get("name"))
        ret_code, response = self.__api_request(
            request="post", url=self.api_url_subnets, json=payload
        )

        if ret_code != requests.codes.ok:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return ""

        return response.get("subnet", dict()).get("id", "")

    def remove_subnet(self, subnet_id=None, subnet_name=None):
        """
        Remove network subnet by subnet ID or subnet name

        Args:
            subnet_id (str): Subnet ID
            subnet_name (str): Subnet name

        Returns:
            bool: True if subnet removed successfully, False in case of error

        """
        subnet_id = subnet_id or self.get_subnet_id(subnet_name=subnet_name)
        if not subnet_id:
            logger.error("Unable to locate subnet with ID: %s", subnet_id)
            return False

        logger.info("Removing subnet ID: %s from provider", subnet_id)
        ret_code, response = self.__api_request(
            request="delete", url="{url}/{subnet}".format(
                url=self.api_url_subnets, subnet=subnet_id
            )
        )

        if ret_code != requests.codes.no_content:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return False

        return True


class OpenStackNetworkProvider(ExternalNetworkProvider):
    """
    OpenStack Network Provider
    """
    provider_api_element_name = "openstack_network_provider"

    def __init__(
        self, name, url, requires_authentication, username=None, password=None,
        authentication_url=None, tenant_name=None, plugin_type=None,
        network_mapping=None, broker_type=None, agent_port=None,
        agent_address=None, agent_user=None, agent_password=None,
        read_only=True
    ):
        """
        Class for OpenStackNetworkProvider

        Args:
            name (str): Provider name
            url (str): Provider URL address
            requires_authentication (bool): True if to enable authentication
                with given username and password
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name
            plugin_type (str): Network plugin to work with
            network_mapping (str): Network mapping. a comma-separated string of
                "label:interface"
            broker_type (str): Messaging broker type
            agent_port (int): Agent port to connect to
            agent_address (str): Agent address
            agent_user (str): Agent username
            agent_password (str): Agent password
            read_only (bool): True (default) to enable provider
                read-only mode, False to enable read/write mode

        """
        self._plugin_type = plugin_type
        self.network_mapping = network_mapping
        self.broker_type = broker_type
        self.agent_port = agent_port
        self.agent_address = agent_address
        self.agent_user = agent_user
        self.agent_password = agent_password
        self.message_broker_type = broker_type
        self.agent_configuration = None
        super(OpenStackNetworkProvider, self).__init__(
            provider_api_element_name=self.provider_api_element_name,
            name=name, url=url, username=username,
            password=password, tenant_name=tenant_name,
            requires_authentication=requires_authentication,
            authentication_url=authentication_url, read_only=read_only
        )

    def _prepare_agent_configuration(self):
        agent_configuration_dict = {
            "network_mappings": self.network_mapping,
            "broker_type": self.broker_type,
            "port": self.agent_port,
            "address": self.agent_address,
            "username": self.agent_user,
            "password": self.agent_password
        }
        self.agent_configuration = ll_general.prepare_ds_object(
            object_name="AgentConfiguration", **agent_configuration_dict
        )

    def _init(self):
        super(OpenStackNetworkProvider, self)._init()
        self.osp_obj.set_type("neutron")
        self._prepare_agent_configuration()
        self.osp_obj.set_plugin_type(self._plugin_type)
        self.osp_obj.set_agent_configuration(self.agent_configuration)
        self.osp_obj.set_read_only(self.read_only)
