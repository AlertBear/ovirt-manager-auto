
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


