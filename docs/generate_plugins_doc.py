#! /usr/bin/env python
import ast
import os

PATH_TO_ART = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PATH_TO_PLUGINS = os.path.join(
    PATH_TO_ART,
    'art',
    'test_handler',
    'plmanagement',
    'plugins',
)


PLUGINS_HEAD = """
ART Plugins
============
Here is a list of ART plugins and documentation

.. toctree:: :maxdepth: 2

"""


if __name__ == '__main__':
    if not os.path.exists('source/plugins'):
        os.makedirs('source/plugins')

    plugins_path = 'source/plugins.rst'
    plugins = [x for x in sorted(os.listdir(PATH_TO_PLUGINS))
               if x.endswith('_plugin.py')]

    with open(plugins_path, 'w') as plugins_doc:
        plugins_doc.write(PLUGINS_HEAD)
        for plugin in plugins:
            try:
                name = plugin[:-3]
                path = os.path.join(PATH_TO_PLUGINS, plugin)
                with open(path) as fh:
                    plugin_mod = ast.parse(fh.read(), path)
                if not plugin_mod.body:
                    print "Skipping %s, empty module." % name
                    continue
                expr = plugin_mod.body[0]
                if not isinstance(expr, ast.Expr):
                    print "Skipping %s, doc is not first statement." % name
                    continue
                if not isinstance(expr.value, ast.Str):
                    print "Skipping %s, fist statement is not string." % name
                    continue
                doc_str = expr.value.s
                plugin_path = 'source/plugins/%s.rst' % name
                with open(plugin_path, 'w') as plugin_doc:
                    plugin_doc.write(doc_str)
                plugins_doc.write('    plugins/%s\n' % name)
            except Exception as ex:
                print "Doc generation for %s failed: %s" % (name, ex)
