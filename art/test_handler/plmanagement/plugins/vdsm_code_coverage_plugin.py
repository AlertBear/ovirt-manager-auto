"""
-------------------------
Vdsm Code Coverage Plugin
-------------------------

Plugin enables vdsm_code_coverage functionality on hosts and fetch results.

CLI Options:
------------
    --with-vdsm-code-coverage   Enable plugin

Configuration Options:
----------------------
    | **[VDSM_CODE_COVERAGE]**
    | **enabled** - to enable the plugin (true/false)
    | **service** - name of vdsmcodecoverage service
    | **path_to_source** - path to coverage file on remote host
    | **path_to_target** - path to final coverage file
"""
import os
import shutil
from art.test_handler.plmanagement import Component, implements, get_logger,\
    PluginError
from art.test_handler.plmanagement.interfaces.application import \
    IConfigurable, IApplicationListener
from art.test_handler.plmanagement.interfaces.packaging import IPackaging
from art.test_handler.plmanagement.interfaces.config_validator import\
    IConfigValidation
from utilities.machine import Machine, LINUX
import tempfile


logger = get_logger("vdsm_code_coverage")

PARAMETERS = 'PARAMETERS'
COVERAGE_SECTION = 'VDSM_CODE_COVERAGE'
VDS_PASSWORD = 'vds_password'
VDS = 'vds'
COVERAGE_SOURCE = 'path_to_source'
COVERAGE_TARGET = 'path_to_target'
ENABLED = 'enabled'
SERVICE = 'service'

TARGET_DEFAULT = "results/vdsm_coverage"
SOURCE_DEFAULT = "/var/lib/vdsmcodecoverage/coverage"
SERVICE_DEFAULT = "vdsmcodecoveraged"


class VDSMCoverageError(PluginError):
    pass


class VDSMCodeCoverage(Component):
    """
    Plugin enables code coverage for vdsm service on hosts and fetch results.
    """
    implements(IConfigurable, IApplicationListener, IPackaging,
               IConfigValidation)
    name = 'VDSM code coverage'

    def __init__(self):
        super(VDSMCodeCoverage, self).__init__()
        self.machines = {}
        self.res_dir = None
        self.target_path = None
        self.source_path = None
        self.service = None

    @classmethod
    def add_options(cls, parser):
        group = parser.add_argument_group(cls.name, description=cls.__doc__)
        group.add_argument('--with-vdsm-code-coverage', action="store_true",
                           dest='vdsm_code_coverage')

    def _start(self):
        for mobj in self.machines.values():
            self._toogle(mobj, False)
            self._clean(mobj)
            self._toogle(mobj, True)

    def _stop(self):
        for mobj in self.machines.values():
            self._toogle(mobj, False)
        for mobj in self.machines.values():
            self._copy(mobj)
        if self.machines:
            self._merge()

    def _toogle(self, machine, op):
        if op:
            logger.info("Start VDSM code coverage on %s", machine.host)
        else:
            logger.info("Stop VDSM code coverage on %s", machine.host)
        chkconfig = ["chkconfig", self.service]
        service = ["service", self.service]

        if op:
            chkconfig.append('on')
            service.append('start')
        else:
            chkconfig.append('off')
            service.append('stop')

        machine.runCmd(service)
        machine.runCmd(chkconfig)

    def _clean(self, machine):
        logger.info("Cleaning old coverage reports: %s", self.source_path)
        machine.removeFile(self.source_path)

    def _copy(self, machine):
        name = ".coverage.%s" % machine.host
        target_path = os.path.join(self.res_dir, name)
        res = machine.copyFrom(self.source_path, target_path, exc_info=False)
        if res:
            logger.info("VDSM code coverage copied to: %s", target_path)

    def _merge(self):
        mobj = Machine().util(LINUX)
        cmd = ['coverage', 'combine']
        res, out = mobj.runCmd(cmd, runDir=self.res_dir)
        if not res:
            logger.error("Merge of code coverage failed: %s", out)
        path = os.path.join(self.res_dir, '.coverage')
        if os.path.exists(path):
            with open(path, 'rb') as fs:
                with open(self.target_path, 'wb') as ft:
                    ft.write(fs.read())
            logger.info("VDSM code coverage file was merged to %s",
                        self.target_path)
        else:
            logger.warning("There is no code coverage found")

    def configure(self, params, conf):
        if not self.is_enabled(params, conf):
            return

        config = conf[COVERAGE_SECTION]

        self.res_dir = tempfile.mkdtemp()
        self.target_path = config[COVERAGE_TARGET]
        self.source_path = config[COVERAGE_SOURCE]
        self.service = config[SERVICE]

        vds = conf[PARAMETERS].as_list(VDS)
        vds_passwd = conf[PARAMETERS].as_list(VDS_PASSWORD)

        for name, passwd in zip(vds, vds_passwd):
            self.machines[name] = Machine(name, 'root', passwd).util(LINUX)

        target_dir = os.path.dirname(self.target_path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir)

    def on_application_exit(self):
        try:
            self._stop()
        finally:
            if self.res_dir and os.path.exists(self.res_dir):
                shutil.rmtree(self.res_dir, ignore_errors=True)

    def on_application_start(self):
        self._start()

    def on_plugins_loaded(self):
        pass

    @classmethod
    def is_enabled(cls, params, conf):
        conf_en = conf.get(COVERAGE_SECTION).as_bool(ENABLED)
        return params.vdsm_code_coverage or conf_en

    @classmethod
    def fill_setup_params(cls, params):
        params['name'] = cls.name.lower().replace(' ', '-')
        params['version'] = '1.0'
        params['author'] = 'Lukas Bednar'
        params['author_email'] = 'lbednar@redhat.com'
        params['description'] = 'VDSM code coverage for ART'
        params['long_description'] = cls.__doc__.strip().replace('\n', ' ')
        params['requires'] = ['art-utilities', 'python-coverage >= 3.5.3']
        params['py_modules'] = ['art.test_handler.plmanagement.plugins.'
                                'vdsm_code_coverage_plugin']

    def config_spec(self, spec, val_funcs):
        section_spec = spec.setdefault(COVERAGE_SECTION, {})
        section_spec[ENABLED] = 'boolean(default=False)'
        section_spec[COVERAGE_TARGET] = 'string(default="%s")' % TARGET_DEFAULT
        section_spec[COVERAGE_SOURCE] = 'string(default="%s")' % SOURCE_DEFAULT
        section_spec[SERVICE] = 'string(default="%s")' % SERVICE_DEFAULT
