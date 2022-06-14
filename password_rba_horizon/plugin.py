# Copyright 2022 Vincent Unsel
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import BadHeaderError
from django.utils.translation import gettext_lazy as _

from keystoneauth1 import exceptions as keystone_exceptions
from keystoneauth1.extras import rba as v3_rba
from keystoneauth1.identity import v3

from openstack_auth.plugin import base
from openstack_auth import exceptions
from openstack_auth import utils

from password_rba_horizon import exceptions as exception

from oslo_serialization import jsonutils

LOG = logging.getLogger(__name__)

__all__ = ['RBAPasswordPlugin']


class RBAPasswordPlugin(base.BasePlugin):
    """Authenticate against keystone with risk-based authentication
    alongside given a username and password.

    Risk-based authentication utilizes collected information during the login
    attempt as features. In the case of suspicious features, a passcode can
    be transmitted to the user as an additional factor and queried to confirm
    and record the new information features for future attempts.

    The features dict may contain the key and value mapping for information
    such as the IP-Address, the User-Agent and the Round-Trip-Time.
    Example {"ip": "10.0.0.1", "ua": "", rtt": "420"}
    The passcode is a string type value.

    get_plugin returns a v3 keystone plugin for authentication.

    """
    def send_passcode_email(self, email_receipient_address, passcode):
        if passcode and email_receipient_address:
            try:
                subject = 'Your personal security code'
                content = """Dear user,\nsomeone just tried to sign in to your account.\nIf you were prompted for a security code, please enter the following to complete your sign-in: """ + passcode + """\nIf you were not prompted, please change your password immediately in the profile settings.""" 
                LOG.debug(subject)
                LOG.debug(content)
                LOG.debug(settings.EMAIL_HOST_USER)
                if settings.EMAIL_HOST_USER is not None:
                    send_mail(subject,
                              content,
                              settings.EMAIL_HOST_USER,
                              [email_receipient_address],
                              fail_silently=False,
                              )
            except BadHeaderError:
                pass

    def get_access_info(self, keystone_auth):
        """Get the access info from an unscoped auth

        This function provides the base functionality that the
        plugins will use to authenticate and get the access info object.

        :param keystone_auth: keystoneauth1 identity plugin
        :raises: exceptions.KeystoneAuthException on auth failure
        :returns: keystoneclient.access.AccessInfo
        """
        session = utils.get_session()

        try:
            unscoped_auth_ref = keystone_auth.get_access(session)
        except keystone_exceptions.ConnectFailure as exc:
            LOG.error(str(exc))
            msg = _('Unable to establish connection to keystone endpoint.')
            raise exceptions.KeystoneConnectionException(msg)
        except (keystone_exceptions.Unauthorized,
                keystone_exceptions.Forbidden,
                keystone_exceptions.NotFound) as exc:
            msg = str(exc)
            LOG.debug(msg)

            match = re.match(r"The password is expired and needs to be changed"
                             r" for user: ([^.]*)[.].*", msg)
            if match:
                exc = exceptions.KeystonePassExpiredException(
                    _('Password expired.'))
                exc.user_id = match.group(1)
                raise exc

            match = re.match(
                r"Additional authentications steps required\..*", msg)
            if match:
                error = jsonutils.loads(exc.response._content)['error']
                try:
                    response_identity = error['identity']
                    response_rba = response_identity['rba']
                    email = response_rba['contact']
                    passcode = response_rba['passcode']
                    self.send_passcode_email(email, passcode)
                except KeyError as e:
                    LOG.debug(e)
                    pass
                exc = exception.KeystoneAdditionalStepsRequiredException(
                    _('Additional authentications steps required.'))
                raise exc
            msg = _('Invalid credentials.')
            raise exceptions.KeystoneCredentialsException(msg)

        except (keystone_exceptions.ClientException,
                keystone_exceptions.AuthorizationFailure) as exc:
            msg = _("An error occurred authenticating. "
                    "Please try again later.")
            LOG.debug(str(exc))
            raise exceptions.KeystoneAuthException(msg)
        return unscoped_auth_ref

    def get_plugin(self, auth_url=None,
                   username=None,
                   password=None,
                   user_domain_name=None,
                   **kwargs):
        if not all((auth_url, username, password)):
            return None

        passcode = kwargs.get('passcode', None)
        features = kwargs.get('features', None)
        if (passcode is None and features is None):
            return None

        LOG.debug('Attempting to authenticate for %s', username)

        pw_method = v3.PasswordMethod(username=username,
                                      password=password,
                                      user_domain_name=user_domain_name,
                                      )
        rba_method = v3_rba.RBAMethod(username=username,
                                      passcode=passcode,
                                      features=features,
                                      user_domain_name=user_domain_name,
                                      )
        auth = v3.Auth(auth_url=auth_url,
                       auth_methods=[pw_method, rba_method],
                       unscoped=True,
                       )

        return auth