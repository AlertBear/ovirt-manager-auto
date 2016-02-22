"""
Helper classes to use oVirt cli tools
"""
import logging

logger = logging.getLogger("art.utils.enginecli")


class EngineCLI(object):
    """
    Engine CLI helper
    This class will construct commands of cli tool
    Example of command:
     ovirt-aaa-jdbc-tool
       --log-level=log_level
       --db-config=profile
       module=self.entity
       action=*args[0]
       action_positional_argX=*args[X]
       action_named_argX=kwargs[X]
    """
    def __init__(self, tool, session, *args, **kwargs):
        """
        Initialize CLI

        :param tool: cli tool to be used
        :type tool: str
        :param session: session of config.ENGINE_HOST
        :type session: art.rhevm_api.resources.ssh.RemoteExecutor.Session
        :param args: unnamed arguments of cli
        :type args: list
        :param kwargs: parameters of tool
        :type kwargs: dict
        """
        self.tool = tool
        self.session = session
        self.cmd = [self.tool] + list(args) + self._map_kwargs(**kwargs)

    def setup_module(self, module, **kwargs):
        """
        Setup module and it's parameters

        :param module: module of cli tool to be used
        :type module: str
        :param kwargs: parameters of module
        :type kwargs: dict
        """
        self.cmd += [module] + self._map_kwargs(**kwargs)
        return self

    def run(self, *args, **kwargs):
        """
        run command with specific actions

        :param args: actions of module
        :type args: list
        :param kwargs: parameters of action of module
        :type kwargs: dict
        :return: true if cmd ran successfully else false and stdout of command
        :rtype: tuple
        """
        cmd = self.cmd + list(args) + self._map_kwargs(**kwargs)
        with self.session as ss:
            logger.info("Run command: '%s'", cmd)
            rc, out, err = ss.run_cmd(cmd)
            logger.info("rc: '%s', out: '%s', err: '%s'", rc, out, err)

            return not rc, out

    def _map_kwargs(self, **kwargs):
        return map(
            lambda (k, v): '--%s=%s' % (k.replace('_', '-'), v),
            kwargs.iteritems()
        )
