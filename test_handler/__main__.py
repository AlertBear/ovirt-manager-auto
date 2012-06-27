
from test_handler.plmanagement.manager import PluginManager
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="dkhvc")
    parser.add_argument('--config', action='store', help='config file')
    pl = PluginManager()
    pl.add_options(parser)

    opts = parser.parse_args()


