
from art.core_api.apis_utils import getDS
from art.rhevm_api.utils.test_utils import get_api


class OpenStackImageProvider(object):
    def __init__(
            self,
            name=None,
            url=None,
            requires_authentication=None,
            username=None,
            password=None,
            authentication_url=None,
            tenant_name=None
    ):
        self._name = name
        self._url = url
        self._requires_authentication = requires_authentication
        self._username = username
        self._password = password
        self._authentication_url = authentication_url
        self._tenant_name = tenant_name

        self.open_stack_image_provider = getDS('OpenStackImageProvider')
        self._api = get_api(
            'openstack_image_provider', 'openstackimageproviders'
        )
        self.osip_obj = None
        self._is_connected = False

    def add(self):
        self._init()
        try:
            self.osip_obj, self._is_connected = self._api.create(
                self.osip_obj, positive=True
            )
        except TypeError:
            self._api.logger.warning("Unable to add %s", self.name)

        return self._is_connected

    def _init(self):

        self.osip_obj = self.open_stack_image_provider()
        self.osip_obj.set_name(self.name)
        self.osip_obj.set_url(self.url)
        self.osip_obj.set_requires_authentication(
            self.requires_authentication
        )
        self.osip_obj.set_username(self.username)
        self.osip_obj.set_password(self.password)
        self.osip_obj.set_authentication_url(
            self.authentication_url
        )
        self.osip_obj.set_tenant_name(self.tenant_name)

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
