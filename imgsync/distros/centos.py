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
try:
    import lzma
except ImportError:
    from backports import lzma
import os

from oslo_config import cfg
from oslo_log import log
import requests
import six
from six.moves import configparser

from imgsync import distros

LOG = log.getLogger(__name__)

# We are repeating here the options instead of using an interator so that we
# can load them when generating the config file.

c6_opts = [
    cfg.StrOpt('download',
               choices=['all', 'latest'],
               default='latest',
               help='What to sync, "all" will download and sync all images, '
                    '"latest" will donwload and sync only the latest one.')
]

c7_opts = [
    cfg.StrOpt('download',
               choices=['all', 'latest'],
               default='latest',
               help='What to sync, "all" will download and sync all images, '
                    '"latest" will donwload and sync only the latest one.')
]

CONF = cfg.CONF
CONF.register_opts(c6_opts, group="centos6")
CONF.register_opts(c7_opts, group="centos7")


@six.add_metaclass(abc.ABCMeta)
class CentOS(distros.BaseDistro):
    url = None

    def __init__(self):
        super(CentOS, self).__init__()
        self._index = None
        self._get_index()
        self._sections = self._index.sections()
        self._sections.sort()

    def _get_index(self):
        url = self.url + "image-index"
        r = requests.get(url)
        if r.ok:
            aux = r.text
        else:
            return

        parser = configparser.SafeConfigParser()
        parser.readfp(six.StringIO(aux))
        self._index = parser

    def _get_url_from_section(self, section):
        filename = self._index.get(section, "file")
        name = self._index.get(section, "name")
        revision = self._index.get(section, "revision")
        arch = self._index.get(section, "arch")
        file_format = self._index.get(section, "format")
        checksum = self._index.get(section, "checksum")
        return filename, name, revision, arch, file_format, checksum

    def _sync_one(self, section):
        LOG.info("Downloading %s", section)
        (
            filename, name, revision, arch,
            file_format, checksum
        ) = self._get_url_from_section(section)

        prefix = CONF.prefix
        name = "%s%s [%s] " % (prefix, name, revision)

        image = self.glance.get_image_by_name(name)
        if image:
            if image.get("imgsync.sha512") != checksum:
                LOG.error("Glance image chechsum (%s, %s)and official "
                          "checksum %s missmatch.",
                          image.id, image.get("imgsync.sha512"), checksum)
            else:
                LOG.info("Image already downloaded and synchroniced")
            return
        url = self.url + filename

        location = None
        try:
            location = self._download_one(url, ("sha512", checksum))
            fd = lzma.open(location.name, "rb")
            self.glance.upload_with_fd(fd,
                                       name,
                                       architecture=arch,
                                       file_format=file_format,
                                       container_format="bare",
                                       checksum={"sha512": checksum},
                                       os_distro="centos",
                                       os_version=self.version)
        finally:
            if location is not None:
                os.remove(location.name)

    def _sync_all(self):
        for aux in self._sections:
            self._sync_one(aux)

    def _sync_latest(self):
        aux = self._sections[-1]
        self._sync_one(aux)


class CentOS6(CentOS):
    url = "http://cloud.centos.org/centos/6/images/"
    version = 6

    def __init__(self):
        super(CentOS6, self).__init__()

    @property
    def what(self):
        return CONF.centos6.download


class CentOS7(CentOS):
    url = "http://cloud.centos.org/centos/7/images/"
    version = 7

    def __init__(self):
        super(CentOS7, self).__init__()

    @property
    def what(self):
        return CONF.centos7.download
