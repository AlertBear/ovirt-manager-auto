import sys
import traceback
from art.test_handler.plmanagement import PluginError


class VitalTestFailed(Exception):
    '''
    Raised when some vital test fails.
    '''
    def __init__(self, test_name):
        self.test_name = test_name

    def __str__(self):
        MSG = "Test '{0}' failed, can't run any further test."
        return MSG.format(self.test_name)


class Vital4GroupTestFailed(VitalTestFailed):
    '''
    Raised when some vital test on group level fails.
    '''
    pass


class CannotRunTests(Exception):
    ''' Raised when some problem occured during running the test scenario. '''


class TestComposeError(CannotRunTests):
    pass


class CanNotResolveActionPath(CannotRunTests):
    pass


class WrongIterableParams(CannotRunTests):
    pass


class SkipTest(Exception):
    pass


class TestExceptionType(type):
    """
    Customized type of exceptions which privides auto-discovery these
    exceptions
    """
    EXCEPTIONS = {}
    def __new__(cls, name, bases, dct):
        ex_cls = type.__new__(cls, name, bases, dct)
        cls.EXCEPTIONS[name] = ex_cls
        return ex_cls


class TestException(Exception):
    """
    Base class for exceptions used in negative test_cases, in order
    to identify specific (expected) type of fail.
    """
    __metaclass__ = TestExceptionType


class RHEVMEntityException(TestException):
    """
    Base class for particular RHEVM entities exceptions
    """
    pass


class DataCenterException(RHEVMEntityException):
    pass


class ClusterException(RHEVMEntityException):
    pass


class StorageDomainException(RHEVMEntityException):
    pass


class GlanceRepositoryException(RHEVMEntityException):
    pass


class GlanceImageException(RHEVMEntityException):
    pass


class HostException(RHEVMEntityException):
    pass


class VMException(RHEVMEntityException):
    pass


class TemplateException(RHEVMEntityException):
    pass


class DiskException(RHEVMEntityException):
    pass


class SnapshotException(RHEVMEntityException):
    pass


class UnkownConfigurationException(RHEVMEntityException):
    pass


class NetworkException(RHEVMEntityException):
    pass


class JobException(RHEVMEntityException):
    pass


class StepException(RHEVMEntityException):
    pass


class SchedulerException(RHEVMEntityException):
    pass


class VmPoolException(RHEVMEntityException):
    pass


class UserException(RHEVMEntityException):
    pass


def formatExcInfo():
    ei = sys.exc_info()
    einfo = traceback.format_exception(*ei)
    einfo.insert(0, einfo[-1])
    return ''.join(einfo)


class UnkownConfigurationException(RHEVMEntityException):
    pass


class ResourceError(RHEVMEntityException):
    """
    Base class for plugin- or other exceptions that must be caught inside ART
    to inherit.
    This is needed due to the way ART imports the plugins - they are not
    imported from art.test_handler.plmanagement.plugins, rather from
    art.test_handler.tools.
    To catch the exceptions either have the plugin exception inherit this as
    well as Plugin error, or create a more specific class here that inherits
    both of them and have the plugin exception inherit that, and then catch
    the more general exception.
    """
    pass


class CanNotFindIP(ResourceError, PluginError):
    pass


class QueryNotFoundException(RHEVMEntityException):
    """
    Exception for query not found (get_obj_by_query)
    """
    pass


class TearDownException(RHEVMEntityException):
    """
    Exception for failed teardown
    """
    pass


class HostedEngineException(RHEVMEntityException):
    """
    Exception for hosted engine errors
    """
    pass


class SriovException(RHEVMEntityException):
    pass
