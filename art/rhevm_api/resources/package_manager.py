from art.rhevm_api.resources.service import Service

YUM_MANAGER_CLASS = 'YumPackageManager'
RPM_MANAGER_CLASS = 'RPMPackageManager'


class PackageManager(Service):
    """
    Class to provide flex interface
    """
    exist_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'list', 'installed'],
        RPM_MANAGER_CLASS: ['rpm', '-q']
    }
    install_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'install', '-y'],
        RPM_MANAGER_CLASS: ['rpm', '-i']
    }
    erase_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'erase', '-y'],
        RPM_MANAGER_CLASS: ['rpm', '-e']
    }

    def __init__(self, host):
        """
        Initialization method for PackageManager class

        :param host: host resource
        :type host: Host
        """
        super(PackageManager, self).__init__(host)
        self.cls_name = self.__class__.__name__

    def _run_command_on_host(self, cmd):
        """
        Run given command on host

        :param cmd: command to run
        :type cmd: list
        :return: True, if command success, otherwise False
        :rtype: bool
        """
        self.logger.info(
            "Execute command '%s' on host %s", " ".join(cmd), self.host
        )
        rc, out, err = self.host.executor().run_cmd(cmd)
        if rc:
            self.logger.error(
                "Failed to execute command '%s' on host %s; out: %s; err: %s",
                " ".join(cmd), self.host, out, err
            )
            return False
        return True

    def exist(self, package):
        """
        Check if package exist on host

        :param package: name of package
        :type package: str
        :return: True, if package exist, otherwise False
        :rtype: bool
        """
        cmd = list(self.exist_command_d[self.cls_name])
        cmd.append(package)
        self.logger.info(
            "Check if host %s have %s package", self.host, package
        )
        return self._run_command_on_host(cmd)

    def install(self, package):
        """
        Install package on host

        :param package: name of package
        :type package: str
        :return: True, if package installation success, otherwise False
        :rtype: bool
        """
        cmd = list(self.install_command_d[self.cls_name])
        cmd.append(package)
        if not self.exist(package):
            self.logger.info(
                "Install package %s on host %s", package, self.host
            )
            return self._run_command_on_host(cmd)
        self.logger.info(
            "Package %s already exist on host %s", package, self.host
        )
        return True

    def remove(self, package):
        """
        Remove package from host

        :param package: name of package
        :type package: str
        :return: True, if package removal success, otherwise False
        :rtype: bool
        """
        cmd = list(self.erase_command_d[self.cls_name])
        cmd.append(package)
        if self.exist(package):
            self.logger.info(
                "Erase package %s on host %s", package, self.host
            )
            return self._run_command_on_host(cmd)
        self.logger.info(
            "Package %s not exist on host %s", package, self.host
        )
        return True


class YumPackageManager(PackageManager):
    """
    YUM package manager class
    """
    pass


class RPMPackageManager(PackageManager):
    """
    RPM package manager class
    """
    pass
