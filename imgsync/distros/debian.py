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
import os

from oslo_config import cfg
from oslo_log import log
import requests
import six
from six.moves import configparser

from imgsync import distros

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Debian(distros.BaseDistro):
    url = None

    def __init__(self):
        super(Debian, self).__init__()
        self.filename = None

    @property
    def what(self):
        return "latest"

    def _sync_latest(self):
        base_url = self.url

        checksum_file = base_url + "SHA256SUMS"
        checksum_file = requests.get(checksum_file)
        if checksum_file.status_code != 200:
            LOG.error("Could not get checksums file %s" % checksum_file.url)
            return

        aux = dict([list(reversed(line.split()))
                    for line in checksum_file.text.splitlines()])

        filename = None
        for k, v in aux.items():
            if k.endswith(".qcow2"):
                filename = k
                checksum = v
                break

        if filename is None:
            LOG.error("Could not get image file")
            return

        LOG.info("Downloading %s", filename)

        # Get the revision from the index file
        index = requests.get(base_url + filename + ".index")
        if not index.ok:
            LOG.error("Cannot download image from server, got %s", index.status_code)
            return
        parser = configparser.SafeConfigParser()
        parser.readfp(six.StringIO(index.text))
        section = parser.sections()[0]
        revision = parser.get(section, "revision")

        url = base_url + filename
        architecture = "x86_64"
        file_format = "qcow2"

        prefix = CONF.prefix
        name = "%sDebian %s [%s]" % (prefix, self.version, revision)

        image = self.glance.get_image_by_name(name)
        if image:
            if image.get("imgsync.sha256") != checksum:
                LOG.error("Glance image chechsum (%s, %s)and official "
                          "checksum %s missmatch.",
                          image.id, image.get("imgsync.sha256"), checksum)
            else:
                LOG.info("Image already downloaded and synchroniced")
            return

        location = None
        try:
            location = self._download_one(url, ("sha256", checksum))
            self.glance.upload(location,
                               name,
                               architecture=architecture,
                               file_format=file_format,
                               container_format="bare",
                               checksum={"sha256": checksum},
                               os_distro="ubuntu",
                               os_version=self.version)
            LOG.info("Synchronized %s", name)
        finally:
            if location is not None:
                os.remove(location.name)

    def _sync_all(self):
        LOG.warn("Sync all not supported for Ubuntu, syncing "
                 "the latest one.")
        self._sync_latest()


class Debian8(Debian):
    url = "https://cdimage.debian.org/cdimage/openstack/current-8/"
    debian_release = "jessie"
    version = "8"


class Debian9(Debian):
    url = "https://cdimage.debian.org/cdimage/openstack/current-9/"
    debian_release = "stretch"
    version = "9"


class DebianTesting(Debian):
    url = "https://cdimage.debian.org/cdimage/openstack/testing/"
    debian_release = "testing"
    version = "testing"
