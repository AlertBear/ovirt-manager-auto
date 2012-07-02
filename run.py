#!/usr/bin/python

import os
import sys

project_path = os.path.abspath(os.path.dirname(__file__))
paths = list(set([os.path.abspath(x) for x in sys.path]) - set((project_path,)))
paths.insert(0, project_path)
sys.path = paths

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

