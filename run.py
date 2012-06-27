#!/usr/bin/python

#import logging
#logging.basicConfig(level=logging.DEBUG)

from test_handler.test_suite_runner import TestSuiteRunner
from test_handler.settings import populateOptsFromArgv, CmdLineError, plmanager
from sys import argv, exit, stderr
import traceback
from socket import error as SocketError

try:
    redefs = populateOptsFromArgv(argv)
    suiteRunner = TestSuiteRunner(redefs)
    plmanager.configure()
    plmanager.application_liteners.on_application_start()
    suiteRunner.run_suite()
except KeyboardInterrupt:
    pass
except SocketError as ex:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exitting with failure."
    exit(2)
except CmdLineError as e:
    print >>stderr, e
    print >>stderr, "Exitting with failure."
    exit(2)
except Exception as exc:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exitting with failure."
    exit(2)
finally:
    plmanager.application_liteners.on_application_exit()

