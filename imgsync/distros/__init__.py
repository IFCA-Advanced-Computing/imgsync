"""Package to manage distribution download."""

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

import itertools

from oslo_config import cfg
from oslo_log import log

from imgsync.distros import debian
from imgsync.distros import ubuntu


_DISTRO_OBJS = {
    i.name: i
    for i in itertools.chain(
        ubuntu.Ubuntu.__subclasses__(), debian.Debian.__subclasses__()
    )
}

SUPPORTED_DISTROS = list(_DISTRO_OBJS.keys())

opts = [
    cfg.StrOpt(
        "prefix",
        default="",
        help="Name prefix to be used when storing the images " "in glance.",
    ),
    cfg.ListOpt(
        "properties",
        help="Name of the protected properties that we will set "
        "for all images that are synced by us. This is useful "
        "when used together with protected properties so that "
        'your cloud users can check what are the "official" and '
        "trusted images at your site. \n"
        'Properties here are defined in the way "key=value". \n'
        "This option can be specified several times.",
    ),
    # TODO(aloga): add the complete list here using stevedore
    cfg.ListOpt(
        "distributions",
        default=SUPPORTED_DISTROS,
        help="List of distributions to sync (supported values are "
        "%s)." % ", ".join(SUPPORTED_DISTROS),
    ),
]

cli_opts = [
    cfg.BoolOpt(
        "download-only",
        default=False,
        help="Only download the images, do not sync them to glance. Be aware"
        " that images are deleted after being synced to glance, so if you use"
        " this option the images will be deleted after the download. Use this"
        " only for debugging purposes.",
    ),
    cfg.BoolOpt(
        "dry-run",
        default=False,
        help="Do not sync the images, only show what would be done. This still"
        " equires authenticating with Glance, in order to check what would be done.",
    ),
]


CONF = cfg.CONF
CONF.register_opts(opts)
CONF.register_cli_opts(cli_opts)

LOG = log.getLogger(__name__)


class DistroManager(object):
    """Class to manage the distributions."""

    def __init__(self):
        """Initialize the DistroManager object."""
        self.distros = []

        for distro in CONF.distributions:
            if distro not in SUPPORTED_DISTROS:
                raise ValueError("Unsupported distribution %s" % distro)
            self.distros.append(_DISTRO_OBJS[distro]())

    def sync(self):
        """Sync the distributions."""
        if CONF.download_only:
            LOG.warn("Only downloading the images, not checkinf if they need sync.")

        if CONF.dry_run:
            LOG.warn("Dry run, not syncing the images to glance.")

        for distro in self.distros:
            LOG.info("Syncing %s", distro.name)
            distro.sync()
