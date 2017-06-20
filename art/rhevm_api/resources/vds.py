import ast
import os
import shlex

import yaml
from repoze.lru import CacheMaker
from rrmngmnt.host import Host
from rrmngmnt.user import RootUser

LIBVIRTD_PID_DIRECTORY = "/var/run/libvirt/qemu/"
VDSM_API_YAML = "/usr/lib/python2.7/site-packages/vdsm/rpc/vdsm-api.yml"


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
        self.logger.info("Get NICs from %s", self.fqdn)
        if active_int is not None:
            active_int_mac = net.find_mac_by_int([active_int])[0]
            for nic in nics:
                if nic == active_int:
                    continue
                nic_mac = net.find_mac_by_int([nic])[0]
                if nic_mac.split(":")[:-1] == active_int_mac.split(":")[:-1]:
                    second_int = nic
                    break

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
        return self.get_cpu_model()

    @cache.lrucache(name='cpu_model')
    def get_cpu_model(self):
        raise NotImplementedError()

    @property
    def vdsm_client_content(self):
        return self._get_vdsm_client_content()

    @cache.lrucache(name='vdsm_client_content')
    def _get_vdsm_client_content(self):
        vdsm_client_content = self.executor().run_cmd(
            shlex.split("cat {path_}".format(path_=VDSM_API_YAML))
        )[1]
        return vdsm_client_content

    @property
    def hosted_engine_host(self):
        return self.is_hosted_engined_deployed()

    def vds_client(self, cmd, args=None):
        """
        Run given command on host with vdsClient
        All commands can be found under:
        https://github.com/oVirt/vdsm/blob/master/lib/vdsm/api/vdsm-api.yml

        Json code:
            from vdsm import client
            cli = client.connect(localhost, 54321, use_tls=True)

        Args:
            cmd (str): command to execute
            args (dict): command parameters optional

        Returns:
            Any: vdsm-client output

        Examples:
            stop VM
            out = config.VDS_HOSTS[0].vds_client("Host.getVMList")
            vm_id = out.get('vmList')[0].get('vmId')
            config.VDS_HOSTS[0].vds_client("VM.destroy", {name:vm_id})

            getVdsCaps
            out = config.VDS_HOSTS[0].vds_client("Host.getCapabilities")
        """
        supported_actions = yaml.load(self.vdsm_client_content)
        action = filter(lambda x: cmd == x, supported_actions.keys())
        if not action:
            self.logger.error("Command %s is not supported", cmd)
            return None
        action = action[0]

        args = args if args else dict()
        command = (
            'python -c "from vdsm import client;'
            'cli = client.connect(\'localhost\', 54321, use_tls=True);'
            'print cli.{action}(**{args})"'.format(action=action, args=args)
        )

        rc, out, err = self.run_command(shlex.split(command))
        if rc:
            return None
        return ast.literal_eval(out)

    def get_vm_process_pid(self, vm_name):
        """
        Get vm process pid from vds resource

        :param vm_name: vm name
        :type vm_name: str
        :returns: vm process pid
        :rtype: str
        """
        vm_pid_file = os.path.join(LIBVIRTD_PID_DIRECTORY, "%s.pid" % vm_name)
        cmd = ["cat", vm_pid_file]
        rc, out, _ = self.run_command(command=cmd)
        return "" if rc else out

    def is_hosted_engined_deployed(self):
        """
        Is host configure as hosted-engine host

        Returns:
            bool: True, if the host configured as the hosted-engine host,
                otherwise False
        """
        return self.vds_client(
            cmd="Host.getCapabilities"
        )["hostedEngineDeployed"]

    def get_he_stats(self):
        """
        Get host hosted engine stats

        Returns:
            dict: Host hosted engine stats
        """
        he_stats = dict()

        if not self.hosted_engine_host:
            return he_stats

        command = (
            'python -c '
            '"from ovirt_hosted_engine_ha.client.client import HAClient;'
            'host_id = HAClient().get_local_host_id();'
            'print HAClient().get_all_host_stats()[host_id]"'
        )
        rc, out, _ = self.run_command(shlex.split(command))
        if rc:
            return he_stats

        return ast.literal_eval(out)
