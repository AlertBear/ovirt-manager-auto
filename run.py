#!/usr/bin/python

from utils.test_runner import TestSuiteRunner
from utils.settings import populateOptsFromArgv, CmdLineError
from sys import argv, exit, stderr
import traceback

try:
    redefs = populateOptsFromArgv(argv)
    suiteRunner = TestSuiteRunner(redefs)
    suiteRunner.run_suite()
except KeyboardInterrupt:
    pass
except CmdLineError as e:
    print >>stderr, e
    print >>stderr, "Exitting with failure."
    exit(2)
except Exception as exc:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exitting with failure."
    exit(2)

