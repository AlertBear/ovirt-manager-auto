from art.rhevm_api.resources.service import Service
from art.rhevm_api.resources.db import Database
from art.rhevm_api.resources.user import User
from art.rhevm_api.resources.host import Host


DATABASE_CONFIG = "/etc/ovirt-engine/engine.conf.d/10-setup-database.conf"


class Engine(Service):
    def __init__(
        self, host, admin, schema='https', port=443,
        entry_point='api', service_name='ovirt-engine',
    ):
        """
        :param: host: refer to machine where the Engine is hosted
        :param host: instance of Host
        :param admin: Engine administrator
        :type admin: instance of ADUser
        :param schema: schema
        :type schema: str
        :param port: port number
        :type port: int
        :param entry_point: API entry point
        :type entry_point: str
        :param service_name: name of service
        :type service_name: str
        """
        super(Engine, self).__init__(host)
        self.admin = admin
        self.schema = schema
        self.port = port
        self.entry_point = entry_point
        self.service_name = service_name

    def _read_config(self, path_to_config):
        data = {}
        executor = self.host.executor()
        with executor.session() as ss:
            with ss.open_file(path_to_config) as fh:
                for line in fh.readlines():
                    line = line.strip()
                    key, val = line.split('=', 1)
                    data[key] = val.strip("\"'")
        return data

    @property
    def url(self):
        return "%s://%s:%s/%s" % (
            self.schema,
            self.host.fqdn,
            self.port,
            self.entry_point,
        )

    @property
    def health_page(self):
        # NOTE: it is always http
        return "http://%s/ovirt-engine/services/health" % self.host.fqdn

    @property
    def db(self):
        try:
            config = self._read_config(DATABASE_CONFIG)
            user = User(config['ENGINE_DB_USER'], config['ENGINE_DB_PASSWORD'])
            host = self.host
            if config['ENGINE_DB_HOST'] != 'localhost':
                remote_host = [
                    h for h in Host.inventory
                    if h.ip == config['ENGINE_DB_HOST'] or
                    h.fqdn == config['ENGINE_DB_HOST']
                ]
                if not remote_host:
                    raise Exception(
                        "Can not find instance of %s in inventory: %s" % (
                            config['ENGINE_DB_HOST'],
                            Host.inventory,
                        )
                    )
                remote_host = remote_host[0]
                self.logger.info(
                    "Using %s as host for DB %s",
                    remote_host,
                    config['ENGINE_DB_DATABASE']
                )
                host = remote_host
            return Database(host, config['ENGINE_DB_DATABASE'], user)
        except KeyError as ex:
            self.logger.error(
                "There are missing values %s in %s from %s",
                ex.args,
                config,
                DATABASE_CONFIG,
            )
            raise

    def restart(self):
        service = self.host.service(self.service_name)
        service.stop()
        service.start()
        # TODO: wait for health page
