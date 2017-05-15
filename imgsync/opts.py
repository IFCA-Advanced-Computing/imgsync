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

import imgsync.distros
import imgsync.distros.centos
import imgsync.glance


def list_opts():
    return [
        ('DEFAULT', imgsync.distros.opts),
        ('centos6', imgsync.distros.centos.c6_opts),
        ('centos7', imgsync.distros.centos.c7_opts),
        ('keystone_auth', imgsync.glance.opts),
    ]
