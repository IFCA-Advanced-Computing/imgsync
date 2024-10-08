"""Handle imgsync commands."""

# Copyright (c) 2016 Alvaro Lopez Garcia

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import print_function

import sys

from oslo_config import cfg

from imgsync import distros
from imgsync import exception

CONF = cfg.CONF


def add_command_parsers(subparsers):
    """Add command parsers to the global parser."""
    SyncCommand(subparsers)


command_opt = cfg.SubCommandOpt(
    "command",
    title="Commands",
    help="Show available commands.",
    handler=add_command_parsers,
)

CONF.register_cli_opt(command_opt)


class Command(object):
    """Base class for imgsync commands."""

    def __init__(self, parser, name, cmd_help):
        """Initialize the command."""
        self.name = name
        self.cmd_help = cmd_help
        self.parser = parser.add_parser(name, help=cmd_help)
        self.parser.set_defaults(func=self.run)

    def run(self):
        """Run the command. This has to be implemented by the subclass."""
        raise NotImplementedError("Method must me overriden on subclass")


class SyncCommand(Command):
    """Sync command."""

    def __init__(self, parser, name="sync", cmd_help="Syncrhonize configured images"):
        """Initialize the sync command."""
        super(SyncCommand, self).__init__(parser, name, cmd_help)
        self.manager = distros.DistroManager()

    def run(self):
        """Run the sync command."""
        self.manager.sync()


class CommandManager(object):
    """Command manager."""

    def execute(self):
        """Execute the command."""
        try:
            CONF.command.func()
        except exception.ImgSyncException as e:
            print("ERROR: %s" % e, file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nExiting...", file=sys.stderr)
            sys.exit(0)
