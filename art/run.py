#!/usr/bin/python

import logging
from sys import argv, exit, stderr
import traceback
from socket import error as SocketError

from art.core_api.apis_exceptions import APICommandError, APIException
from art.test_handler.test_runner import TestRunner
from art.test_handler.settings import populateOptsFromArgv, CmdLineError, \
        initPlmanager, opts, readTestRunOpts
from art.test_handler.plmanagement import PluginError
from art.test_handler.reports import initializeLogger
from art.test_handler.settings import ReturnCode as RC
from art.test_handler.handler_lib.configs import ValidationError

logger = logging.getLogger(__name__)


def _main(plmanager):
    args = populateOptsFromArgv(argv)
    initializeLogger()
    logger.info("Log file name: %s" % opts['log'])
    config = readTestRunOpts(opts['conf'], args.redefs)
    if config['RUN']['debug']:
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

    plmanager.configure(args, config)
    runner = TestRunner(suitable_parser)
    plmanager.configurators.configure_app(config)
    plmanager.application_liteners.on_application_start()
    runner.run()


def _print_error(msg, ex):
    logger.debug(str(ex), exc_info=True)
    print >>stderr, ex
    print >>stderr, msg


def main():
    plmanager = None
    try:
        plmanager = initPlmanager()
        _main(plmanager)
    except KeyboardInterrupt:
        return 0
    except IOError as e:
        _print_error("Exiting with IO failure.", e)
        return RC.IO
    except SocketError as ex:
        traceback.print_exc(file=stderr)
        print >>stderr, "Exiting with Connection failure."
        return RC.Connection
    except CmdLineError as e:
        _print_error("Exiting with Command line failure.", e)
        return RC.CommandLine
    except ValidationError as e:
        _print_error("Exiting with Configuration Validation failure.", e)
        return RC.Validation
    except PluginError as e:
        print >>stderr, e
        _print_error("Exiting with failure.", e)
        return RC.Plugin
    except (APICommandError, APIException) as e:
        print >>stderr, e
        print >>stderr, "Exiting with API error."
        exit(RC.API)
    except Exception as exc:
        traceback.print_exc(file=stderr)
        print >>stderr, "Exiting with failure."
        return RC.General
    finally:
        if plmanager is not None:
            for listener in plmanager.application_liteners:
                try:
                    listener.on_application_exit()
                except Exception as ex:
                    logger.error(str(ex), exc_info=True)
    return 0


if __name__ == "__main__":
    exit(main())
