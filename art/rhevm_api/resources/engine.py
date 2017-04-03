import contextlib
import time
import urllib2

import requests

from rrmngmnt.db import Database
from rrmngmnt.host import Host
from rrmngmnt.service import Service
from rrmngmnt.user import User

DATABASE_CONFIG = "/etc/ovirt-engine/engine.conf.d/10-setup-database.conf"


class Engine(Service):
    def __init__(
        self, host, admin, schema='https', port=443,
        entry_point='ovirt-engine/api', service_name='ovirt-engine',
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
    def api_page_status(self):
        """
        Get API page status

        Returns:
            bool: True, if the engine API is reachable, otherwise False
        """
        response = requests.get(
            url=self.url,
            auth=(self.admin.get_full_name(), self.admin.password),
            verify=False
        )
        self.logger.debug(
            "Engine response: %s - %s",
            response.status_code, response.reason
        )
        return response.ok

    @property
    def health_page_status(self):
        """
        True / False according to health page status
        """
        happy_message = "DB Up!Welcome to Health Status!"
        self.logger.info("GET %s", self.health_page)
        try:
            with contextlib.closing(
                urllib2.urlopen(
                    self.health_page
                )
            ) as request:
                self.logger.info("  CODE: %s, %s", request.code, request.msg)
                if request.code != 200:
                    return False
                content = request.read()
                self.logger.info("  Content: %s", content)
                return happy_message in content
        except Exception as ex:
            self.logger.error("  failed to get content of health page: %s", ex)
        return False

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
                    self.logger.warning(
                        "Can not find instance of %s in inventory: %s",
                        config['ENGINE_DB_HOST'], Host.inventory,
                    )
                    remote_host = [
                        Host(config['ENGINE_DB_HOST'])
                    ]
                    remote_host[0].add_user(self.host.root_user)
                remote_host = remote_host[0]
                self.logger.info(
                    "Using %s as host for DB %s (%s/%s), over SSH (%s/%s)",
                    remote_host,
                    config['ENGINE_DB_DATABASE'],
                    user.name, user.password,
                    remote_host.root_user.name,
                    remote_host.root_user.password,
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

    def wait_for_engine_status_up(self, timeout=360, interval=20):
        """
        Wait for the engine UP status

        Args:
            timeout (int): Timeout
            interval (int): Interval between samples

        Returns:
            bool: True, if the engine will have the status UP before timeout,
                otherwise False
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.health_page_status and self.api_page_status:
                return True
            time.sleep(interval)
        self.logger.error(
            "Engine still does not reachable after %s seconds", timeout
        )
        return False

    def restart(self):
        service = self.host.service(self.service_name)
        service.stop()
        service.start()
        self.wait_for_engine_status_up()

    def engine_config(self, action, param=None, restart=True, version=None):
        """ Runs engine-config command with given action
        Args:
             action (str): list, get, set, all
             param (str): parameter given to the command
            restart (bool): True to restart engine False otherwise
            version (str): The version of the parameter
        Returns:
            dict: Command returned output

        Raises:
            TypeError: if user send non supported action
        """
        res = {
            "results": dict()
        }
        cmd = ["engine-config"]
        actions = ["list", "get", "set", "all"]
        if action not in actions:
            raise TypeError("Action %s is not supported", action)

        cmd.extend(["--%s" % action])
        if param:
            cmd.extend([param])
        if version:
            cmd.extend(["--cver=%s" % version])
        executor = self.host.executor()
        rc, out, _ = executor.run_cmd(cmd)
        if rc:
            res["results"] = False
            return res

        if out:
            out_list = out.splitlines()
            for out_line in out_list:
                try:
                    out_split = out_line.split(":", 1)
                    key = out_split[0].strip()
                    out_split = out_split[1].strip()
                    if 'version:' in out_split:
                        value = out_split.split('version:')[0].strip()
                        version = out_split.split('version:')[-1].strip()
                    else:
                        value = out_split
                    if key:
                        res["results"].update(
                            {key: {'value': value, 'version': version}}
                        )

                except IndexError:
                    self.logger.info(
                        "Output that we couldn't split by ':' or "
                        "'version:' >> %s", out_line
                    )
                    continue
        else:
            res["results"] = True

        if restart and action == 'set':
            self.restart()

        return res

    def ovirt_aaa_jdbc_tool(self, action, what, name='*'):
        """
        Function allows you execute some actions of ovirt-aaa-jdbc-tool.

        Args:
            action (str): action you want to call:
                list - list of users/groups
                delete - delete user/group
            what (str): on which object do action: user or group
            name (str): name or pattern in list action case
        Returns:
            tuple: (rc, out, err)
        """
        JDBC_TOOL = 'ovirt-aaa-jdbc-tool'
        what_param = '--what=%s' % what

        # we can later implement more actions like add, edit
        actions = ['delete', 'list']
        if action not in actions:
            raise NotImplementedError("Action %s is not implemented" % action)
        if action == 'list':
            cmd = [
                JDBC_TOOL, 'query', '--pattern=name=%s' % name, what_param,
                '|', 'grep', '^Name:', '|', 'cut', '-d', ' ', '-f', '2'
            ]
        elif action == 'delete':
            cmd = [
                JDBC_TOOL, what, action, name
            ]

        executor = self.host.executor()
        with executor.session() as ss:
            return ss.run_cmd(cmd)
