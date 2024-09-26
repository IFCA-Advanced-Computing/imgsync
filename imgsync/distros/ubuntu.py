"""Ubuntu distros for imgsync."""

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

import dateutil.parser
from oslo_config import cfg
from oslo_log import log
import requests

from imgsync.distros import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class Ubuntu(base.BaseDistro, metaclass=abc.ABCMeta):
    """Base class for all Ubuntu distributions."""

    ubuntu_release = None
    version = None
    name = "ubuntu"

    def __init__(self):
        """Initialize the Ubuntu object."""
        super(Ubuntu, self).__init__()

    @property
    def what(self):
        """Get what to sync. In Ubuntu we can only sync latest."""
        return "latest"

    @property
    def filename(self):
        """Get the filename of the image, based on the Ubuntu release."""
        return "%s-server-cloudimg-amd64.img" % self.ubuntu_release

    @property
    def url(self):
        """Get the URL of the Ubuntu cloud images."""
        return "https://repo.ifca.es/ubuntu-cloud-images/%s/" % self.ubuntu_release

    def _sync_latest(self):
        """Sync the latest image."""
        filename = self.filename
        LOG.info("Downloading %s", filename)
        base_url = self.url + "current/"
        checksum_file = base_url + "SHA256SUMS"
        checksum_file = requests.get(checksum_file, timeout=10)
        if checksum_file.status_code != 200:
            LOG.error("Could not get checksums file %s" % checksum_file.url)
            return

        aux = dict(
            [list(reversed(line.split())) for line in checksum_file.text.splitlines()]
        )

        checksum = aux["*%s" % filename]
        url = base_url + filename
        architecture = "x86_64"
        file_format = "qcow2"

        revision = checksum_file.headers.get("Last-Modified")
        revision = dateutil.parser.parse(revision).strftime("%Y-%m-%d")

        prefix = CONF.prefix
        name = "%sUbuntu %s [%s]" % (prefix, self.version, revision)
        sha = "sha256"

        if self._needs_download(name, sha, checksum):
            self._sync_with_glance(
                name, url, "ubuntu", sha, checksum, architecture, file_format
            )

    def _sync_all(self):
        """Sync all images."""
        LOG.warn("Sync all not supported for Ubuntu, syncing " "the latest one.")
        self._sync_latest()


class Ubuntu18(Ubuntu):
    """Class to sync Ubuntu 18.04."""

    ubuntu_release = "bionic"
    version = "18.04"
    name = "ubuntu18"


class Ubuntu20(Ubuntu):
    """Class to sync Ubuntu 20.04."""

    ubuntu_release = "focal"
    version = "20.04"
    name = "ubuntu20"


class Ubuntu22(Ubuntu):
    """Class to sync Ubuntu 22.04."""

    ubuntu_release = "jammy"
    version = "22.04"
    name = "ubuntu22"


class Ubuntu24(Ubuntu):
    """Class to sync Ubuntu 24.04."""

    ubuntu_release = "noble"
    version = "24.04"
    name = "ubuntu24"
