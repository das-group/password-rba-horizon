# Password authentication plugin enhanced with Risk-Based Authentication (RBA) for OpenStack's Horizon Dashboard.

During the login attempt will the plugin collect the features IP-Address, Round-Trip-Time (RTT) and the User-Agent string.
Based on Keystone's response may the user verify the identity with a passcode that is sent to the user's contact address.

## Requirements

The login with RBA requires the presence of the Keystoneauth library that supports the RBA method and an extended Keystone identity service with the corresponding keystone_rba_plugin package.


## Installation

Install the plugin with the `pip` package manager:

    cd password_rba-horizon
    pip install .

Install from local VCS Branch using `pip`:
	`pip install <VCS>+file:///<Path_to_setup.py>@<branch>`
    or editable for development
	`pip install -e <VCS>+file:///<Path_to_setup.py>/password_rba_horizon@<branch>#egg=password_rba_horizon`

Place the Horizon configuration file `enabled/_3091_password_rba_horizon.py` into your prefered Horizon configuration location, e.g. in `horizon/openstack_dashboard/local/enabled/`.

At this point should a restart of the wsgi web server be enough to use the plugin.

To enable the RTT feature value collection, Horizon will need a deployment on an asynchronous capable web server instead, as it uses WebSockets to start the measurements, e.g. install the `daphne` web server via `pip`.
    
    pip install daphne

For this reasen is the `asgi.py` file included in the plugin. Place the file besides the default `wsgi.py` file in the `horizon/openstack_dashboard/` folder and add the following asgi deployment instruction into the `settings.py` file.

    ASGI_APPLICATION = 'openstack_dashboard.asgi.application'

Moreover requires the RTT feature value collection the use of a cached session instead of only cookie based sessions, e.g. configure the session engine to use the memcached cache.
    
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': 'controller:11211',
        },
    }

Start the asynchronous web server e.g.:
    
    daphne -b 0.0.0.0 -p 8000 openstack_dashboard.asgi:application

or via Horizons tox:

    tox -e runserver -- 0:8000

Note, that Horizon's tox testserver will require enabled sitepackages to use the installed plugin in the sitepackages. Therefore add the following attribute into the `[testenv]` section in Horizon's `tox.ini` file. 
    
    [testenv]
    sitepackages = True
    ...

The dashboard should now be running to get visited with the web browser.

## License

### Code

&copy; 2022 Vincent Unsel \& 2021 Stephan Wiefling/[Data and Application Security Group](https://das.h-brs.de)

The code in this repository is licensed under the Apache License 2.0.
See [LICENSE](LICENSE) for details.
