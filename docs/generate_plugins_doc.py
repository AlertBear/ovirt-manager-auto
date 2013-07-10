#! /usr/bin/env python
import os
import sys

PATH_TO_ART = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH_TO_PLUGINS = os.path.join(PATH_TO_ART, 'art', 'test_handler', 'plmanagement', 'plugins')


PLUGINS_HEAD = """
ART Plugins
============
Here is a list of ART plugins and documentation

.. toctree:: :maxdepth: 2

"""


if __name__ == '__main__':
    if not os.path.exists('source/plugins'):
        os.makedirs('source/plugins')

    sys.path.insert(0, PATH_TO_ART)
    sys.path.insert(0, PATH_TO_PLUGINS)

    plugins_path = 'source/plugins.rst'
    plugins = [x for x in sorted(os.listdir(PATH_TO_PLUGINS))
               if x.endswith('_plugin.py')]

    with open(plugins_path, 'w') as plugins_doc:
        plugins_doc.write(PLUGINS_HEAD)
        for plugin in plugins:
            try:
                name = plugin[:-3]
                plugin_mod = __import__(name)
                if not plugin_mod.__doc__:
                    continue
                plugin_path = 'source/plugins/%s.rst' % name
                with open(plugin_path, 'w') as plugin_doc:
                    plugin_doc.write(plugin_mod.__doc__)
                plugins_doc.write('    plugins/%s\n' % name)
            except Exception as ex:
                print "Doc generation for %s failed: %s" % (name, ex)
