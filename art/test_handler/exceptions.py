
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


class VmPoolException(RHEVMEntityException):
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


class CanNotFindIP(ResourceError):
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
