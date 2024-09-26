"""Base class for all distributions."""

import abc
import hashlib
import os
import tempfile

from oslo_config import cfg
from oslo_log import log
import requests

from imgsync import exception
from imgsync import glance

CONF = cfg.CONF

LOG = log.getLogger(__name__)


class BaseDistro(object, metaclass=abc.ABCMeta):
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

        self.verify_checksum(location, url, checksum, url)

    def verify_checksum(self, location, name, checksum, url):
        """Verify the image's checksum."""
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

    def _needs_download(self, name, checksum_type, checksum):
        """Check if the image needs to be downloaded."""
        if CONF.download_only:
            return True

        image = self.glance.get_image_by_name(name)
        if image:
            if image.get("imgsync.%s" % checksum_type) == checksum:
                LOG.info("Image already downloaded and synchroniced")
                return False
            else:
                LOG.error(
                    "Glance image chechsum (%s, %s) and official "
                    "checksum %s missmatch.",
                    image.id,
                    image.get("imgsync.%s" % checksum_type),
                    checksum,
                )
        return True

    def _sync_with_glance(
        self, name, url, distro, checksum_type, checksum, architecture, file_format
    ):
        """Upload the image to glance."""
        location = None
        try:
            location = self._download_one(url, (checksum_type, checksum))
            if not (CONF.download_only or CONF.dry_run):
                self.glance.upload(
                    location,
                    name,
                    architecture=architecture,
                    file_format=file_format,
                    container_format="bare",
                    checksum={checksum_type: checksum},
                    os_distro=distro,
                    os_version=self.version,
                )
                LOG.info("Synchronized %s", name)
            else:
                LOG.info("Downloaded %s", name)
        finally:
            if location is not None:
                LOG.debug("Removing %s", location.name)
                os.remove(location.name)
