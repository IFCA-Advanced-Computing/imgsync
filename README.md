# OpenStack Glance Image Synchronization tool

This application will download images from the official distribution
repository, and upload them to OpenStack Glance. It is possible to define
custom properties and prefixes for all the synced images.

## Available distribution repositories

Currently the following images repositories are supported:

### Debian

- Debian 11: https://cloud.debian.org/images/cloud/bullseye/
- Debian 12: https://cloud.debian.org/images/cloud/bookworm/
- Debian testing: https://cloud.debian.org/images/cloud/sid/

### Ubuntu

- Ubuntu 18.04: https://cloud-images.ubuntu.com/bionic/
- Ubuntu 20.04: https://cloud-images.ubuntu.com/focal/
- Ubuntu 22.04: https://cloud-images.ubuntu.com/jammy/
- Ubuntu 24.04: https://cloud-images.ubuntu.com/noble

## Installation

Install it via PyPI:

    pip install imgsync

Or install it from the repo:

    git clone https://github.com/alvarolopez/imgsync
    pip install imgsync

## Configuration

Copy `/etc/imgsync/imgsync.conf.sample` into `/etc/imgsync/imgsync.conf` and
adjust it your your needs. Take into account the following:

- You need to configure your OpenStack Keystone authentication under the
  `[keystone_auth]` section. The user should be able to publicize images in
  your glance deployment (check your policy file).

- You can define a prefix to be used for all the distribution names with the
  `prefix` option.

- Additionally you can add some custom image properties, using the `properties`
  option, that can be repeated multiple times for multiple properties.

- The list of images to be downloaded is configured via the `distributions`
  option.

### Image properties

`imgsync` sets a property `source=imgsync` to all the images that donwloaded
and synced. This way we can identify if an image is uploaded into glance by us
or by anyone else. This property is hardcoded and cannot be reconfigured or
replaced by something else. Other properties set by `imgsync` are are stored with the
`imgsync.prefix` (like `imgsync.sha256` or `imgsync.sha512`)

Nevertheless, it is also possible to define additional properties in the form
"key=value" via the `properties` option in the configuration file (you can
specify this option several times).

Therefore, it is important that you configure glance to enable the proper
[policy protection rules](https://docs.openstack.org/developer/glance/property-protections.html)
so that only the configured user is able to write those properties (i.e. at
least `source`, `imgsync.sha512` and `imgsync.sha256`). Moreover, you need to
configure nova to exclude those properties when nova creates and uploads an
snapshot to glance, via the `non_inheritable_image_properties` option in your
`/etc/nova/nova.conf` configuration file (again, at least add `source`,
`imgsync.sha512` and `imgsync.sha256`).
