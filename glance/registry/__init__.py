# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010-2011 OpenStack, LLC
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Registry API
"""

import os

from oslo.config import cfg

from glance.common import exception
import glance.openstack.common.log as logging
from glance.registry import client

LOG = logging.getLogger(__name__)

registry_addr_opts = [
    cfg.StrOpt('registry_host', default='0.0.0.0',
               help=_('Address to find the registry server.')),
    cfg.IntOpt('registry_port', default=9191,
               help=_('Port the registry server is listening on.')),
]
registry_client_opts = [
    cfg.StrOpt('registry_client_protocol', default='http',
               help=_('The protocol to use for communication with the '
                      'registry server.  Either http or https.')),
    cfg.StrOpt('registry_client_key_file',
               help=_('The path to the key file to use in SSL connections '
                      'to the registry server.')),
    cfg.StrOpt('registry_client_cert_file',
               help=_('The path to the cert file to use in SSL connections '
                      'to the registry server.')),
    cfg.StrOpt('registry_client_ca_file',
               help=_('The path to the certifying authority cert file to '
                      'use in SSL connections to the registry server.')),
    cfg.BoolOpt('registry_client_insecure', default=False,
                help=_('When using SSL in connections to the registry server, '
                       'do not require validation via a certifying '
                       'authority.')),
    cfg.IntOpt('registry_client_timeout', default=600,
               help=_('The period of time, in seconds, that the API server '
                      'will wait for a registry request to complete. A '
                      'value of 0 implies no timeout.')),
]
registry_client_ctx_opts = [
    cfg.StrOpt('admin_user', secret=True,
               help=_('The administrators user name.')),
    cfg.StrOpt('admin_password', secret=True,
               help=_('The administrators password.')),
    cfg.StrOpt('admin_tenant_name', secret=True,
               help=_('The tenant name of the adminstrative user.')),
    cfg.StrOpt('auth_url',
               help=_('The URL to the keystone service.')),
    cfg.StrOpt('auth_strategy', default='noauth',
               help=_('The strategy to use for authentication.')),
    cfg.StrOpt('auth_region',
               help=_('The region for the authentication service.')),
]

CONF = cfg.CONF
CONF.register_opts(registry_addr_opts)
CONF.register_opts(registry_client_opts)
CONF.register_opts(registry_client_ctx_opts)
CONF.import_opt('metadata_encryption_key', 'glance.common.config')

_CLIENT_CREDS = None
_CLIENT_HOST = None
_CLIENT_PORT = None
_CLIENT_KWARGS = {}
# AES key used to encrypt 'location' metadata
_METADATA_ENCRYPTION_KEY = None


def configure_registry_client():
    """
    Sets up a registry client for use in registry lookups
    """
    global _CLIENT_KWARGS, _CLIENT_HOST, _CLIENT_PORT, _METADATA_ENCRYPTION_KEY
    try:
        host, port = CONF.registry_host, CONF.registry_port
    except cfg.ConfigFileValueError:
        msg = _("Configuration option was not valid")
        LOG.error(msg)
        raise exception.BadRegistryConnectionConfiguration(msg)
    except IndexError:
        msg = _("Could not find required configuration option")
        LOG.error(msg)
        raise exception.BadRegistryConnectionConfiguration(msg)

    _CLIENT_HOST = host
    _CLIENT_PORT = port
    _METADATA_ENCRYPTION_KEY = CONF.metadata_encryption_key
    _CLIENT_KWARGS = {
        'use_ssl': CONF.registry_client_protocol.lower() == 'https',
        'key_file': CONF.registry_client_key_file,
        'cert_file': CONF.registry_client_cert_file,
        'ca_file': CONF.registry_client_ca_file,
        'insecure': CONF.registry_client_insecure,
        'timeout': CONF.registry_client_timeout,
    }


def configure_registry_admin_creds():
    global _CLIENT_CREDS

    if CONF.auth_url or os.getenv('OS_AUTH_URL'):
        strategy = 'keystone'
    else:
        strategy = CONF.auth_strategy

    _CLIENT_CREDS = {
        'user': CONF.admin_user,
        'password': CONF.admin_password,
        'username': CONF.admin_user,
        'tenant': CONF.admin_tenant_name,
        'auth_url': CONF.auth_url,
        'strategy': strategy,
        'region': CONF.auth_region,
    }


def get_registry_client(cxt):
    global _CLIENT_CREDS, _CLIENT_KWARGS, _CLIENT_HOST, _CLIENT_PORT
    global _METADATA_ENCRYPTION_KEY
    kwargs = _CLIENT_KWARGS.copy()
    kwargs['auth_tok'] = cxt.auth_tok
    if _CLIENT_CREDS:
        kwargs['creds'] = _CLIENT_CREDS
    return client.RegistryClient(_CLIENT_HOST, _CLIENT_PORT,
                                 _METADATA_ENCRYPTION_KEY, **kwargs)


def get_images_list(context, **kwargs):
    c = get_registry_client(context)
    return c.get_images(**kwargs)


def get_images_detail(context, **kwargs):
    c = get_registry_client(context)
    return c.get_images_detailed(**kwargs)


def get_image_metadata(context, image_id):
    c = get_registry_client(context)
    return c.get_image(image_id)


def add_image_metadata(context, image_meta):
    LOG.debug(_("Adding image metadata..."))
    c = get_registry_client(context)
    return c.add_image(image_meta)


def update_image_metadata(context, image_id, image_meta,
                          purge_props=False):
    LOG.debug(_("Updating image metadata for image %s..."), image_id)
    c = get_registry_client(context)
    return c.update_image(image_id, image_meta, purge_props)


def delete_image_metadata(context, image_id):
    LOG.debug(_("Deleting image metadata for image %s..."), image_id)
    c = get_registry_client(context)
    return c.delete_image(image_id)


def get_image_members(context, image_id):
    c = get_registry_client(context)
    return c.get_image_members(image_id)


def get_member_images(context, member_id):
    c = get_registry_client(context)
    return c.get_member_images(member_id)


def replace_members(context, image_id, member_data):
    c = get_registry_client(context)
    return c.replace_members(image_id, member_data)


def add_member(context, image_id, member_id, can_share=None):
    c = get_registry_client(context)
    return c.add_member(image_id, member_id, can_share=can_share)


def delete_member(context, image_id, member_id):
    c = get_registry_client(context)
    return c.delete_member(image_id, member_id)
