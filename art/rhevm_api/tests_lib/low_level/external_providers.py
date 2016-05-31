import logging
from art.core_api.apis_utils import getDS
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
