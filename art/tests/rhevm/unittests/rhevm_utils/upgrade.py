
# Usage: rhevm-upgrade [options]
#
# Options:
#   -h, --help            show this help message and exit
#   -r, --no-yum-rollback
#                         don't rollback yum transaction
#   -u, --unattended      unattended upgrade (this option will stop jboss
#                         service before upgrading rhevm)
#   -s, --force-current-setup-rpm
#                         Ignore new rhevm-setup rpm
#   -c, --check-update    Check for available package updates

from rhevm_utils.base import Utility, logger, RHEVMUtilsTestCase
from rhevm_utils import errors

NAME = 'upgrade'

OPT_HELP = set(('h', 'help'))
OPT_UNATENDED = set(('u', 'unattended'))
OPT_NO_YUM_ROLLBACK = set(('r', 'no-yum-rollback'))
OPT_FORCE_CURRENT_SETUP_RPM = set(('s', 'force-current-setup-rpm'))
OPT_UPDATE = set(('c', 'check-update'))


# ( pattern, exeption, names of params, (sub errors, .. ) )
ERROR_PATTERNS = ()


class UpgradeUtility(Utility):
    """
    Encapsulation of rhevm-upgrade utility
    """
    def __init__(self, *args, **kwargs):
        super(UpgradeUtility, self).__init__(*args, **kwargs)
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        self.kwargs = self.clearParams(kwargs)

        if OPT_HELP not in self.kwargs and OPT_UNATENDED not in self.kwargs:
            logger.warn("adding --unattended option to avoid prompt")
            self.kwargs['unattended'] = None

        cmd = self.createCommand(NAME, self.kwargs)

        self.execute(NAME, cmd)

        #self.autoTest()

    # ====== TESTS ========

    def autoTest(self):
        if OPT_HELP in self.kwargs:
            self.testReturnCode()
            return
        self.testReturnCode()

#### UNITTESTS #####


class UpgradeTestCase(RHEVMUtilsTestCase):

    __test__ = False # FIXME: change to True, when you implement this
    utility = NAME
    utility_class = UpgradeUtility
    _multiprocess_can_split_ = True

