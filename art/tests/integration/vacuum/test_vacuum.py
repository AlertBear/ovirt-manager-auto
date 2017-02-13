"""
Tests for engine-vacuum utility
"""
import itertools

from art.unittest_lib import attr, testflow
from art.test_handler.tools import polarion, bz

from vacuum_base import VacuumTest
import config
from config import logger


@attr(tier=2)
class TestNegative(VacuumTest):
    """
    Check negative test-cases on un-existing table
    """
    __test__ = True

    @polarion("RHEVM-18943")
    def test_wrong_table(self):
        """
        Test running vacuum on non-existing table
        """
        rc, out, err = self.run_engine_vacuum(table="test")
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, out, err = self.run_engine_vacuum(table="test", full=True)
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, out, err = self.run_engine_vacuum(table="test", analyze=True)
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, out, err = self.run_engine_vacuum(table="test", analyze_only=True)
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err


@attr(tier=2)
class TestSanityOptions(VacuumTest):
    """
    Check basic options of utility
    """
    __test__ = True

    @polarion("RHEVM-17206")
    def test_run_full(self):
        """
        Test running vacuum full
        """
        rc, _, err = self.run_engine_vacuum(full=True)

        testflow.step("Check return code and error output.")
        assert not rc and not err

    @polarion("RHEVM-18937")
    def test_run_no_options(self):
        """
        Test running vacuum full
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum()
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old
        assert vacuum_check and analyze_check

    @polarion("RHEVM-18939")
    def test_run_analyze(self):
        """
        Test running vacuum analyze
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum(analyze=True)
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @polarion("RHEVM-18941")
    def test_run_analyze_only(self):
        """
        Test running vacuum analyze only
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum(analyze_only=True)
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @bz({'1422562': {}})
    @polarion("RHEVM-18944")
    def test_print_help(self):
        """
        Test running vacuum utility with help
        """
        rc, out, err = self.run_engine_vacuum(help_param="-h")

        testflow.step("Check output of help.")
        assert not rc and out and not err

        rc, out2, err = self.run_engine_vacuum(help_param="--help")
        assert not rc and out and not err

        testflow.step("Check same help message is displayed.")
        assert out == out2
        logger.info("Standard output - %s", out)


@attr(tier=2)
class TestSpecificTable(VacuumTest):
    """
    Check vacuum utility on specific table
    """
    __test__ = True

    @polarion("RHEVM-17513")
    def test_run_full_table(self):
        """
        Test running vacuum full for specific table
        """
        rc, _, err = self.run_engine_vacuum(
            full=True, table=config.VM_DYNAMIC_TABLE
        )

        testflow.step("Check vacuum run successfully.")
        assert not rc and not err

    @polarion("RHEVM-18938")
    def test_run_table(self):
        """
        Test running vacuum for specific table
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum(
            table=config.VM_DYNAMIC_TABLE
        )
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old
        assert vacuum_check and analyze_check

    @polarion("RHEVM-18940")
    def test_run_analyze_table(self):
        """
        Test running vacuum analyze for specific table
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum(analyze=True, table=config.VM_DYNAMIC_TABLE)
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @polarion("RHEVM-18942")
    def test_run_analyze_only_table(self):
        """
        Test running vacuum analyze only for specific table
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats()
        self.run_engine_vacuum(
            analyze_only=True, table=config.VM_DYNAMIC_TABLE
        )
        vacuum_count, analyze_count = self.check_vacuum_stats()

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check


@attr(tier=2)
class TestVerboseMode(VacuumTest):
    """
    Check verbose mode and logging
    """
    __test__ = True

    @polarion("RHEVM-19093")
    def test_verbose_mode(self):
        """
        Test running vacuum with verbose mode
        """
        testflow.step("Build possible combinations for parameters.")
        param_type = (str(), config.FULL, config.ANALYZE, config.ANALYZE_ONLY)
        param_table = (config.VM_DYNAMIC_TABLE, None)
        param_list = list(itertools.product(param_type, param_table))

        for params in param_list:
            arguments = (
                params[0] == config.FULL, True, params[0] == config.ANALYZE,
                params[0] == config.ANALYZE_ONLY, params[1], str()
            )
            rc, _, err = self.run_engine_vacuum(*arguments)

            testflow.step("Check return value is 0.")
            assert not rc

            testflow.step("Check verbose mode is enabled in stdout.")
            assert config.VERBOSE_INFO in err
