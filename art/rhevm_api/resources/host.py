import socket
import netaddr
from art.rhevm_api.resources.common import fqdn2ip
from art.rhevm_api.resources.resource import Resource
from art.rhevm_api.resources.service import Systemd, SysVinit, InitCtl
from art.rhevm_api.resources.network import Network
from art.rhevm_api.resources.filesystem import FileSystem
from art.rhevm_api.resources import ssh


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
        :param ip: IP address of machine or resolvable FQDN
        :type ip: string
        :param service_provider: system service handler
        :type service_provider: class which implement SystemService interface
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
        :param ip: IP address of machine or resolvable FQDN
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
        return ssh.RemoteExecutor(user, self.ip)

    def copy_to(self, resource, src, dst):
        """
        Copy to host from another resource

        :param resource: resource to copy from
        :type resource: instance of Host
        :param src: path to source
        :type src: str
        :param dst: path to destination
        :type dst: str
        """
        with resource.executor().session() as resource_session:
            with self.executor().session() as host_session:
                with resource_session.open_file(src, 'rb') as resource_file:
                    with host_session.open_file(dst, 'wb') as host_file:
                        host_file.write(resource_file.read())

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

    def get_ssh_public_key(self):
        """
        Get SSH public key

        :return: SSH public key
        :rtype: str
        """
        host_exec = self.executor()
        if not self.fs.exists(ssh.ID_RSA_PUB):
            # Generating SSH key if not exist
            cmd = [
                "ssh-keygen", "-q", "-t", "rsa", "-N", '', "-f", ssh.ID_RSA_PRV
            ]
            rc = host_exec.run_cmd(cmd)[0]
            if rc:
                return ""

        cmd = ["cat", ssh.ID_RSA_PUB]
        return host_exec.run_cmd(cmd)[1]

    def remove_remote_host_ssh_key(self, remote_host):
        """
        Remove remote host keys (ip, fqdn) from KNOWN_HOSTS file

        :param remote_host: Remote host resource object
        :type remote_host: Host
        :return: True/False
        :rtype: bool
        """
        local_host_exec = self.executor()
        ssh_keygen = ["ssh-keygen", "-R"]
        if self.fs.exists(ssh.KNOWN_HOSTS):
            # Remove old keys from local host if any
            for i in [remote_host.ip, remote_host.fqdn]:
                rc = local_host_exec.run_cmd(ssh_keygen + [i])[0]
                if rc:
                    return False
        return True

    def remove_remote_key_from_authorized_keys(self):
        """
        Remove remote ssh key from AUTHORIZED_KEYS file

        :return: True/False
        :rtype: bool
        """
        local_host_exec = self.executor()
        local_fqdn = self.fqdn
        cmd = ["sed", "-i", "/%s/d" % local_fqdn, ssh.AUTHORIZED_KEYS]
        rc = local_host_exec.run_cmd(cmd)[0]
        if rc:
            return False
        return True

    def get_network(self):
        return Network(self)

    @property
    def network(self):
        return self.get_network()

    @property
    def fs(self):
        return FileSystem(self)

    @property
    def ssh_public_key(self):
        return self.get_ssh_public_key()
