import socket
from art.rhevm_api.resources.resource import Resource
from art.rhevm_api.resources.ssh import RemoteExecutor
from art.rhevm_api.resources.service import SystemService, SystemctlService
from art.rhevm_api.resources.network import Network


class Host(Resource):
    # The purpose of inventory variable is keeping all instances of
    # interesting resources in single place.
    inventory = list()

    def __init__(self, ip):
        """
        :param ip: IP of host
        :type ip: string
        """
        super(Host, self).__init__()
        self.ip = ip
        self.users = list()

    def __str__(self):
        return "Host(%s)" % self.address

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

    def service(self, name):
        return SystemService(self, name)

    def systemctl(self, name):
        return SystemctlService(self, name)

    def get_network(self):
        return Network(self)

    @property
    def network(self):
        return self.get_network()
