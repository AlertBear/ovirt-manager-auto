"""
Helper class to use ovirt-aaa-jdbc-tool, which manages oVirt jdbc users
"""
import logging

logger = logging.getLogger(__name__)


class JDBCCLI(object):
    """
    JDBC CLI helper
    This class will contruct ovirt-aaa-jdbc-tool commands
    Example of command:
     ovirt-aaa-jdbc-tool
       --log-level=log_level
       --db-config=profile
       module=self.entity
       action=*args[0]
       action_positional_argX=*args[X]
       action_named_argX=kwargs[X]
    """
    program = 'ovirt-aaa-jdbc-tool'

    def __init__(
        self,
        session,
        entity,
        profile='/etc/ovirt-engine/aaa/internal.properties',
        log_level='WARNING'
    ):
        """
        Initilize JDBCCLI

        :param session: session of config.ENGINE_HOST
        :type session: art.rhevm_api.resources.ssh.RemoteExecutor.Session
        :param entity: entity to run command for (user, group, query,...)
        :type entity: str
        :param profile: path to profile which should be used to run cmd
        :type profile: str
        :param log_level: log-level to run cmd with
        :type log_level: str
        """
        self.session = session
        self.cmd = [
            self.program,
            '--log-level=%s' % log_level,
            '--db-config=%s' % profile,
            entity,
        ]

    def run(self, *args, **kwargs):
        """
        run command

        :param args: args of command
        :param kwargs: named args of command
        :return: true if cmd ran successfully else false
        :rtype: bool
        """
        cmd = (
            self.cmd +
            list(args) +
            map(
                lambda (k, v): '--%s=%s' % (k.replace('_', '-'), v),
                kwargs.iteritems()
            )
        )
        with self.session as ss:
            logger.info("Run command: '%s'", cmd)
            rc, out, err = ss.run_cmd(cmd)
            logger.info("rc: '%s', out: '%s', err: '%s'", rc, out, err)

            return not rc
