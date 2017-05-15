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

import glanceclient
from keystoneauth1 import loading
from oslo_config import cfg
from oslo_log import log

CONF = cfg.CONF

cfg_group = "keystone_auth"

loading.register_auth_conf_options(CONF, cfg_group)
loading.register_session_conf_options(CONF, cfg_group)

opts = (loading.get_auth_common_conf_options() +
        loading.get_session_conf_options() +
        loading.get_auth_plugin_conf_options('password'))

LOG = log.getLogger(__name__)


class GlanceClient(object):
    def __init__(self):
        self._images = None
        self._client = None

    @property
    def client(self):
        # Defer the client creation to when it is needed.
        if self._client is None:
            self._client = self._get_session()
        return self._client

    def _get_session(self):
        """Get an auth session."""
        auth_plugin = loading.load_auth_from_conf_options(CONF, cfg_group)
        sess = loading.load_session_from_conf_options(CONF, cfg_group,
                                                      auth=auth_plugin)

        return glanceclient.Client('2', session=sess)

    @property
    def images(self):
        if self._images is None:
            images = self.client.images.list(filters={"source": "imgsync"})
            images = {image.name: image for image in images}
            self._images = images
        return self._images

    def get_image_by_name(self, name):
        return self.images.get(name)

    def upload(self, location, name, architecture, file_format,
               container_format, checksum, os_distro, os_version,
               os_type="Linux"):

        self.upload_with_fd(open(location.name, 'rb'), name, architecture,
                            file_format, container_format, checksum, os_distro,
                            os_version, os_type=os_type)

    def upload_with_fd(self, fd, name, architecture, file_format,
                       container_format, checksum, os_distro, os_version,
                       os_type="Linux"):

        os_version = str(os_version)

        try:
            properties = dict([i.split("=") for i in CONF.properties])
        except ValueError:
            raise
            LOG.error("Wrong 'properties' option defined in config file")

        checksum = {"imgsync.%s" % k: v for k, v in checksum.items()}
        properties.update(checksum)
        properties["source"] = "imgsync"

        image = self.client.images.create(
            name=name, architecture=architecture,
            disk_format=file_format,
            container_format=container_format,
            visibility="public",
            os_distro=os_distro, distribution=os_distro,
            os_version=os_version, version=os_version,
            os_type=os_type, type=os_type,
            **properties)

        try:
            self.client.images.upload(image.id, fd)
        except Exception as e:
            LOG.error("Cannot upload image, an error has happened")
            LOG.exception(e)
            self.client.images.delete(image.id)


GLANCE = GlanceClient()
