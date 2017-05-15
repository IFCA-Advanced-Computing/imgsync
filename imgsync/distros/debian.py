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
        self.filename = "debian-%s-openstack-amd64.qcow2" % self.version

    @property
    def what(self):
        return "latest"

    def _sync_latest(self):
        LOG.info("Downloading %s", self.filename)
        base_url = self.url

        # Get the checksum from the index file
        index = requests.get(base_url + self.filename + ".index")
        parser = configparser.SafeConfigParser()
        parser.readfp(six.StringIO(index.text))
        section = parser.sections()[0]
        checksum = parser.get(section, "checksum[sha512]")
        revision = parser.get(section, "revision")

        url = base_url + self.filename
        architecture = "x86_64"
        file_format = "qcow2"

        prefix = CONF.prefix
        name = "%sDebian %s [%s]" % (prefix, self.version, revision)

        image = self.glance.get_image_by_name(name)
        if image:
            if image.sha256 != checksum:
                LOG.error("Glance image chechsum (%s, %s)and official "
                          "checksum %s missmatch.",
                          image.id, image.sha512, checksum)
            else:
                LOG.info("Image already downloaded and synchroniced")
            return

        location = None
        try:
            location = self._download_one(url, ("sha512", checksum))
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


class DebianTesting(Debian):
    url = "https://cdimage.debian.org/cdimage/openstack/testing/"
    debian_release = "testing"
    version = "testing"
