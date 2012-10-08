
# USAGE:
#     rhevm-manage-domains -action=ACTION [-domain=DOMAIN -user=USER -passwordFile=PASSWORD_FILE -interactive -configFile=PATH] -report
# Where:
#     ACTION             action to perform (add/edit/delete/validate/list). See details below.
#     DOMAIN              (mandatory for add, edit and delete) the domain you wish to perform the action on.
#     USER             (optional for edit, mandatory for add) the domain user.
#     PASSWORD_FILE            (optional for edit, mandatory for add) a file containing the password in the first line.
#     interactive        alternative for using -passwordFile - read the password interactively.
#     PATH               (optional) use the given alternate configuration file.
#
#     Available actions:
#     add
#     Examples:
#         -action=add -domain=example.com -user=admin -passwordFile=/tmp/.pwd
#             Add a domain called example.com, using user admin and read the password from /tmp/.pwd.
#         -action=edit -domain=example.com -passwordFile=/tmp/.new_password
#             Edit the domain example.com, using another password file.
#         -action=delete -domain=example.com
#             Delete the domain example.com.
#         -action=validate
#             Validate the current configuration (go over all the domains, try to authenticate to each domain using the configured user/password.).
#         -report In combination with -action=validate will report all validation error, if occured.
#             Default behaviour is to exit when a validation error occurs.
#         -action=list
#             Lists the current configuration.
#         -h
#             Show this help.


from rhevm_utils.base import Utility, logger, RHEVMUtilsTestCase
from rhevm_utils import errors

NAME = 'manage-domains'

OPT_HELP = set(('h', 'help'))
OPT_ACTION = 'action'
OPT_INTERACTIVE = 'interactive'
OPT_REPORT = 'report'
OPT_PASSWORD_FILE = 'passwordFile'
OPT_DOMAIN = 'domain'
OPT_USER = 'user'

ACTION_ADD = 'add'
ACTION_EDIT = 'edit'
ACTION_DELETE = 'delete'
ACTION_VALIDATE = 'validate'
ACTION_LIST = 'list'

OPTIONS_TABLE = 'vdc_options'
OPTION_VALUE_COLUMN = 'option_value'
OPTION_NAME_COLUMN = 'option_name'

# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = (
        ( 'Domain (?P<name>[^ ]+) already exists in the configuration', \
            errors.DomainAlreadyExists, ('name',), ()
        ),
        ( "Domain (?P<name>[^ ]+) doesn't exist in the configuration.", \
            errors.DomainDoesNotExists, ('name',), ()
        ),
        ( "Invalid argument (?P<name>[^ ]+)", \
            errors.InvalidParameter, ('name',), ()
        ),
        ( "(?P<name>[^ ]+) is not a valid action", \
            errors.InvalidAction, ('name',), ()
        ),
        ( "Argument (?P<name>) is required", \
            errors.MissingParameter, ('name',), ()
        ),
    )

class ManageDomainsUtility(Utility):
    """
    Encapsulation of rhevm-manage-domains utility
    """
    def __init__(self, *args, **kwargs):
        super(ManageDomainsUtility, self).__init__(*args, **kwargs)
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.kwargs = self.clearParams(kwargs)

        if OPT_INTERACTIVE in self.kwargs:
            logger.warning("test requires paswordFile instead of interactive")

        cmd = self.createCommand(NAME, self.kwargs, '-')

        self.execute(NAME, cmd)

        #self.autoTest()

    def retrieveDomains(self):
        """
        Retrieves list of known domains
        Return: {domain: user, ..}
        """
        sql = 'SELECT %s FROM %s where %s = "DomainName" LIMIT 1'
        data = self.setup.psql(sql, OPTION_VALUE_COLUMN, OPTIONS_TABLE,\
                OPTION_NAME_COLUMN)
        domains = data[0][0].split(',')
        sql = 'SELECT %s FROM %s where %s = "AdUserName" LIMIT 1'
        data = self.setup.psql(sql, OPTION_VALUE_COLUMN, OPTIONS_TABLE,\
                OPTION_NAME_COLUMN)
        users = data[0][0].split(',')
        res = {}
        for user in users:
            domain, user = user.split(':', 1)
            res[domain] = user
        if set(domains) & set(res.keys()):
            raise errors.InconsistentDataInDB(domains, res.keys())
        return res

    # ====== TESTS ========

    def autoTest(self):
        if not self.kwargs and self.out:
            self.testReturnCode(1)
            return
        if self.rc == 0:
            if OPT_ACTION in self.kwargs:
                if self.kwargs[OPT_ACTION] == ACTION_ADD:
                    self.testAddAction()
                elif self.kwargs[OPT_ACTION] == ACTION_EDIT:
                    self.testEditAction()
                elif self.kwargs[OPT_ACTION] == ACTION_DELETE:
                    self.testDeleteAction()
                elif self.kwargs[OPT_ACTION] == ACTION_VALIDATE:
                    self.testValidateAction()
                elif self.kwargs[OPT_ACTION] == ACTION_LIST:
                    self.testListAction()
        else:
            self.recognizeError()
        self.testReturnCode()

    def testAddAction(self):
        data = self.retrieveDomains()
        if not self.kwargs[OPT_DOMAIN] in data:
            raise errors.MissingDmainError(self.kwargs[OPT_DOMAIN])
        if data[self.kwargs[OPT_DOMAIN]] != self.kwargs[OPT_USER]:
            msg = "'%s' != '%s'" % (self.kwargs[OPT_USER], data[self.kwargs[OPT_DOMAIN]])
            raise errors.UnexpectedUserError(msg)

    def testEditAction(self):
        self.testAddAction()

    def testDeleteAction(self):
        data = self.retrieveDomains()
        if self.kwargs[OPT_DOMAIN] in data:
            raise errors.RedundantDmainError(self.kwargs[OPT_DOMAIN])

    def testValidateAction(self):
        #TODO: validate
        pass

    def testListAction(self):
        # TODO: list action
        pass

#### UNITTESTS #####


class ManageDomainsTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = ManageDomainsUtility
    _multiprocess_can_split_ = True

