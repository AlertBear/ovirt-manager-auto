#!/usr/bin/python

import os
import sys
import logging
from sys import argv, exit, stderr
import traceback
from socket import error as SocketError

project_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = list(set([os.path.abspath(x) for x in sys.path]) - set((project_path,)))
paths.insert(0, project_path)
sys.path = paths

from art.test_handler.test_runner import TestRunner
from art.test_handler.settings import populateOptsFromArgv, CmdLineError, \
        initPlmanager, opts, readTestRunOpts
from art.test_handler.plmanagement import PluginError
from art.test_handler.reports import initializeLogger
from art.test_handler.settings import ReturnCode as RC
from art.test_handler.handler_lib.configs import ValidationError


try:
    plmanager = initPlmanager()
    redefs = populateOptsFromArgv(argv)
    initializeLogger()
    logger = logging.getLogger(__name__)
    logger.info("Log file name: %s" % opts['log'])
    config = readTestRunOpts(opts['conf'], redefs)
    if opts['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
    test_iden = config['RUN']['tests_file']
    suitable_parser = None
    for parser in plmanager.test_parsers:
        if suitable_parser is None and parser.is_able_to_run(test_iden):
            suitable_parser = parser
        else:
            plmanager.disable_component(parser)
    if suitable_parser is None:
        raise Exception("can not find suitable test_parser for %s" % test_iden)

    plmanager.configure()
    runner = TestRunner(suitable_parser)
    plmanager.application_liteners.on_application_start()
    runner.run()
except KeyboardInterrupt:
    pass
except IOError as e:
    print >>stderr, e
    print >>stderr, "Exiting with IO failure."
    exit(RC.IO)
except SocketError as ex:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exiting with Connection failure."
    exit(RC.Connection)
except CmdLineError as e:
    print >>stderr, e
    print >>stderr, "Exiting with Command line failure."
    exit(RC.CommandLine)
except ValidationError as e:
    print >>stderr, e
    print >>stderr, "Exiting with Configuration Validation failure."
    exit(RC.Validation)
except PluginError as e:
    print >>stderr, e
    print >>stderr, "Exiting with failure."
    exit(RC.Plugin)
except Exception as exc:
    traceback.print_exc(file=stderr)
    print >>stderr, "Exiting with failure."
    exit(RC.General)
finally:
    if plmanager is not None:
        plmanager.application_liteners.on_application_exit()
