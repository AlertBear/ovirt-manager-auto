import logging
from art.core_api.apis_utils import getDS
import art.rhevm_api.tests_lib.low_level.datacenters as ll_datacenters
from art.rhevm_api.utils.test_utils import get_api
import art.rhevm_api.tests_lib.low_level.general as ll_general

CEPH = 'ceph'
AUTH_KEY = 'authenticationkey'
logger = logging.getLogger(__name__)


class OpenStackProvider(object):
    """
    Base class for Open Stack external providers
    """
    def __init__(
        self, provider_api_element_name, name=None, url=None,
        requires_authentication=None, username=None, password=None,
        authentication_url=None, tenant_name=None
    ):
        """
        :param provider_api_element_name: api element name
        :type provider_api_element_name: str
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
            action="Remove", obj_type=self.provider_name,
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
        username, password, authentication_url, tenant_name
    ):
        """
        Class for OpenStackNetworkProvider

        Args:
            provider_api_element_name (str): API element name
            name (str): Provider name
            url (str): Provider URL
            requires_authentication (bool): True if requires auth,
                False otherwise
            username (str): Provider username
            password (str): Provider password
            authentication_url (str): Provider authentication URL
            tenant_name (str): Tenant name
        """
        super(ExternalNetworkProvider, self).__init__(
            provider_api_element_name=provider_api_element_name,
            name=name, url=url,
            requires_authentication=requires_authentication,
            username=username, password=password,
            authentication_url=authentication_url, tenant_name=tenant_name
        )

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
            "{href}/networks".format(
                href=self.osp_obj.href
            )
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

    def import_network(self, network, datacenter):
        """
        Import network from external provider

        Args:
            network (str): Network name
            datacenter (str): Datacenter name to import the network into

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
        return True


class OpenStackNetworkProvider(ExternalNetworkProvider):
    """
    OpenStack Network Provider
    """
    provider_api_element_name = "openstack_network_provider"

    def __init__(
        self, name, url, requires_authentication, username,
        password, authentication_url, tenant_name,
        plugin_type, network_mapping, broker_type, agent_port,
        agent_address, agent_user, agent_password
    ):
        """
        Class for OpenStackNetworkProvider

        Args:
            name (str): Provider name
            url (str): Provider URL
            requires_authentication (bool): True if requires auth,
                False otherwise
            username (str): Provider username
            password (str): Provider password
            authentication_url (str): Provider authentication URL
            tenant_name (str): Tenant name
            plugin_type (str): Network plugin to work with
            network_mapping (str): Network mapping. a comma separated string of
                "label:interface
            broker_type (str): Messaging broker type
            agent_port (int): Agent port to connect to
            agent_address (str): Agent address
            agent_user (str): Agent username
            agent_password (str): Agent password
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
            name=name, url=url,
            requires_authentication=requires_authentication,
            username=username, password=password,
            authentication_url=authentication_url, tenant_name=tenant_name,
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
