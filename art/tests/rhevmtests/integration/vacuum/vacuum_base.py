"""
Base classes with methods for vacuum tests
"""
from art.unittest_lib import testflow
from art.unittest_lib import CoreSystemTest as TestCase
from art.core_api.apis_utils import TimeoutingSampler
import art.test_handler.exceptions as ex

from rrmngmnt.db import Database
from rrmngmnt.host import Host
from rrmngmnt.user import User

import config


class VacuumDwhDb():
    """ Singleton for getting dwh database """

    instance = None

    def __init__(cls):
        if not VacuumDwhDb.instance:
            try:
                testflow.setup("Get dwh database object")
                db_cfg = config.ENGINE._read_config(config.DWH_DATABASE_CONFIG)
                db_host = db_cfg['DWH_DB_HOST']
                user = User(db_cfg['DWH_DB_USER'], db_cfg['DWH_DB_PASSWORD'])
                if db_host != 'localhost':
                    host = Host(db_host)
                    host.add_user(config.ENGINE.host.root_user)
                else:
                    host = config.ENGINE.host
                VacuumDwhDb.instance = Database(
                    host, db_cfg['DWH_DB_DATABASE'], user
                )
            except KeyError:
                raise EnvironmentError(
                    "No dwh settings in engine environment!"
                )

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)


class VacuumTest(TestCase):
    """ Base class for tests of vacuum """

    @staticmethod
    def run_engine_vacuum(
        full=False, verbose=False, analyze=False, analyze_only=False,
        on_table=False, table=None, help_param=str(), dwh=False,
        stop_service=False
    ):
        """
        Run vacuum utility on engine machine

        Args:
            full (boolean): True if -f parameter should be added
            verbose (boolean): True if -v parameter should be added
            analyze (boolean): True if -a parameter should be added
            analyze_only (boolean): True if -A parameter should be added
            on_table (boolean): True - if parameter -t string should be added
            table (string): run on specific table other than test tables
                from config
            help_param (string): empty string, -h or --help
            dwh (boolean): True - use dwh vacuum tool instead of engine

        Returns:
            (rc, stdout, stderr): Return tuple of return code, standard output
                and standard error output
        """
        if dwh:
            cmd = [config.VACUUM_DWH_UTIL]
            cmd_table = config.VACUUM_DWH_TABLE
            service_name = "ovirt-engine-dwhd"
        else:
            cmd = [config.VACUUM_UTIL]
            cmd_table = config.VACUUM_TABLE
            service_name = "ovirt-engine"
        if full:
            cmd.append(config.FULL)
        if verbose:
            cmd.append(config.VERBOSE)
        if analyze:
            cmd.append(config.ANALYZE)
        if analyze_only:
            cmd.append(config.ANALYZE_ONLY)
        if on_table:
            if not table:
                table = cmd_table
            cmd.append(" ".join([config.TABLE, table]))
        if help_param:
            cmd.append(help_param)

        if stop_service:
            config.logger.info("Stopping service - %s", service_name)
            assert config.ENGINE_HOST.service(
                service_name
            ).stop(), "There was an error while stopping a service."

        config.logger.info("Command - %s", " ".join(cmd))

        testflow.step("Running vacuum")
        rc, out, err = config.ENGINE_HOST.executor().run_cmd(cmd)

        if stop_service:
            config.logger.info("Starting service - %s", service_name)
            assert config.ENGINE_HOST.service(
                service_name
            ).start(), "There was an error while starting a service."

        return rc, out, err

    @classmethod
    def check_vacuum_stats(cls, table=None, dwh=False, result_prev=None):
        """
        Check values vacuum_count, analyze_count in database

        Args:
            table (string): on which table to check
            dwh (boolean): if table is not set use dwh/engine test table
                depending on this parameter
            result_prev (tupple): previous result of check_vacuum_stats to
                compare changes

        Returns:
            (vacuum_count, analysis_count): Returns tuple of values how many
                vacuums and vacuum analysis where run on the specific table
        """
        if not table:
            if dwh:
                table = config.VACUUM_DWH_TABLE
            else:
                table = config.VACUUM_TABLE
        if dwh:
            db = VacuumDwhDb()
        else:
            db = config.ENGINE.db
        testflow.step("Check vacuum is not running on table %s", table)

        result = None
        for out in TimeoutingSampler(
            timeout=config.GET_STATS_TIMEOUT, sleep=config.GET_STATS_SLEEP,
            func=db.psql,
            sql=config.SQL_VACUUM_STATS.format(table)
        ):
            if not out:
                raise ex.TestException(
                    "Unable to check stats of vacuum - %s" % out
                )
            result = int(out[0][0]), int(out[0][1])
            if (
                not result_prev or (
                    result[0] != result_prev[0] or result[1] != result_prev[1]
                )
            ):
                break
            result_prev = result

        config.logger.info("Output of sql - %s.", result)

        testflow.step(
            "Get vacuum_count and analyse_count from DB for table %s",
            table
        )
        return result

    @classmethod
    def run_full_vacuum(cls, on_table=False, dwh=False):
        """
        Run full vacuum tests and check results

        Args:
            on_table (boolean): True - if parameter -t string should be added
            dwh (boolean): if table is not set use dwh/engine test table
                depending on this parameter
        """
        testflow.step("Run full vacuum.")
        rc, _, _ = cls.run_engine_vacuum(
            full=True, on_table=on_table, dwh=dwh, stop_service=True
        )

        testflow.step("Check vacuum run successfully.")
        assert not rc

        testflow.step("Run full vacuum in verbose mode.")
        rc, _, err = cls.run_engine_vacuum(
            full=True, on_table=on_table, dwh=dwh, stop_service=True,
            verbose=True
        )

        testflow.step("Check return value is 0.")
        assert not rc

        testflow.step("Check verbose mode is enabled in stdout.")
        assert config.VERBOSE_INFO in err
