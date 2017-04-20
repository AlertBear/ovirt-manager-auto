"""
Base class with methods for vacuum tests
"""
from art.unittest_lib import testflow
from art.unittest_lib import CoreSystemTest as TestCase
import art.test_handler.exceptions as ex

import config
from config import logger


class VacuumTest(TestCase):
    """ Base class for tests of vacuum """
    @staticmethod
    def run_engine_vacuum(
        full=False, verbose=False, analyze=False, analyze_only=False,
        table=None, help_param=str()
    ):
        """
        Run engine-vacuum utility on engine machine

        Args:
            full (boolean): True if -f parameter should be added
            verbose (boolean): True if -v parameter should be added
            analyze (boolean): True if -a parameter should be added
            analyze_only (boolean): True if -A parameter should be added
            table (string): if parameter -t string should be added
            help_param (string): empty string, -h or --help

        Returns:
            (rc, stdout, stderr): Return tuple of return code, standard output
                and standard error output
        """
        cmd = [config.VACUUM_UTIL]
        if full:
            cmd.append(config.FULL)
        if verbose:
            cmd.append(config.VERBOSE)
        if analyze:
            cmd.append(config.ANALYZE)
        if analyze_only:
            cmd.append(config.ANALYZE_ONLY)
        if table:
            cmd.append(" ".join([config.TABLE, table]))
        if help_param:
            cmd.append(help_param)
        logger.info("Command - %s", " ".join(cmd))

        testflow.step("Running engine vacuum")
        return config.ENGINE_HOST.executor().run_cmd(cmd)

    @classmethod
    def check_vacuum_stats(cls, table=config.VM_DYNAMIC_TABLE):
        """
        Check values vacuum_count, analyze_count in database

        Args:
            table (string): on which table to check

        Returns:
            (vacuum_count, analysis_count): Returns tuple of values how many
                vacuums and vacuum analysis where run on the specific table
        """
        testflow.step("Check vacuum is not running on table %s", table)
        out = config.ENGINE.db.psql(config.SQL_VACUUM_STATS)
        if not out:
            raise ex.TestException(
                "Unable to check stats of vacuum - %s" % out
            )
        logger.info("Output of sql - %s.", out)

        testflow.step(
            "Get vacuum_count and analyse_count from DB for table %s",
            table
        )
        return int(out[0][0]), int(out[0][1])
