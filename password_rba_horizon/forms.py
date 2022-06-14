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

import copy
import logging

from django.conf import settings
from django.contrib.auth import authenticate

from django import forms
from django.utils.translation import gettext_lazy as _
from django.views.decorators.debug import sensitive_variables

from openstack_auth import exceptions
from openstack_auth import forms as oa_forms
from openstack_auth import utils
from openstack_auth.forms import get_region_endpoint

from password_rba_horizon import exceptions as exception

LOG = logging.getLogger(__name__)


class Login(oa_forms.Login):
    """Form used for logging in a user.
    Inherits from the base ``openstack_auth.forms.Login``
    class to keep default functionality.
    """
    class Media:
        js = ('login-rba.js',)

    error_css_class = "error"
    passcode = forms.RegexField(label=_("Security code"),
                                strip=False,
                                widget=forms.widgets.HiddenInput(
                                    attrs={'autocomplete': 'one-time-code',
                                           'value': '',
                                           'disable': True}),
                                required=False,
                                regex=r"^\d{6,8}$",
                                min_length=6,
                                max_length=8,
                                initial='',
                                empty_value='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['passcode'] = copy.deepcopy(self.base_fields['passcode'])
        if self.request.method == 'GET':
            self.request.session['rtt'] = None

    @sensitive_variables()
    def clean(self):
        default_domain = settings.OPENSTACK_KEYSTONE_DEFAULT_DOMAIN
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        passcode = self.cleaned_data.get('passcode')
        domain = self.cleaned_data.get('domain', default_domain)
        region_id = self.cleaned_data.get('region')
        try:
            region = get_region_endpoint(region_id)
        except (ValueError, IndexError, TypeError):
            raise forms.ValidationError("Invalid region %r" % region_id)
        self.cleaned_data['region'] = region

        if not (username and password):
            # Don't authenticate, just let the other validators handle it.
            return self.cleaned_data

        try:
            features = None
            if passcode is None:
                raise exception.KeystoneAdditionalStepsRequiredException()
            if not passcode:
                rtt = self.request.session.get('rtt')
                features = {'ip': utils.get_client_ip(self.request),
                            'rtt': rtt if rtt is not None else '',
                            'ua': self.request.headers.get('User-Agent', '')}
                LOG.debug(str(features))
                passcode = None
            self.user_cache = authenticate(request=self.request,
                                           auth_url=region,
                                           username=username,
                                           password=password,
                                           user_domain_name=domain,
                                           passcode=passcode,
                                           features=features)

            LOG.debug("forms self.user_cache" + str(self.user_cache))

            LOG.info('Login successful for user "%(username)s" using domain '
                     '"%(domain)s", remote address %(remote_ip)s.',
                     {'username': username, 'domain': domain,
                      'remote_ip': utils.get_client_ip(self.request)})

        except exceptions.KeystonePassExpiredException as exc:
            LOG.info('Login failed for user "%(username)s" using domain '
                     '"%(domain)s", remote address %(remote_ip)s: password'
                     ' expired.',
                     {'username': username, 'domain': domain,
                      'remote_ip': utils.get_client_ip(self.request)})
            if utils.allow_expired_passowrd_change():
                raise
            raise forms.ValidationError(exc)

        except exception.KeystoneAdditionalStepsRequiredException:
            self.show_passcode_field()
            self.add_error(None, 'For security reasons we would '
                            'like to verify your identity. This is '
                            'required when something about your '
                            'sign-in activity changes, like signing in '
                            'from a new location or a new device.')
            msg = ('We\'ve sent a security '
                   'code to your deposited contact address. '
                   'Please enter the code to log in.')
            raise forms.ValidationError(msg)

        except exceptions.KeystoneAuthException as exc:
            self.reset_fields()
            LOG.info('Login failed for user "%(username)s" using domain '
                     '"%(domain)s", remote address %(remote_ip)s.',
                     {'username': username, 'domain': domain,
                      'remote_ip': utils.get_client_ip(self.request)})
            raise forms.ValidationError(exc)
        return self.cleaned_data

    def show_passcode_field(self):
        self.fields['username'].widget = forms.widgets.HiddenInput()
        self.fields['password'].widget = forms.widgets.HiddenInput()
        self.fields['region'].widget = forms.widgets.HiddenInput()
        if settings.OPENSTACK_KEYSTONE_MULTIDOMAIN_SUPPORT:
            self.fields['domain'].widget = forms.widgets.HiddenInput()
        if settings.WEBSSO_ENABLED:
            self.fields['auth_type'].widget = forms.widgets.HiddenInput()
        self.fields['passcode'].widget = forms.widgets.TextInput(
            attrs={'autofocus': 'autofocus',
                   'value': '',
                   'required': True,
                   'autocomplete': 'one-time-code'
                   })

    def reset_fields(self):
        self.fields['username'].widget = forms.TextInput(
            attrs={"autofocus": "autofocus"})
        self.fields['password'].widget = forms.PasswordInput(
            render_value=False)
        if len(self.fields['region'].choices) > 1:
            self.fields['region'].widget = forms.widgets.Select()
        if settings.OPENSTACK_KEYSTONE_MULTIDOMAIN_SUPPORT:
            if settings.OPENSTACK_KEYSTONE_DOMAIN_DROPDOWN:
                self.fields['domain'].widget = forms.widgets.Select()
            else:
                self.fields['domain'].widget = forms.widgets.TextInput()
        if settings.WEBSSO_ENABLED:
            self.fields['auth_type'].widget = forms.widgets.Select()
        self.fields['passcode'].widget = forms.widgets.HiddenInput(
            attrs={'autocomplete': 'one-time-code',
                   'value': '',
                   'disabled': True})
