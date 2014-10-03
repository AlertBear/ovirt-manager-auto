from art.rhevm_api.resources.resource import Resource


class Service(Resource):
    def __init__(self, host):
        super(Service, self).__init__()
        self.host = host


class SystemService(Service):
    """
    Read https://fedoraproject.org/wiki/SysVinit_to_Systemd_Cheatsheet
    for more info / differences between Systemd and SysVinit
    """
    cmd = None

    def __init__(self, host, name):
        super(SystemService, self).__init__(host)
        self.name = name

    def is_enabled(self):
        raise NotImplementedError()

    def enable(self):
        raise NotImplementedError()

    def disable(self):
        raise NotImplementedError()

    def status(self):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def restart(self):
        raise NotImplementedError()

    def reload(self):
        raise NotImplementedError()


class SysVinit(SystemService):
    cmd = 'service'
    manage_cmd = 'chkconfig'

    def _toggle(self, action):
        cmd = [
            self.cmd,
            self.name,
            action,
        ]
        executor = self.host.executor()
        rc, _, _ = executor.run_cmd(cmd)
        return rc == 0

    def _manage(self, action):
        cmd = [
            self.manage_cmd,
            self.name,
            action,
        ]
        executor = self.host.executor()
        rc, _, _ = executor.run_cmd(cmd)
        return rc == 0

    def is_enabled(self):
        cmd = [
            self.manage_cmd,
            self.name,
        ]
        executor = self.host.executor()
        rc, _, _ = executor.run_cmd(cmd)
        return rc == 0

    def enable(self):
        return self._manage('on')

    def disable(self):
        return self._manage('off')

    def status(self):
        return self._toggle('status')

    def start(self):
        return self._toggle('start')

    def stop(self):
        return self._toggle('stop')

    def restart(self):
        return self._toggle('restart')

    def reload(self):
        return self._toggle('reload')


class Systemd(SystemService):
    cmd = 'systemctl'

    def _execute(self, action):
        cmd = [
            self.cmd,
            action,
            self.name + ".service",
        ]
        executor = self.host.executor()
        rc, _, _ = executor.run_cmd(cmd)
        return rc == 0

    def is_enabled(self):
        return self._execute('is-enabled')

    def enable(self):
        return self._execute('enable')

    def disable(self):
        return self._execute('disable')

    def status(self):
        return self._execute('status')

    def start(self):
        return self._execute('start')

    def stop(self):
        return self._execute('stop')

    def restart(self):
        return self._execute('restart')

    def reload(self):
        return self._execute('reload')
