"""
Tests for engine-vacuum utility
"""
import itertools
import pytest

from art.unittest_lib import (
    tier2, tier3
)
from art.unittest_lib import testflow
from art.test_handler.tools import polarion

from vacuum_base import VacuumTest
import config


@tier2
class TestNegative(VacuumTest):
    """
    Check negative test-cases on un-existing table
    """
    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18943")(False),
            polarion("RHEVM-22339")(True)
        ]
    )
    def test_wrong_table(self, dwh):
        """
        Test running vacuum on non-existing table

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        rc, _, err = self.run_engine_vacuum(
            on_table=True, table="test", dwh=dwh
        )
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, _, err = self.run_engine_vacuum(
            on_table=True, table="test", full=True, dwh=dwh
        )
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, _, err = self.run_engine_vacuum(
            on_table=True, table="test", analyze=True, dwh=dwh
        )
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err

        rc, _, err = self.run_engine_vacuum(
            on_table=True, table="test", analyze_only=True, dwh=dwh
        )
        testflow.step("Check non-zero return code and stderr.")
        assert rc and err


@tier2
class TestSanityOptions(VacuumTest):
    """
    Check basic options of utility
    """
    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18937")(False),
            polarion("RHEVM-22343")(True)
        ]
    )
    def test_run_no_options(self, dwh):
        """
        Test running vacuum

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(dwh=dwh)
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old
        assert vacuum_check and analyze_check

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18939")(False),
            polarion("RHEVM-22349")(True)
        ]
    )
    def test_run_analyze(self, dwh):
        """
        Test running vacuum analyze

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(analyze=True, dwh=dwh)
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18941")(False),
            polarion("RHEVM-22347")(True)
        ]
    )
    def test_run_analyze_only(self, dwh):
        """
        Test running analyze only

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(analyze_only=True, dwh=dwh)
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18944")(False),
            polarion("RHEVM-22339")(True)
        ]
    )
    def test_print_help(self, dwh):
        """
        Test running vacuum utility with help

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        rc, out, err = self.run_engine_vacuum(help_param="-h", dwh=dwh)

        testflow.step("Check output of help.")
        assert not rc and out and not err

        rc, out2, err = self.run_engine_vacuum(help_param="--help", dwh=dwh)
        assert not rc and out and not err

        testflow.step("Check same help message is displayed.")
        assert out == out2
        config.logger.info("Standard output - %s", out)


@tier2
class TestSpecificTable(VacuumTest):
    """
    Check vacuum utility on specific table
    """
    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18938")(False),
            polarion("RHEVM-22342")(True)
        ]
    )
    def test_run_table(self, dwh):
        """
        Test running vacuum on specific table

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(on_table=True, dwh=dwh)
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old
        assert vacuum_check and analyze_check

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18940")(False),
            polarion("RHEVM-22348")(True)
        ]
    )
    def test_run_analyze_table(self, dwh):
        """
        Test running vacuum analyze on specific table

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(analyze=True, on_table=True, dwh=dwh)
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old + 1
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-18942")(False),
            polarion("RHEVM-22346")(True)
        ]
    )
    def test_run_analyze_only_table(self, dwh):
        """
        Test running analyze only on specific table

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        vacuum_count_old, analyze_count_old = self.check_vacuum_stats(dwh=dwh)
        self.run_engine_vacuum(
            analyze_only=True, on_table=True, dwh=dwh
        )
        vacuum_count, analyze_count = self.check_vacuum_stats(
            dwh=dwh, result_prev=(vacuum_count_old, analyze_count_old)
        )

        testflow.step("Check vacuum and analyze count.")
        vacuum_check = vacuum_count == vacuum_count_old
        analyze_check = analyze_count == analyze_count_old + 1
        assert vacuum_check and analyze_check


@tier2
class TestVerboseMode(VacuumTest):
    """
    Check verbose mode and logging
    """
    @polarion("RHEVM-19093")
    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-19093")(False),
            polarion("RHEVM-22340")(True)
        ]
    )
    def test_verbose_mode(self, dwh):
        """
        Test running vacuum with verbose mode

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        testflow.step("Build possible combinations for parameters.")
        param_type = (str(), config.ANALYZE, config.ANALYZE_ONLY)
        param_on_table = (True, False)
        param_list = list(itertools.product(param_type, param_on_table))

        for params in param_list:
            arguments = (
                False, True, params[0] == config.ANALYZE,
                params[0] == config.ANALYZE_ONLY, params[1], None, str(), dwh
            )
            rc, _, err = self.run_engine_vacuum(*arguments)

            testflow.step("Check return value is 0.")
            assert not rc

            testflow.step("Check verbose mode is enabled in stdout.")
            assert config.VERBOSE_INFO in err


@tier3
class TestAdvancedOptions(VacuumTest):
    """
    Check vacuum full
    """
    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-17206")(False),
            polarion("RHEVM-22345")(True)
        ]
    )
    def test_run_full(self, dwh):
        """
        Test running vacuum full

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        self.run_full_vacuum(self, dwh=dwh)

    @pytest.mark.parametrize(
        "dwh",
        [
            polarion("RHEVM-17513")(False),
            polarion("RHEVM-22344")(True)
        ]
    )
    def test_run_full_table(self, dwh):
        """
        Test running vacuum full on specific table

        Args:
            dwh (boolean): True - use dwh vacuum tool instead of engine
        """
        self.run_full_vacuum(on_table=True, dwh=dwh)
