import logging
import os
from art.rhevm_api.utils import test_utils
from art.test_handler import find_test_file

from lxml import etree
from art.core_api.apis_exceptions import EngineTypeError


logger = logging.getLogger(__name__)


def copy_extension_file(host, ext_file, target_file, chown='ovirt'):
    """
    :param host: host where copy file to
    :type host: instance of resources.Host
    :param ext_file: file to copy
    :type ext_file: str
    :param target_file: file to create
    :type target_file: str
    :param chown: permission to set
    :type chown: str / int
    """
    with host.executor().session() as ss:
        with open(ext_file) as fhs:
            with ss.open_file(target_file, 'w') as fhd:
                fhd.write(fhs.read())
        if chown:
            chown_cmd = [
                'chown', '%s:%s' % (chown, chown), target_file,
            ]
            res = ss.run_cmd(chown_cmd)
            assert not res[0], res[1]
    logger.info('Configuration "%s" has been copied.', ext_file)


class Extension(object):
    module_name = ''
    INTERVAL = 5
    TIMEOUT = 60
    CONFIG_DIRECTORY = 'tests/ldap/'
    EXTENSIONS_DIR = '/etc/ovirt-engine/extensions.d/'

    def __init__(self, host, engine):
        """
        :param host: host where engine is running
        :type host: instance of resources.Host
        :param engine: the engine
        :type engine: instance of resources.Engine
        """
        self.host = host
        self.engine = engine
        self.module_dir = find_test_file(
            '%s%s' % (self.CONFIG_DIRECTORY, self.module_name)
        )

    def __get_confs(self):
        """ get configuration from directory module_name """
        return os.listdir(self.module_dir)

    def add(self, apply=True):
        """
        :param apply: if true ovirt engine will be restarted
        :type apply: boolean
        """
        logger.info(self.module_name)
        for conf in self.__get_confs():
            ext_file = os.path.join(self.module_dir, conf)
            target_file = os.path.join(self.EXTENSIONS_DIR, conf)
            try:
                copy_extension_file(self.host, ext_file, target_file)
            except AssertionError as e:
                logger.error(
                    'Configuration "%s" has NOT been copied. Tests with '
                    'this configuration should be skipped. %s', conf, e
                )
        if apply:
            self.apply()

    def apply(self):
        test_utils.restart_engine(self.engine, self.INTERVAL, self.TIMEOUT)

    def remove(self, apply=True):
        with self.host.executor().session() as ss:
            for conf in self.__get_confs():
                ss.run_cmd([
                    'rm', '-f', os.path.join(self.EXTENSIONS_DIR, conf)
                ])
        if apply:
            self.apply()


class ADTLV(Extension):
    module_name = 'ad_tlv'


class BRQOpenLDAP(Extension):
    module_name = 'brq_openldap'


class XPathMatch(object):
    """
    This callable class can HTTP-GET the resource specified and perform a XPath
    query on the resource got. Then the result of XPath query is evaluated
    using eval(rslt_eval).

    Normally you actually won't need to set the positivity to any other
    value than True, because all the logic can be done in rslt_eval.

    Usage:
    # Instantiate the callable and call it.
    xpathMatch = XPathMatch(api)
    xpathMatch(True, 'hosts', 'count(/hosts//ksm/enabled)',
                    rslt_eval='match == 1')
    # Returns True iff exactly one tag matches.

    returns: True iff the test positivity equals the evaluation result.
    """

    def __init__(self, api_util):
        """
        A callable object that provides generic way to use XPath queries for
        all facilities as Hosts, Clusters and so on.

        param utils: An instance of restutils to use.
        param href:  An URL to HTTP-GET the doc to perform XPath query on.
        param links: A mapping of link and href.

        See the doc for XPathMatch for more details.
        """
        self.api = api_util

    def __call__(self, positive, link, xpath, rslt_eval='0. < result',
                 abs_link=False):
        """
        See the doc for XPathMatch for more details.
        """
        # A hack to make the XPathMatch able to match against the tags in the
        # RHEVM entry-point url.
        if self.api.opts['RUN']['engine'] != 'rest':
            raise EngineTypeError(
                "Engine type '%s' not supported by xpath" %
                self.api.opts['RUN']['engine']
            )

        if link.startswith('/'):
            matching_nodes = self.get_and_xpath_eval(link, xpath, abs_link)
        else:
            if 'api' == link:
                matching_nodes = self.get_and_xpath_eval(None, xpath, abs_link)
            else:
                matching_nodes = self.get_and_xpath_eval(link, xpath, abs_link)

        if positive != eval(rslt_eval, None, {'result': matching_nodes}):
            e = "XPath '%s' result evaluated using '%s' not equal to %s."
            self.api.logger.error(e % (xpath, rslt_eval, positive))
            return False
        else:
            self.api.logger.debug("XPath evaluation succeed.")
            return True

    def get_etree_parsed(self, link, abs_link):
        return etree.fromstring(self.api.get(link, abs_link=abs_link,
                                             no_parse=True))

    def get_and_xpath_eval(self, link, xpath, abs_link):
        return self.get_etree_parsed(link, abs_link).xpath(xpath)


class XPathLinks(XPathMatch):
    """
    This class is used to verify XPath on reponses which are referenced as
    links in api

    You have to specify entity_type  e.g. 'hosts' in constructor
    Author: jvorcak
    Usage:
        xpathHostsLinks = XPathLinks(api)
        xpathHostsLinks(True,
                        'host_address',
                        link_name='storage',
                        xpath='count(/base)')
    See @XPathMatch for more details
    """

    def __init__(self, api_util):
        XPathMatch.__init__(self, api_util)

    def __call__(self, positive, entity, link_name, xpath,
                 rslt_eval='0. < result'):

        if self.api.opts['RUN']['engine'] != 'rest':
            raise EngineTypeError(
                "Engine type '%s' not supported by xpath"
                % self.api.opts['RUN']['engine']
            )

        entityObj = self.api.find(entity)
        link = self.api.getElemFromLink(entityObj, link_name=link_name,
                                        attr=None, get_href=True)
        return XPathMatch.__call__(
            self, positive, link, xpath, rslt_eval, True)


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
            lambda (k, v): '--%s=%s' % (k.replace('_', '-'), v),  # flake8: noqa E999
            kwargs.iteritems()
        )
