from art.rhevm_api.resources.service import Service

YUM_MANAGER_CLASS = 'YumPackageManager'
RPM_MANAGER_CLASS = 'RPMPackageManager'
APT_MANAGER_CLASS = 'APTPackageManager'


class PackageManager(Service):
    """
    Class to provide flex interface
    """
    exist_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'list', 'installed'],
        RPM_MANAGER_CLASS: ['rpm', '-q'],
        # FIXME: Once apt will return correct return codes fix this
        APT_MANAGER_CLASS: ['apt', 'list', '--installed', '|', 'grep'],
    }
    install_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'install', '-y'],
        RPM_MANAGER_CLASS: ['rpm', '-i'],
        APT_MANAGER_CLASS: ['apt', 'install', '-y'],
    }
    erase_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'erase', '-y'],
        RPM_MANAGER_CLASS: ['rpm', '-e'],
        APT_MANAGER_CLASS: ['apt', 'remove', '-y'],
    }
    update_command_d = {
        YUM_MANAGER_CLASS: ['yum', 'update', '-y'],
        RPM_MANAGER_CLASS: ['rpm', '-U'],
        APT_MANAGER_CLASS: ['apt', 'update', '-y'],
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

    def update(self, packages=None):
        """
        Updated specified packages, or all available system updates
        if no packages are specified

        __author__ = "omachace"
        :param packages: Packages to be updated, if empty, update system
        :type packages: list
        :return: True when updates succeed, False otherwise
        :rtype: bool
        """
        cmd = list(self.update_command_d[self.cls_name])
        if packages:
            cmd.extend(packages)
            self.logger.info(
                "Update packages %s on host %s", packages, self.host
            )
        else:
            self.logger.info("Updating system on host %s", self.host)
        return self._run_command_on_host(cmd)


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


class APTPackageManager(PackageManager):
    """
    APT package manager class
    """
    pass
