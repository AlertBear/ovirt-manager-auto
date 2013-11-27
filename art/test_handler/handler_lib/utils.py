from functools import wraps
import art.test_handler.settings as settings

DS_PATH = settings.opts.get('data_struct_mod')


class DataStructuresCheat(object):
    """
    Context manager and namespace for methods that will be injected to code

    ***IMPORTANT - if TEMPLATE_HEADER in generateDS.py is changed, this   ***
    ***namespace should be updated according to changes in TEMPLATE_HEADER***

    """
    generateds_super_to_cheat_methods_list = \
        ['gds_format_double', 'gds_format_float', 'gds_format_integer',
         'gds_validate_boolean_list', 'gds_validate_double_list',
         'gds_validate_float_list', 'gds_validate_integer_list']

    cheat_func_prefix = "cheat_"

    def __init__(self):
        # getting module that its code will be modified
        data_structure_module = __import__(DS_PATH)
        # assuming art.<api name>.data_struct.data_structures
        api_name = DS_PATH.split('.')[1]
        # getting code from module that will be modified by code injection
        self._ds = getattr(data_structure_module,
                           api_name).data_struct.data_structures

    def __enter__(self):
        self.inject_cheat_functions()

    def __exit__(self, type_, value, traceback):
        self.return_original_implementation()

    def inject_cheat_functions(self):
        for func in self.generateds_super_to_cheat_methods_list:
            getattr(self._ds.GeneratedsSuper, func).im_func.func_code = \
                getattr(DataStructuresCheat.GeneratedsSuper, '%s%s' %
                        (self.cheat_func_prefix, func)).im_func.func_code
        self._ds._cast.func_code = DataStructuresCheat.cheat_cast.func_code

    def return_original_implementation(self):
        for func in self.generateds_super_to_cheat_methods_list:
            getattr(self._ds.GeneratedsSuper, func).im_func.func_code = \
                getattr(DataStructuresCheat.GeneratedsSuper,
                        func).im_func.func_code
        self._ds._cast.func_code = DataStructuresCheat._cast.func_code

    # cheat function
    @staticmethod
    def cheat_cast(typ, value):
        if typ is None or value is None:
            return value
        try:
            return typ(value)
        except ValueError:
            return value

    # original one
    @staticmethod
    def _cast(typ, value):
        if typ is None or value is None:
            return value
        return typ(value)

    class GeneratedsSuper(object):

        def gds_format_integer(self, input_data, input_name=''):
            return '%d' % input_data

        def cheat_gds_format_integer(self, input_data, input_name=''):
            try:
                return '%d' % input_data
            except TypeError:
                return input_data

        def gds_validate_integer_list(self, input_data, node, input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    raise_parse_error(node, 'Requires sequence of integers')
            return input_data

        def cheat_gds_validate_integer_list(self, input_data, node,
                                            input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    pass
            return input_data

        def gds_format_float(self, input_data, input_name=''):
            return '%f' % input_data

        def cheat_gds_format_float(self, input_data, input_name=''):
            try:
                return '%f' % input_data
            except TypeError:
                return input_data

        def gds_validate_float_list(self, input_data, node, input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    raise_parse_error(node, 'Requires sequence of floats')
            return input_data

        def cheat_gds_validate_float_list(self, input_data, node,
                                          input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    pass
            return input_data

        def gds_format_double(self, input_data, input_name=''):
            return '%e' % input_data

        def cheat_gds_format_double(self, input_data, input_name=''):
            try:
                return '%e' % input_data
            except TypeError:
                return input_data

        def gds_validate_double_list(self, input_data, node, input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    raise_parse_error(node, 'Requires sequence of doubles')
            return input_data

        def cheat_gds_validate_double_list(self, input_data, node,
                                           input_name=''):
            values = input_data.split()
            for value in values:
                try:
                    fvalue = float(value)
                except (TypeError, ValueError), exp:
                    pass
            return input_data

        def gds_validate_boolean_list(self, input_data, node, input_name=''):
            values = input_data.split()
            for value in values:
                if value not in ('true', '1', 'false', '0', ):
                    raise_parse_error(node, 'Requires sequence of booleans ("true", "1", "false", "0")')
            return input_data

        def cheat_gds_validate_boolean_list(self, input_data, node,
                                            input_name=''):
            values = input_data.split()
            for value in values:
                if value not in ('true', '1', 'false', '0', ):
                    pass
            return input_data


def no_datatype_validation(func):
    """
    Description: This closure will be used as decorator for skipping validation
                 of parameters that are passed to data_structures.py variables
    Author: imeerovi
    Parameters:
        *  func - test function
    Returns: returns test_func wrapper for func
    """

    @wraps(func)
    def test_func(*args, **kwargs):
        """
        Description: this code will run when func will be called, at the end it
                     will return original code to data_structures
        Author: imeerovi
        Parameters:
            *  *args, **kwargs - parameters that should be passed to func
        Returns: result of func run
        """

        # cheating :)
        with DataStructuresCheat():
            return func(*args, **kwargs)

    return test_func
