
# rhevm-config: get/set/list configuration
# USAGE:
#     rhevm-config ACTION [--cver=version] [-p | --properties=/path/to/alternate/property/file] [-c | --config=/path/to/alternate/config/file]
# Where:
#     ACTION              action to perform, see details below
#     version             relevant configuration version to use.
#     -p, --properties=   (optional) use the given alternate properties file.
#     -c, --config=       (optional) use the given alternate configuration file.
#
#     Available actions:
#     -l, --list
#         list available configuration keys.
#     -a, --all
#         get all available configuration values.
#     -g key, --get=key [--cver=version]
#         get the value of the given key for the given version. If a version is not given, the values of all existing versions are returned.
#     -s key=val --cver=version, --set key=val --cver=version
#         set the value of the given key for the given version. The cver version is mandatory for this action.
#     -h, --help
#         display this help and exit.
#
# ### Note: In order for your change(s) to take effect,
# ### restart the JBoss service (using: 'service jbossas restart').
# #############################################################################


from rhevm_utils.base import Utility, BIN, logger, RHEVMUtilsTestCase
from rhevm_utils import errors

NAME = 'config'

OPT_HELP = set(('h', 'help'))
OPT_LIST = set(('l', 'list'))
OPT_ALL = set(('a', 'all'))
OPT_GET = set(('g', 'get'))
OPT_SET = set(('s', 'set'))
OPT_CVER = 'cver'
OPT_PROP = set(('p', 'properties'))

OPT_ACTIONS = [OPT_SET, OPT_GET]

PATH_TO_PROPERTIES = 'PATH_TO_CONFIG_PROPERTIES'

OPTIONS_TABLE = 'vdc_options'
VERSION_COLUMN = 'version'
NAME_COLUMN = 'option_name'
VALUE_COLUMN = 'option_value'

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = ()

class ConfigUtility(Utility):
    """
    Encapsulation of rhevm-config utility
    """
    def __init__(self, *args, **kwargs):
        super(ConfigUtility, self).__init__(*args, **kwargs)
        self.kwargs = None

    @property
    def pathToDefaultProperties(self):
        return PATH_TO_PROPERTIES % tuple([self.setup.product for i in range(3)])

    def __call__(self, *args, **kwargs):
        self.kwargs = self.clearParams(kwargs)

        if OPT_SET in self.kwargs and OPT_CVER not in self.kwargs:
            logger.warn("the version specification is missing. "\
                    "it could lead to stuck")

        cmd = self.createCommand(NAME, self.kwargs, long_glue=' ')

        self.execute(NAME, cmd)

        #self.autoTest()

    def createCommand(self, name, kwargs, long_prefix='--', long_glue='='):
        cmd = super(ConfigUtility, self).createCommand(name, kwargs, \
                long_prefix, long_glue)
        actions = ('-s', '--set', '-g', '--get')
        newCmd = []
        for arg in cmd[1:]:
            if long_glue in arg:
                act, val = arg.split(long_glue)
            else:
                act = arg
                val = None
            if [x for x in actions if x == act]:
                newCmd.insert(0, val)
                newCmd.insert(0, act)
            else:
                newCmd.append(act)
                if val is not None:
                    newCmd.append(val)
        newCmd.insert(0, cmd[0])
        return newCmd

    def isConfigOptionAllowed(self, option, path):
        """
        Check whether option is allowed by property file
        Parameters:
         * option - name of option
         * path - path to property file
        """
        cmd = [BIN['grep'], '^%s[.]' % option, path]
        with self.setup.ssh as ssh:
            fh = ssh.getFileHandler()
            if fh.exists(path):
                rc, out, err = ssh.runCmd(cmd, \
                        conn_timeout=self.setup.connectionTimeout)
                logger.info('%s, %s, %s', rc, out, err)
            else:
                raise errors.MissingPropertyFile(path)
        return rc == 0

    def fetchOption(self, key):
        """
        Fetch value for key
        Parameters:
         * key - name of option
        Return: (('value', 'version'), ('val', 'ver'), ..)
        """
        sql = "SELECT %s, %s FROM %s WHERE %s = '%s';"
        res = self.setup.psql(sql, VALUE_COLUMN, VERSION_COLUMN, \
                OPTIONS_TABLE, NAME_COLUMN, key)
        if not res:
            raise errors.FetchOptionError(key)
        return res

    def retrieveSecretKeys(self, propertyFile):
        """
        Fetch list of secret options
        Parameters:
         * propertyFile - path to property file
        """
        with self.setup.ssh as ssh:
            rc, out, err = ssh.runCmd([BIN['grep'], 'type=Password', \
                    propertyFile, '|', BIN['cut'], '-d.', '-f1'], \
                    timeout=self.setup.execTimeout)
            if rc:
                raise errors.ConfigUtilityError(\
                        "failed to retrieve secret keys: %s" % err)
        return out.splitlines()


    # ====== TESTS ========

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return
        if OPT_LIST in self.kwargs:
            self.testListAction()
        if OPT_GET in self.kwargs:
            self.testGetAction(self.kwargs[OPT_GET], \
                    self.kwargs.get(OPT_CVER, None), \
                    self.kwargs.get(OPT_PROP, None))
        if OPT_SET in self.kwargs:
            self.testSetAction(self.kwargs[OPT_SET], \
                    self.kwargs.get(OPT_CVER, None), \
                    self.kwargs.get(OPT_PROP, None))

    def testListAction(self):
        self.testReturnCode()
        if not self.out.strip():
            # FIXME: Maybe we will need to check option according properties file
            raise errors.ConfigUtilityError("there is no output: %s", self.out)

    def __testGetOption(self, key, propertyFile):
        if propertyFile is None:
            propertyFile = self.getVar(PATH_TO_PROPERTIES)
        opts = {}
        try:
            if self.isConfigOptionAllowed(key, propertyFile):
                opts = self.fetchOption(key)
            else:
                raise errors.OptionIsNotAllowed(key)
        except errors.MissingPropertyFile as ex:
            logger.warn("%s", ex)
            self.testReturnCode(1)
        except errors.FetchOptionError as ex:
            logger.info("failed to use option '%s': %s", key, ex)
            self.testReturnCode(1)
        logger.info(opts)
        opts = dict((a[1], a[0]) for a in opts)

        return opts

    def testGetAction(self, key, version, propertyFile):
        if propertyFile is None:
            propertyFile = self.getVar(PATH_TO_PROPERTIES)
        opt = self.__testGetOption(key, propertyFile)
        if not opt:
            return

        secretKeys = self.retrieveSecretKeys(propertyFile)
        def adjustValue(key, val):
            if key in secretKeys:
                if val:
                    val = 'Set'
                else:
                    val = 'Empty'
            return val

        if version is None:
            for ver, val in opt.items():
                val = adjustValue(key, val)
                exp = "%s: %s version: %s" % (key, val, ver)
                if exp in self.out:
                    logger.debug("found expected string: %s", exp)
                else:
                    raise errors.OutputVerificationError(exp, self.out)
        else:
            val = adjustValue(key, opt.values()[0])
            if val not in self.out:
                raise errors.OutputVerificationError(val)
        self.testReturnCode()


    def testSetAction(self, key, version, propertyFile):
        try:
            key, val = key.split('=')
        except ValueError:
            self.testReturnCode(1)
            return
        opt = self.__testGetOption(key, propertyFile)
        if not opt:
            return
        if version is None and len(opt) == 1:
            version = opt.keys()[0]
        if version not in opt:
            exp = "No such entry with version %s" % version
            if exp not in self.err:
                raise errors.OutputVerificationError(exp, self.err)
            self.testReturnCode(1)
            return
        if opt[version] != val and self.rc == 0:
            raise errors.FailedToSetValue(key, val, version)
        self.testReturnCode()

#### UNITTESTS #####


class ConfigTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ConfigUtility
    _multiprocess_can_split_ = True

