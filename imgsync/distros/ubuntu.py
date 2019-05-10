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

import dateutil.parser
from oslo_config import cfg
from oslo_log import log
import requests
import six

from imgsync import distros

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Ubuntu(distros.BaseDistro):
    url = None
    ubuntu_release = None
    version = None

    def __init__(self):
        super(Ubuntu, self).__init__()

    @property
    def what(self):
        return "latest"

    @property
    def filename(self):
        return "%s-server-cloudimg-amd64-disk1.img" % self.ubuntu_release

    def _sync_latest(self):
        filename = self.filename
        LOG.info("Downloading %s", filename)
        base_url = self.url + "current/"
        checksum_file = base_url + "SHA256SUMS"
        checksum_file = requests.get(checksum_file)
        if checksum_file.status_code != 200:
            LOG.error("Could not get checksums file %s" % checksum_file.url)
            return

        aux = dict([list(reversed(line.split()))
                    for line in checksum_file.text.splitlines()])

        checksum = aux["*%s" % filename]
        url = base_url + filename
        architecture = "x86_64"
        file_format = "qcow2"

        revision = checksum_file.headers.get("Last-Modified")
        revision = dateutil.parser.parse(revision).strftime("%Y-%m-%d")

        prefix = CONF.prefix
        name = "%sUbuntu %s [%s]" % (prefix, self.version, revision)

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
        finally:
            if location is not None:
                os.remove(location.name)

    def _sync_all(self):
        LOG.warn("Sync all not supported for Ubuntu, syncing "
                 "the latest one.")
        self._sync_latest()


class Ubuntu14(Ubuntu):
    url = "https://cloud-images.ubuntu.com/trusty/"
    ubuntu_release = "trusty"
    version = "14.04"


class Ubuntu16(Ubuntu):
    url = "https://cloud-images.ubuntu.com/xenial/"
    ubuntu_release = "xenial"
    version = "16.04"


class Ubuntu18(Ubuntu):
    url = "https://cloud-images.ubuntu.com/bionic/"
    ubuntu_release = "bionic"
    version = "18.04"
    filename = "%s-server-cloudimg-amd64.img" % ubuntu_release
