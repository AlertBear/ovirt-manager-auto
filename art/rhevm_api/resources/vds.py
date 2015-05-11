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
        net = self.get_network()
        nics = net.all_interfaces()
        info = net.get_info()
        active_int = info.get('interface')
        second_int = None
        if active_int is not None:
            active_int_mac = net.find_mac_by_int([active_int])[0]
            for nic in nics:
                if nic == active_int:
                    continue
                nic_mac = net.find_mac_by_int([nic])[0]
                if nic_mac.split(":")[:-1] == active_int_mac.split(":")[:-1]:
                    second_int = nic

            try:
                nics.remove(active_int)
                nics.insert(0, active_int)
                if second_int is not None:
                    nics.remove(second_int)
                    nics.insert(1, second_int)
            except ValueError:
                self.logger.warning(
                    "Active interface '%s' is not listed as interface: %s",
                    active_int, nics
                )
        else:
            self.logger.warning("No active interface was recogized: %s", nics)
        return nics

    @property
    def cpu_model(self):
        return self.cpu_model()

    @cache.lrucache(name='cpu_model')
    def get_cpu_model(self):
        raise NotImplementedError()

    def vds_client(self, cmd, args=None):
        """
        Run given commend on host with vdsClient
        :param cmd: command to execute
        :type: cmd: str
        :param args: command parameters optional
        :type: list
        :return: rc, command output
        :rtype: tuple
        """
        vds_command = ['vdsClient', '-s', '0', cmd]
        if args:
            vds_command.extend(args)
        rc, out, err = self.executor().run_cmd(vds_command)
        if rc:
            self.logger.error(
                "Failed to run command '%s'; out: %s; err: %s",
                " ".join(cmd),
                out,
                err
            )
        return rc, out
