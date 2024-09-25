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
import os

from oslo_config import cfg
from oslo_log import log
import requests
import six

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

        checksum_file = base_url + "SHA512SUMS"
        checksum_file = requests.get(checksum_file, timeout=10)
        if checksum_file.status_code != 200:
            LOG.error("Could not get checksums file %s" % checksum_file.url)
            return

        aux = dict(
            [list(reversed(line.split())) for line in checksum_file.text.splitlines()]
        )

        filename = "debian-%s-genericcloud-amd64.qcow2" % self.version

        for k, v in aux.items():
            if k == filename:
                checksum = v
                break

        LOG.info("Downloading %s", filename)

        url = base_url + filename
        architecture = "x86_64"
        file_format = "qcow2"

        revision = datetime.datetime.now().strftime("%Y%m%d")
        prefix = CONF.prefix
        name = "%sDebian %s [%s]" % (prefix, self.version, revision)

        image = self.glance.get_image_by_name(name)
        if image:
            if image.get("imgsync.sha512") != checksum:
                LOG.error(
                    "Glance image chechsum (%s, %s)and official "
                    "checksum %s missmatch.",
                    image.id,
                    image.get("imgsync.sha512"),
                    checksum,
                )
            else:
                LOG.info("Image already downloaded and synchroniced")
            return

        location = None
        try:
            location = self._download_one(url, ("sha512", checksum))
            self.glance.upload(
                location,
                name,
                architecture=architecture,
                file_format=file_format,
                container_format="bare",
                checksum={"sha512": checksum},
                os_distro="ubuntu",
                os_version=self.version,
            )
            LOG.info("Synchronized %s", name)
        finally:
            if location is not None:
                os.remove(location.name)

    def _sync_all(self):
        LOG.warn("Sync all not supported for Ubuntu, syncing " "the latest one.")
        self._sync_latest()


class Debian10(Debian):
    debian_release = "buster"
    version = "10"
    url = "https://repo.ifca.es/debian-cdimage-cloud/%s/latest/" % debian_release


class Debian11(Debian):
    debian_release = "bullseye"
    version = "11"
    url = "https://repo.ifca.es/debian-cdimage-cloud/%s/latest/" % debian_release


class Debian12(Debian):
    debian_release = "bookworm"
    version = "12"
    url = "https://repo.ifca.es/debian-cdimage-cloud/%s/latest/" % debian_release
