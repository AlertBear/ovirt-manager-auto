#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
External network providers
"""

import logging

import requests

from art.core_api import apis_exceptions
from art.core_api.apis_utils import getDS
from art.rhevm_api.tests_lib.low_level import (
    datacenters as ll_datacenters,
    general as ll_general,
    networks as ll_networks
)
from art.rhevm_api.utils.test_utils import get_api

CEPH = "ceph"
AUTH_KEY = "authenticationkey"

logger = logging.getLogger(__name__)


class OpenStackProvider(object):
    """
    Base class for Open Stack external providers
    """
    def __init__(
        self, provider_api_element_name, name, url,
        requires_authentication=False, username=None, password=None,
        authentication_url=None, tenant_name=None
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
            provider_api_element_name, self.provider_name.lower() + "s"
        )
        self.osp_obj = None

        # Get existing provider object (if already exist on engine)
        self.get(openstack_ep=name)

    def add(self):
        """
        Add External Provider to engine
        """
        self._init()

        try:
            self.osp_obj = self._api.create(self.osp_obj, positive=True)[0]
        except TypeError:
            self._api.logger.warning("Unable to add provider: %s", self.name)
            return False
        return True

    def update(self, **kwargs):
        """
        Update External Provider object with given properties

        Keyword Args:
            url (str): URL to update
            requires_authentication (bool): Provider requires authentication
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider authentication URL
            tenant_name (str): Provider tenant name

        Returns:
            bool: True if update succeeded, False otherwise
        """
        url = kwargs.get("url")
        requires_authentication = kwargs.get("requires_authentication")
        username = kwargs.get("username")
        password = kwargs.get("password")
        authentication_url = kwargs.get("authentication_url")
        tenant_name = kwargs.get("tenant_name")

        new_osp_obj = self.open_stack_provider()

        if url:
            new_osp_obj.set_url(url)
            self._url = self.osp_obj.url
        if requires_authentication:
            new_osp_obj.set_requires_authentication(requires_authentication)
            self._requires_authentication = (
                self.osp_obj.requires_authentication
            )
        if username:
            new_osp_obj.set_username(username)
            self._username = self.osp_obj.username
        if password:
            new_osp_obj.set_password(password)
            self._password = self.osp_obj.password
        if authentication_url:
            new_osp_obj.set_authentication_url(authentication_url)
            self._authentication_url = self.osp_obj.authentication_url
        if tenant_name:
            new_osp_obj.set_tenant_name(tenant_name)
            self._tenant_name = self.osp_obj.tenant_name

        return self._api.update(
            origEntity=self.osp_obj, newEntity=new_osp_obj, positive=True
        )

    def get(self, openstack_ep, key="name"):
        """
        Get OpenStack External Provider object from engine by name or ID

        Args:
            openstack_ep (str): OpenStack property name or ID
            key (str): OpenStack property attribute, can be name or ID

        Returns:
            Openstack provider object: OpenStack provider object if exists, or
                None if not exists
        """
        try:
            self.osp_obj = self._api.find(openstack_ep, attribute=key)
        except apis_exceptions.EntityNotFound:
            return None
        return self.osp_obj

    def get_openstack_ep_objects(self):
        """
        Get OpenStack External Provider objects from engine

        Returns:
            list: A list of OpenStack External Provider objects
        """
        return self._api.get(abs_link=False)

    @ll_general.generate_logs()
    def remove(self, openstack_ep, key="name"):
        """
        Remove openstack_ep object from engine by key

        Args:
            openstack_ep (str): OpenStack property name or ID
            key (str): OpenStack property attribute, can be name or ID

        Returns:
            bool: True if removed successfully, False otherwise
        """
        ep_obj = self.get(openstack_ep=openstack_ep)
        if ep_obj:
            return self._api.delete(ep_obj, True)
        return False

    def _init(self):
        """
        Initialize Open Stack Provider object instance and populate it with
        properties
        """
        self.osp_obj = self.open_stack_provider()
        self.osp_obj.set_name(self.name)
        self.osp_obj.set_url(self.url)
        self.osp_obj.set_requires_authentication(self.requires_authentication)
        self.osp_obj.set_username(self.username)
        self.osp_obj.set_password(self.password)
        self.osp_obj.set_authentication_url(self.authentication_url)
        self.osp_obj.set_tenant_name(self.tenant_name)

    @property
    def name(self):
        """
        Get provider name property
        """
        return self._name

    @property
    def url(self):
        """
        Get provider URL property
        """
        return self._url

    @property
    def requires_authentication(self):
        """
        Get requires_authentication property
        """
        return self._requires_authentication

    @property
    def username(self):
        """
        Get provider username property
        """
        return self._username

    @property
    def password(self):
        """
        Get provider password property
        """
        return self._password

    @property
    def authentication_url(self):
        """
        Get provider authentication URL property
        """
        return self._authentication_url

    @property
    def tenant_name(self):
        """
        Get provider tenant name property
        """
        return self._tenant_name

    @property
    def is_exists(self):
        """
        Provider exists on engine property

        Returns:
            bool: True if provider exists, False otherwise
        """
        return self.get(openstack_ep=self.name) is not None


class OpenStackImageProvider(OpenStackProvider):
    """
    Base class for Open Stack Image Providers
    """

    provider_api_element_name = "openstack_image_provider"

    def __init__(
        self, name=None, url=None, requires_authentication=None, username=None,
        password=None, authentication_url=None, tenant_name=None
    ):
        """
        OpenStackImageProvider class

        Args:
            name (str): Provider name
            url (str): Provider URL address
            requires_authentication (bool): True to enable authentication
                with given username and password
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name
        """
        super(OpenStackImageProvider, self).__init__(
            self.provider_api_element_name, name, url, requires_authentication,
            username, password, authentication_url, tenant_name,
        )


class OpenStackVolumeProvider(OpenStackProvider):
    """
    Base class for Open Stack Volume Providers
    """
    provider_api_element_name = "openstack_volume_provider"
    cinder_key_ds = getDS("OpenstackVolumeAuthenticationKey")
    cinder_key_coll_name = "openstack_volume_authentication_key"

    def __init__(
            self,
            name=None, url=None, requires_authentication=None, username=None,
            password=None, authentication_url=None, tenant_name=None,
            data_center=None, key_uuid=None, key_value=None
    ):
        """
        OpenStackVolumeProvider class

        Args:
            name (str): Provider name
            url (str): Provider URL address
            requires_authentication (bool): True to enable authentication
                with given username and password
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name
            data_center (DataCenter object): Data Center object
            key_uuid (str): Auth key uuid
            key_value (str): Auth key value
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
        """
        Get Data Center property
        """
        return self._data_center

    @data_center.setter
    def data_center(self, data_center):
        """
        Set Data Center property

        Args:
            data_center (DataCenter object): Data Center object
        """
        self._data_center = data_center

    def _init(self):
        """
        Initialize OpenstackVolumeProvider object instance and populate it
            with properties
        """
        super(OpenStackVolumeProvider, self)._init()
        self.osp_obj.set_data_center(self.data_center)

    def add_ceph_auth_key(self, uuid, value, usage_type=CEPH):
        """
        Add Ceph authorization key

        Args:
            uuid (str): Auth key uuid
            value (str): Auth key value to set
            usage_type (str): Auth key usage type

        Returns (bool): True if added successfully, False otherwise
        """
        key_obj = self.cinder_key_ds()
        key_obj.set_uuid(uuid)
        key_obj.set_value(value)
        key_obj.set_usage_type(usage_type)

        key_collection = self._api.getElemFromLink(
            self.osp_obj, link_name=AUTH_KEY+"s", attr=AUTH_KEY, get_href=True
        )
        self.key_obj, created_success = self._api.create(
            key_obj, positive=True, collection=key_collection,
            coll_elm_name=self.cinder_key_coll_name, expected_entity=key_obj
        )
        return created_success

    def add(self):
        """
        Add OpenStackVolumeProvider object to engine
        """
        if super(OpenStackVolumeProvider, self).add():
            if self.key_uuid and self.key_value:
                self.add_ceph_auth_key(self.key_uuid, self.key_value)
            return True
        return False


def get_glance_ep_obj(glance_ep, key="name"):
    """
    Get Glance image external provider object from engine by name or ID

    Args:
        glance_ep (str): OpenStack External Provider name or ID
        key (str): Key to look for, can be "name" or "id"

    Returns:
        Glance object: Glance object or None if not found
    """
    return OpenStackImageProvider().get(glance_ep, key)


def get_glance_ep_objs():
    """
    Get Glance External provider objects from engine

    Returns:
        list: a list of Glance External provider objects
    """
    return OpenStackImageProvider().get_openstack_ep_objects()


def get_glance_ep_objs_names():
    """
    Get glance ep objects names from engine

    Returns:
        list: a list of Glance External provider object names
    """
    return [ep.name for ep in get_glance_ep_objs()]


def remove_glance_ep(glance_ep, key="name"):
    """
    Remove glance ep object from engine by name or id

    Args:
        glance_ep (str): Glance external provider name/id
        key (str): Key to look for glance external provider, it can be name or
            id

    Returns:
        bool: True if Glance external provider was removed properly,
            False otherwise
    """
    return OpenStackImageProvider().remove(glance_ep, key)


def get_cinder_ep_obj(cinder_ep, key="name"):
    """
    Get cinder ep object from engine by name or id

    Args:
        cinder_ep (str): openstack ep name/id
        key (str): key to look for ep, it can be name or id

    Returns:
        cinder ep object: Cinder External Provider object if found, None
            otherwise
    """
    return OpenStackVolumeProvider().get(openstack_ep=cinder_ep, key=key)


def get_cinder_ep_objs():
    """
    Get cinder ep objects from engine

    Returns:
        list: a list of cinder ep objects
    """
    return OpenStackVolumeProvider().get_openstack_ep_objects()


def get_cinder_ep_objs_names():
    """
    Get cinder ep objects names from engine

    Returns:
        list: a list of cinder ep objects names
    """
    return [ep.name for ep in get_cinder_ep_objs()]


def remove_cinder_ep(cinder_ep, key="name"):
    """
    Remove cinder ep object from engine by name or id

    Args:
        cinder_ep (str): cinder ep name/id
        key (str): key to look for cinder ep, it can be name or id

    Returns:
        bool: True if removed successfully, False otherwise

    """
    return OpenStackVolumeProvider().remove(cinder_ep, key)


class ExternalNetworkProvider(OpenStackProvider):
    """
    External Network Provider
    """
    provider_api_element_name = "external_network_provider"

    def __init__(
        self, name, provider_api_element_name=None, url=None,
        requires_authentication=True, username=None, password=None,
        authentication_url=None, tenant_name=None, read_only=True,
        api_url=None, keystone_url=None, keystone_username=None,
        keystone_password=None, verify_ssl=True, unmanaged=False,
        plugin_type="OVIRT_PROVIDER_OVN"
    ):
        """
        ExternalNetworkProvider class

        Args:
            name (str): Provider name
            url (str): Provider URL address
            provider_api_element_name (str): API element name
            requires_authentication (bool): True to enable authentication
                with given username and password, False otherwise
            username (str): Provider authentication username
            password (str): Provider authentication password
            authentication_url (str): Provider URL address for
                authentication (in case required_authentication is enabled)
            tenant_name (str): Provider tenant name
            read_only (bool): True (default) to enable provider
                read-only mode, False to enable read/write mode
            api_url (str): Provider API URL address
            keystone_url (str): Keystone URL address
            keystone_username (str): Keystone username
            keystone_password (str): Keystone password
            verify_ssl (bool): Verify SSL certificate on provider connections
            unmanaged (bool): Set provider as unmanaged provider
            plugin_type (str): Network plugin to use

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
        self._unmanaged = unmanaged
        self._plugin_type = plugin_type
        self._read_only = read_only
        self._keystone_username = keystone_username
        self._keystone_password = keystone_password
        self._api_keystone_token = None
        self._valid_return_codes = (
            requests.codes.ok, requests.codes.created
        )
        self._token_expired_msg = (
            "The provided authorization grant for the auth code has expired"
        )
        if api_url:
            self.api_url_networks = "%s/networks" % api_url
            self.api_url_subnets = "%s/subnets" % api_url
            self.api_requests = requests.session()
            self.api_requests.verify = verify_ssl
        if keystone_url and keystone_username and keystone_password:
            self._keystone_tokens_url = "%s/tokens" % keystone_url
            self.__request_keystone_token()

    @property
    def read_only(self):
        """
        Get external provider read_only property

        Returns:
            bool: True if provider in read_only, False otherwise
        """
        return self._read_only

    @read_only.setter
    def read_only(self, read_only):
        """
        Set external provider read_only property

        Args:
            read_only (bool): True to set read-only property, False to set
                read-write property
        """
        self._read_only = read_only

    @property
    def unmanaged(self):
        """
        Get external provider unmanaged property

        Returns:
            bool: True if provider in unmanaged, False otherwise
        """
        return self._unmanaged

    @unmanaged.setter
    def unmanaged(self, unmanaged):
        """
        Set external provider unmanaged property

        Args:
            unmanaged (bool): True to set unmanaged-only property
        """
        self._unmanaged = unmanaged

    @property
    def plugin_type(self):
        """
        Get external provider unmanaged property

        Returns:
            str: Plugin type of the provider
        """
        return self._plugin_type

    @plugin_type.setter
    def plugin_type(self, plugin_type):
        """
        Set external provider unmanaged property

        Args:
            plugin_type (str): Set provider plugin type
        """
        self._plugin_type = plugin_type

    def _init(self):
        super(ExternalNetworkProvider, self)._init()
        self.osp_obj.set_type("external")
        self.osp_obj.set_read_only(self.read_only)
        self.osp_obj.set_unmanaged(self.unmanaged)
        self.osp_obj.set_external_plugin_type(self.plugin_type)

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
        logger.info(
            "Get network %s from External Network Provider %s",
            network, self.osp_obj.name
        )
        networks = [
            net for net in self.get_all_networks() if net.name == network
        ]
        if not networks:
            logger.error(
                "Network: %s not found on External Network Provider: %s",
                network, self.osp_obj.name
            )
            return None

        if len(networks) > 1:
            logger.warning("Duplicate OVN network names exists on provider")

        return networks[0]

    def import_network(self, network, datacenter, cluster=None):
        """
        Import network from external provider

        Args:
            network (str): Network name
            datacenter (str): Datacenter name to import the network into
            cluster (str): Cluster to import the network into

        Returns:
            bool: True if network imported successfully, False otherwise

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

    # All methods below provide support for interacting with the OVN provider
    # server directly (not through the engine REST API)
    def __api_request(self, request, url, json=None, timeout=30):
        """
        Handler for provider HTTP server requests

        Args:
            request (str): Server request type: "get", post", "put" or "delete"
            url (str): Server URL address
            json (dict): JSON request to be used in conjunction with post
                request
            timeout (int): Timeout in seconds to wait for server response

        Returns:
            tuple: Tuple (server request return code, JSON response),
                or (None, None) in case of error
        """
        ret = headers = None

        req = getattr(self.api_requests, request)
        if not req:
            return None, None

        if self._api_keystone_token:
            headers = {"X-Auth-Token": self._api_keystone_token}
        try:
            ret = req(url=url, timeout=timeout, json=json, headers=headers)
        except requests.ConnectionError as conn_err:
            logger.error("Server connection error has occurred: %s", conn_err)
            return None, None

        # Check the validity of token grant and renew it if expired
        # NOTE: code may stuck be in infinite loop in case of a failure to
        # renew the token using the provider (and ovirt-engine)
        if self._token_expired_msg in ret.text:
            logger.warn(
                "API token is expired. Requesting a new token from keystone."
            )
            self.__request_keystone_token()
            return self.__api_request(
                request=request, url=url, json=json, timeout=timeout
            )

        try:
            json_response = ret.json() if request != "delete" and ret else ""
        except ValueError as val_err:
            logger.error(
                "Failed to parse external provider response: %s error: %s",
                ret.text, val_err
            )
            return None, None

        return ret.status_code, json_response

    def __request_keystone_token(self):
        """
        Request a token from Keystone server to authenticate provider API
            requests

        Raises:
            APITokenError: In case of Keystone error or token not received
        """
        logger.info("Requesting token from Keystone service")
        payload = {
            "auth": {
                "passwordCredentials": {
                    "username": self._keystone_username,
                    "password": self._keystone_password
                }
            }
        }
        ret_code, response = self.__api_request(
            request="post", url=self._keystone_tokens_url, json=payload
        )

        logger.debug(
            "Keystone service returned JSON response: %s and HTTP code: %s",
            response, ret_code
        )
        if ret_code not in self._valid_return_codes:
            logger.error(
                "Keystone returned unexpected HTTP code: %s", ret_code
            )
            raise apis_exceptions.APITokenError

        # Expected JSON response structure:
        # { "access": { "token": { "id": <unicode encoded str> } } }
        token = response.get("access", {}).get("token", {})
        self._api_keystone_token = token.get("id", "")
        if not self._api_keystone_token:
            logger.error("Keystone service did not return a valid token")
            raise apis_exceptions.APITokenError

        logger.info("Received a valid token from Keystone service")

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
            return []
        nets = response.get("networks", [])
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

        if ret_code not in self._valid_return_codes:
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
            return []

        subnets = response.get("subnets", [])
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
        subnet_id = [s.get("id") for s in subnets if s.get(prop) == val]

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

        """
        logger.info("Adding subnet: %s to provider", subnet.get("name"))
        ret_code, response = self.__api_request(
            request="post", url=self.api_url_subnets,
            json={"subnet": subnet}
        )

        if ret_code not in self._valid_return_codes:
            logger.error("Provider returned unexpected error: %s", ret_code)
            return ""
        return response.get("subnet", {}).get("id", "")

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
            logger.error("Unable to locate a subnet for the given network")
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

    def test_connection(self):
        """
        Test the state of the connection to the external provider

        Returns:
            bool: True if provider connection is working, False otherwise
        """
        res = self._api.syncAction(
            entity=self.osp_obj, action="testconnectivity", positive=True
        )
        return bool(res)


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
        """
        Prepare External Provider agent configuration structure
        """
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
        """
        Initialize OpenStackNetworkProvider object instance and populate it
            with properties
        """
        super(OpenStackNetworkProvider, self)._init()
        self.osp_obj.set_type("neutron")
        self._prepare_agent_configuration()
        self.osp_obj.set_agent_configuration(self.agent_configuration)
        self.osp_obj.set_plugin_type(self._plugin_type)
        self.osp_obj.set_read_only(self.read_only)
