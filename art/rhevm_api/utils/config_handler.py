#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Config file handling
"""

import ConfigParser
import StringIO
import logging
import shlex

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_SECTION_NAME = "global"


class ConfigFileReadingError(Exception):
    """
    Exception for error in config file reading
    """
    def __init__(self, path):
        super(ConfigFileReadingError, self).__init__(
            "FileSystem reading error occurred while reading configuration"
            " file: {0}.", path
        )
        logger.error("Failed reading config file: %s", path)


class ConfigParsingError(Exception):
    """
    Exception for error in config file parsing
    """
    def __init__(self, path, error):
        super(ConfigParsingError, self).__init__(
            "Exception '{0}' occurred while parsing configuration file: "
            "{1}.", error, path
        )
        logger.error("Failed parsing config file: %s", error)


class HostConfigFileHandler(object):
    """
    Host config file (INI-like style) handler
    """

    def __init__(self, host, path):
        """
        Initialize Host Config Handler

        Args:
            host (Host): Host resource object
            path (str): Config file path
        """
        self._host = host
        self._path = path
        self._content = ""
        self._parser = ConfigParser.ConfigParser()
        # Override lower-case transformation in ConfigParser
        self._parser.optionxform = str
        self._parser_io = None
        self._section_less = False
        # Load and parse config file
        self._load_config()

    def _parse_file(self):
        """
        Parse config file using ConfigParser

        Raises:
            MissingSectionHeaderError: In case of missing section header in
                config file ("section-less")
            ParsingError: In case of config parsing error
        """
        try:
            self._parser_io = StringIO.StringIO(self._content)
            self._parser_io.seek(0)
            self._parser.readfp(self._parser_io)
        except ConfigParser.MissingSectionHeaderError:
            self._section_less = True
            logger.debug(
                "Config file: %s is section-less. "
                "Adding a default section [%s] to the file",
                self._path, DEFAULT_CONFIG_SECTION_NAME
            )
            self._content = "[{sn}]\n{content}".format(
                sn=DEFAULT_CONFIG_SECTION_NAME, content=self._content
            )
            self._parse_file()
        except ConfigParser.ParsingError as e:
            raise ConfigParsingError(self._path, e.message)
        finally:
            self._parser_io.close()

    def _flush_content(self):
        """
        Flush parser file, and save file content on memory
        """
        if self._parser_io:
            self._parser_io.close()
        self._parser_io = StringIO.StringIO()
        self._parser.write(self._parser_io)
        self._content = self._parser_io.getvalue()

    def _load_config(self):
        """
        Load config file on ConfigParser

        Raises:
            ConfigFileReadingError: In case of config reading error
        """
        self._content = self._host.fs.read_file(self._path)

        if not self._content:
            raise ConfigFileReadingError("Host filesystem reading error")

        self._parse_file()

    def _save_config(self):
        """
        Save config file on host

        Returns:
            str: Backup filename, or empty string if error occurred
        """
        self._flush_content()

        if self._section_less:
            # Remove the additional section in section-less file, in order to
            # keep the original structure of the file
            self._content = self._content.split("\n", 1)[1]

        logger.info("Saving a backup for existing config file: %s", self._path)
        backup_filename = "{file}.bak".format(file=self._path)
        file_copy_cmd = "cp -pf {src} {dst}".format(
            src=self._path, dst=backup_filename
        )
        rc, _, err = self._host.run_command(shlex.split(file_copy_cmd))
        if rc:
            logger.error("Host file: %s writing error: %s", self._path, err)
            return ""

        logger.debug(
            "Saving content:\n%s\non file: %s", self._content, self._path
        )
        logger.info("Saving changes on file: %s", self._path)
        mode = self._host.os.get_file_permissions(self._path)
        self._host.fs.create_script(self._content, self._path)
        self._host.fs.chmod(self._path, mode)

        return backup_filename

    def _get_config_option(self, option, section=DEFAULT_CONFIG_SECTION_NAME):
        """
        Get config option

        Args:
            option (str): Option name
            section (str): Section name

        Returns:
            str: Option value
        """
        return self._parser.get(section, option)

    def _get_config_section(self, section=DEFAULT_CONFIG_SECTION_NAME):
        """
        Get config section options

        Args:
            section (str): Section name

        Returns:
            dict: Option names as keys, and option values as values
        """
        return dict(self._parser.items(section))

    def _delete_config_option(
        self, option, section=DEFAULT_CONFIG_SECTION_NAME
    ):
        """
        Delete config option

        Args:
            option (str): Option name
            section (str): Section name

        Returns:
            bool: True if option deleted successfully, False otherwise
        """
        if self._parser.has_section(section):
            self._parser.remove_option(section, option)
            return True

        logger.error("Section: %s does not exists in config file", section)
        return False

    def _delete_config_section(self, section=DEFAULT_CONFIG_SECTION_NAME):
        """
        Delete config section

        Args:
            section (str): Section name

        Returns:
            bool: True if section deleted successfully, False otherwise
        """
        return self._parser.remove_section(section)

    def _set_config_option(
        self, option, value, section=DEFAULT_CONFIG_SECTION_NAME
    ):
        """
        Set config option

        Args:
            option (str): Option name
            value (str): Value
            section (str): Section name

        Returns:
            bool: True if option value set successfully, False otherwise
        """
        if not self._parser.has_section(section):
            logger.error("Section: %s does not exists in config file", section)
            return False

        self._parser.set(section, option, value)
        return True

    def get_options(self, parameters=None):
        """
        Get config options

        Args:
            parameters (dict): Dict with section names as keys,
                and associated options as values in list

        Returns:
            dict: Dict with sections and associated options, or empty dict if
                error has occurred

        Examples:
            Get options from sections:

            parameters_dict = {
                "section_1": ["option_1", "option_2]
                "section_2": "option_1"
            }

            Get all options from two sections:

            parameters_dict = {
                "section_1": list(),
                "section_2": list()
            }

            To get all options from a file without sections (section-less):

            config_file_parser.get_options()
        """
        result = dict()

        if not parameters:
            if self._section_less:
                return self._get_config_section()
            for section in self._parser.sections():
                result[section] = self._get_config_section(section=section)
            return result

        for section, options in parameters.items():
            if not options:
                result[section] = self._get_config_section(section=section)
            else:
                if not isinstance(options, list):
                    options = list(options)
                for option in options:
                    result[section][option] = self._get_config_option(
                        option=option, section=section
                    )

        return result

    def set_options(self, parameters):
        """
        Set config options

        Args:
            parameters (dict): Dict with section names as keys,
                and associated option names and option values as values

        Returns:
            str: Backup filename, or empty string if error occurred

        Examples:
            Create or update exiting options in config file:

            parameters_dict = {
                "section_1": {
                    "option_1": "value",
                    "option_2": "value"
                },
                "section_2": {
                    "option_1": "value"
                }
            }

            Create or update section-less config file:

            from config_handler import DEFAULT_CONFIG_SECTION_NAME
            .
            .
            .
            parameters_dict = {
                DEFAULT_CONFIG_SECTION_NAME: {
                    "option_1": "value",
                    "option_2": "value"
                }
            }
        """
        for section, options in parameters.items():
            for option, value in options.items():
                if not self._set_config_option(
                    option=option, value=value, section=section
                ):
                    return ""

        return self._save_config()

    def delete_options(self, parameters):
        """
        Delete config options

        Args:
            parameters (dict): Dict with section names as keys,
                and associated options as values in list

        Returns:
            str: backup filename, or empty string if error occurred

        Examples:
            Delete two options from section:

            parameters_dict = {
                "section_1": ["option_1", "option_2"]
            }

            Delete section and all of its associated options:

            parameters_dict = {
                "section_1": list()
            }

            Delete options from section-less config file:

            from config_handler import DEFAULT_CONFIG_SECTION_NAME
            .
            .
            .
            parameters_dict = {
                DEFAULT_CONFIG_SECTION_NAME: ["option_1", "option_2"]
            }
        """
        for section, options in parameters.items():
            if not options:
                if not self._delete_config_section(section=section):
                    return ""
            else:
                for option in options:
                    if not self._delete_config_option(
                        option=option, section=section
                    ):
                        return ""

        return self._save_config()
