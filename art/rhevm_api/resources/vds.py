from repoze.lru import CacheMaker
from art.rhevm_api.resources.host import Host
from art.rhevm_api.resources.user import RootUser


class VDS(Host):
    """
    This object hold all host (VDS) related parameters together
    """
    cache = CacheMaker(100)

    def __init__(self, ip, root_password):
        """
        :param ip: ip/hostname
        :type ip: str
        :param root_password: root password for host
        :type root_password: str
        """
        super(VDS, self).__init__(ip)
        self.users.append(RootUser(root_password))

    @property
    def nics(self):
        """
        List of network interfaces which were recognized on host
        """
        return self.get_nics()

    @cache.lrucache(name='nics')
    def get_nics(self):
        raise NotImplementedError()

    @property
    def cpu_model(self):
        return self.cpu_model()

    @cache.lrucache(name='cpu_model')
    def get_cpu_model(self):
        raise NotImplementedError()
