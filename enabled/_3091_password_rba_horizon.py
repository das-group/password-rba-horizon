# Copyright 2022 Vincent Unsel
#
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

from django.conf import settings

# The name of the feature to be added. Required.
FEATURE = 'password_rba_horizon'

# If set to True, this feature will not be added to the settings.
DISABLED = False

# A list of applications to be prepended to INSTALLED_APPS
ADD_INSTALLED_APPS = [
    'channels',
    'password_rba_horizon',
]

if not DISABLED:
    # Remove the default PasswordPlugin
    try:
        settings.AUTHENTICATION_PLUGINS.remove(
            'openstack_auth.plugin.password.PasswordPlugin'
        )
    except ValueError:
        pass
    # Append the RBAPasswordPlugin
    finally:
        settings.AUTHENTICATION_PLUGINS.append(
            'password_rba_horizon.plugin.RBAPasswordPlugin',
        )
    # Changes the used login form instead of overriding the login path.
    try:
        settings.AUTHENTICATION_URLS.remove(
            'openstack_auth.urls'
        )
    finally:
        settings.AUTHENTICATION_URLS.append(
        'password_rba_horizon.urls',
    )


# ASGI_APPLICATION = 'openstack_dashboard.asgi.application'

AUTO_DISCOVER_STATIC_FILES = True

# Send email to the console by default
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Or send them to /dev/null
#EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

# Configure these for your outgoing email host
#EMAIL_HOST = '127.0.0.1'
#EMAIL_PORT = 1025
#EMAIL_HOST_USER = 'noreply'
#EMAIL_HOST_PASSWORD = ''
#EMAIL_HOST = 'smtp.my-company.com'
#EMAIL_PORT = 25
#EMAIL_HOST_USER = 'djangomail'
#EMAIL_HOST_PASSWORD = 'top-secret!'
