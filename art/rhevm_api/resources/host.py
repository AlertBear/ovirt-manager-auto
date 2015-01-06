import socket
import netaddr
from art.rhevm_api.resources.common import fqdn2ip
from art.rhevm_api.resources.resource import Resource
from art.rhevm_api.resources.ssh import RemoteExecutor
from art.rhevm_api.resources.service import Systemd, SysVinit, InitCtl
from art.rhevm_api.resources.network import Network
from art.rhevm_api.resources.filesystem import FileSystem


class Host(Resource):
    """
    This resource could represents any physical / virtual machine
    """

    # The purpose of inventory variable is keeping all instances of
    # interesting resources in single place.
    inventory = list()

    default_service_providers = [
        Systemd,
        SysVinit,
        InitCtl,
    ]

    class LoggerAdapter(Resource.LoggerAdapter):
        """
        Makes sure that all logs which are done via this class, has
        appropriate prefix. [IP]
        """
        def process(self, msg, kwargs):
            return (
                "[%s] %s" % (
                    self.extra['self'].ip,
                    msg,
                ),
                kwargs,
            )

    def __init__(self, ip, service_provider=None):
        """
        :param ip: IP adress of machine or resolvable fqdn
        :type ip: string
        :param service_provider: system service handler
        :type service_provider: class wich implemets SystemService interface
        """
        super(Host, self).__init__()
        if not netaddr.valid_ipv4(ip):
            ip = fqdn2ip(ip)
        self.ip = ip
        self.users = list()
        self._service_provider = service_provider
        self.add()  # adding host to inventory

    def __str__(self):
        return "Host(%s)" % self.ip

    @classmethod
    def get(cls, ip):
        """
        Get host from inventory
        :param ip: IP adress of machine or resolvable fqdn
        :type ip: str
        :return: host
        :rtype: Host
        """
        host = [h for h in cls.inventory if h.ip == ip or h.fqdn == ip]
        if not host:
            raise ValueError("There is no host with %s" % ip)
        return host[0]

    def add(self):
        """
        Add host to inventory
        """
        try:
            host = self.get(self.ip)
        except ValueError:
            pass
        else:
            self.inventory.remove(host)
        self.inventory.append(self)

    @property
    def fqdn(self):
        return socket.getfqdn(self.ip)

    def get_user(self, name):
        for user in self.users:
            if user.name == name:
                return user
        raise Exception(
            "User '%s' is not assoiated with host %s" % (name, self)
        )

    @property
    def root_user(self):
        return self.get_user('root')

    def executor(self, user=None):
        if user is None:
            user = self.root_user
        return RemoteExecutor(user, self.ip)

    def _create_service(self, name, timeout):
        for provider in self.default_service_providers:
            try:
                service = provider(self, name, timeout=timeout)
            except provider.CanNotHandle:
                pass
            else:
                self.logger.info(
                    "Setting %s as service provider", provider
                )
                self._service_provider = provider
                break
        else:
            msg = (
                "Can not find suitable service provider: %s" %
                self.default_service_providers
            )
            self.logger.error(msg)
            raise Exception(msg)
        return service

    def service(self, name, timeout=None):
        """
        Create service provider for desired service

        :param name: service name
        :type name: string
        :param timeout: expected time to complete operations
        :type timeout: int
        :return: service provider for desired service
        :rtype: instance of SystemService
        """
        if self._service_provider is None:
            # we need to pick up service provider,
            # assume same provider for all next services.
            service = self._create_service(name, timeout)
            self._service_provider = service.__class__
            return service
        try:
            return self._service_provider(self, name, timeout=timeout)
        except self._service_provider.CanNotHandle:
            # it may happen there is some special service
            # which needs different provider.
            # try to select different one
            service = self._create_service(name, timeout)
            self._service_provider = service.__class__
            return service

    def get_network(self):
        return Network(self)

    @property
    def network(self):
        return self.get_network()

    @property
    def fs(self):
        return FileSystem(self)
