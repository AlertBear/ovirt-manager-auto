#!/usr/bin/python

from framework_utils.test_runner import TestSuiteRunner
from framework_utils.settings import populateOptsFromArgv, CmdLineError
from sys import argv, exit, stderr
import traceback
from socket import error as SocketError

try:
    redefs = populateOptsFromArgv(argv)
    suiteRunner = TestSuiteRunner(redefs)
    suiteRunner.run_suite()
except KeyboardInterrupt:
    pass
except SocketError:
    exit(2)
except CmdLineError as e:
    print >>stderr, e
    print >>stderr, "Exitting with failure."
    exit(2)
except Exception as exc:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exitting with failure."
    exit(2)

