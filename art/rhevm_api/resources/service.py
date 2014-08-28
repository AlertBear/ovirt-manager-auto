from art.rhevm_api.resources.resource import Resource


class Service(Resource):
    def __init__(self, host):
        super(Service, self).__init__()
        self.host = host


class SystemService(Service):
    provider = 'service'

    def __init__(self, host, name):
        super(SystemService, self).__init__(host)
        self.name = name

    def _compose_command(self, action):
        return [
            self.provider,
            self.name,
            action,
        ]

    def _process_output(self, action, rc, out, err):
        # TODO: make it proper
        return not rc

    def execute(self, action):
        executor = self.host.executor()
        rc, out, err = executor.run_cmd(self._compose_command(action))
        return self._process_output(action, rc, out, err)

    def status(self):
        return self.execute('status')

    def start(self):
        return self.execute('start')

    def stop(self):
        return self.execute('stop')

    def restart(self):
        return self.execute('restart')


class SystemctlService(SystemService):
    provider = 'systemctl'

    def _compose_command(self, action):
        return [
            self.provider,
            self.action,
            self.name,
        ]
    # TODO: implement _process_output
