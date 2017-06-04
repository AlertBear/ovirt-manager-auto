import os
import logging
from art.generateDS.setup_ds import GenerateDataStructures
import art
from art.test_handler.settings import ART_CONFIG

DATA_STRUCT_PATH = os.path.join('data_struct', 'data_structures.py')


logger = logging.getLogger('rhevm_api')


class GenerateRhevmDataStructures(GenerateDataStructures):

    def __init__(self, conf):
        super(GenerateRhevmDataStructures, self).__init__(
            ART_CONFIG, repo_path=os.path.dirname(art.__file__),
        )

    def _set_xsd_path(self):
        xsd_path = os.path.join(
            os.path.dirname(__file__), 'data_struct', 'api.xsd',
        )
        self._ds_path = os.path.join(
            os.path.dirname(__file__), DATA_STRUCT_PATH,
        )
        self._xsd_path = xsd_path
        ART_CONFIG['api_xsd'] = xsd_path


generate_ds = GenerateRhevmDataStructures(ART_CONFIG)
