"""Base classes and options for the distros."""

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
import hashlib
import os
import tempfile

from oslo_config import cfg
from oslo_log import log
import requests
import six
import stevedore

from imgsync import exception
from imgsync import glance

SUPPORTED_DISTROS = [
    "centos6",
    "centos7",
    "ubuntu14",
    "ubuntu16",
    "ubuntu18",
    "ubuntu20",
    "ubuntu22",
    "debian10",
    "debian11",
    "debian12",
]

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

CONF = cfg.CONF
CONF.register_opts(opts)

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseDistro(object):
    """Base class for all distributions."""

    url = None

    def __init__(self):
        """Initialize the BaseDistro object."""
        self.glance = glance.GLANCE

    @abc.abstractproperty
    def what(self):
        """Get what to sync. This has to be implemented by the child class."""
        return None

    def sync(self):
        """Sync the images, calling the method that is needed."""
        if self.what == "all":
            self._sync_all()
        elif self.what == "latest":
            self._sync_latest()
        else:
            LOG.warn("Nothing to do")

    def _get_file_checksum(self, path, block_size=2**20):
        """Get the checksum of a file.

        Get the checksum of a file using sha512.

        :param path: the path to the file
        :param block_size: block size to use when reading the file
        :returns: sha512 object
        """
        sha512 = hashlib.sha512()
        with open(path, "rb") as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                sha512.update(buf)
                buf = f.read(block_size)
        return sha512

    def verify_checksum(
        self,
        location,
        name,
        checksum,
    ):
        """Verify the image's checksum."""
        # TODO(aloga): not implemented yet

    def _download_one(self, url, checksum):
        """Download a file.

        Download a file from a url and return a temporary file object.

        :param url: the url to download
        :param checksum: tuple in the form (checksum_name, checksum_value)
        :returns: temporary file object
        """
        with tempfile.NamedTemporaryFile(suffix=".imgsync", delete=False) as location:
            try:
                response = requests.get(url, stream=True, timeout=10)
            except Exception as e:
                os.remove(location.name)
                LOG.error(e)
                raise exception.ImageDownloadFailed(code=e.errno, reason=e.message)

            if not response.ok:
                os.remove(location.name)
                LOG.error(
                    "Cannot download image: (%s) %s",
                    response.status_code,
                    response.reason,
                )
                raise exception.ImageDownloadFailed(
                    code=response.status_code, reason=response.reason
                )

            for block in response.iter_content(1024):
                if block:
                    location.write(block)
                    location.flush()

        checksum_map = {"sha512": hashlib.sha512, "sha256": hashlib.sha256}
        sha = checksum_map.get(checksum[0])()
        block_size = 2**20
        with open(location.name, "rb") as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                sha.update(buf)
                buf = f.read(block_size)

        if sha.hexdigest() != checksum[1]:
            os.remove(location.name)
            e = exception.ImageVerificationFailed(
                url=url, expected=checksum, obtained=sha.hexdigest()
            )
            LOG.error(e)
            raise e

        LOG.info("Image '%s' downloaded", url)
        return location


class DistroManager(object):
    """Class to manage the distributions."""

    def __init__(self):
        """Initialize the DistroManager object."""
        self.distros = stevedore.NamedExtensionManager(
            "imgsync.distros",
            CONF.distributions,
            invoke_on_load=True,
            propagate_map_exceptions=True,
        )

    def sync(self):
        """Sync the distributions."""
        LOG.info("Syncing %s", self.distros.names())
        self.distros.map_method("sync")
