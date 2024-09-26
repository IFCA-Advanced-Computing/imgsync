"""Module to sync Debian images."""

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

import abc
import datetime

from oslo_config import cfg
from oslo_log import log
import requests

from imgsync.distros import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Debian(base.BaseDistro, metaclass=abc.ABCMeta):
    """Base class for all Debian distributions."""

    debian_release = None
    version = None
    name = "debian"

    def __init__(self):
        """Initialize the Debian object."""
        super(Debian, self).__init__()

    @property
    def what(self):
        """Get what to sync. In debian we can only sync latest."""
        return "latest"

    @property
    def url(self):
        """Get the URL of the Debian cloud images."""
        return "https://cloud.debian.org/images/cloud/%s/latest/" % self.debian_release

    @property
    def filename(self):
        """Get the filename of the image, based on the Debian release."""
        return "debian-%s-genericcloud-amd64.qcow2" % self.version

    def _sync_latest(self):
        """Sync the latest image."""
        base_url = self.url

        checksum_file = base_url + "SHA512SUMS"
        checksum_file = requests.get(checksum_file, timeout=10)
        if checksum_file.status_code != 200:
            LOG.error("Could not get checksums file %s" % checksum_file.url)
            return

        aux = dict(
            [list(reversed(line.split())) for line in checksum_file.text.splitlines()]
        )

        filename = self.filename

        checksum = None
        for k, v in aux.items():
            if k == filename:
                checksum = v
                break
        if not checksum:
            LOG.error("Could not find checksum for %s" % filename)
            return

        LOG.info("Downloading %s", filename)

        url = base_url + filename
        architecture = "x86_64"
        file_format = "qcow2"

        revision = datetime.datetime.now().strftime("%Y%m%d")
        prefix = CONF.prefix
        name = "%sDebian %s [%s]" % (prefix, self.version, revision)
        sha = "sha512"

        if self._needs_download(name, sha, checksum):
            self._sync_with_glance(
                name, url, "debian", sha, checksum, architecture, file_format
            )

    def _sync_all(self):
        """Sync all images."""
        LOG.warn("Sync all not supported for Ubuntu, syncing " "the latest one.")
        self._sync_latest()


class Debian11(Debian):
    """Class to sync Debian 11."""

    debian_release = "bullseye"
    version = "11"
    name = "debian11"


class Debian12(Debian):
    """Class to sync Debian 12."""

    debian_release = "bookworm"
    version = "12"
    name = "debian12"


class DebianTesting(Debian):
    """Class to sync Debian testing."""

    debian_release = "sid"
    version = "testing"
    name = "debian-testing"

    @property
    def url(self):
        """Get the URL of the Debian cloud images."""
        return (
            "https://cloud.debian.org/images/cloud/%s/daily/latest/"
            % self.debian_release
        )

    @property
    def filename(self):
        """Get the filename of the image, based on the Debian release."""
        return "debian-%s-genericcloud-amd64-daily.qcow2" % self.debian_release
