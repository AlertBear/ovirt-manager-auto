#! /usr/bin/env python
import os
import sys

PATH_TO_ART = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH_TO_PLUGINS = os.path.join(PATH_TO_ART, 'art', 'test_handler', 'plmanagement', 'plugins')

if __name__ == '__main__':
    if not os.path.exists('source/plugins'):
        os.makedirs('source/plugins')
    plugins_doc = open('source/plugins.rst', 'w')
    plugins_doc.write("""
ART Plugins
============
Here is a list of ART plugins and documentation

.. toctree::
    :titlesonly:

""")
    plugins = [ x for x in os.listdir(PATH_TO_PLUGINS) if x.endswith('_plugin.py')]
    sys.path.insert(0, PATH_TO_ART)
    sys.path.insert(0, PATH_TO_PLUGINS)
    for plugin in plugins:
        try:
            name = plugin[:-3]
            plugin_mod = __import__(name)
            if not plugin_mod.__doc__:
                continue
            plugin_doc = open('source/plugins/{0}.rst'.format(name), 'w')
            plugin_doc.write(plugin_mod.__doc__)
            plugins_doc.write('    plugins/{0}\n'.format(name))
        except Exception as e:
            print name
            print "Exception: {0}".format(e)
