Sysadmin Guide
===============

.. role:: code-py(code)
   :language: Python
.. role:: code-js(code)
   :language: Javascript


Keycloak SSO
---------------

ELN supports single sign-on (SSO) via Keycloak as an OpenID Connect provider.
When enabled, users are redirected to the Keycloak with "login via SSO"" button

Prerequisites
~~~~~~~~~~~~~

You need a running Keycloak server. Set one up at your own server or use
`Keycloak's official Docker image <https://www.keycloak.org/getting-started/getting-started-docker>`_.

Keycloak Server Setup
~~~~~~~~~~~~~~~~~~~~~

1. **Create a realm** — log into the Keycloak admin console, create a new realm
   (e.g. ``dev``). The realm isolates ELN's users and clients from other applications.

2. **Create a client** — inside the realm, create a new client:

   * **Client ID**: a unique identifier (e.g. ``eln``)
   * **Client type**: ``confidential`` (requires a client secret)
   * **Valid redirect URIs**: ``https://<your-eln-backend>/api/callback``
   * **Valid post logout redirect URIs**: ``https://<your-eln-frontend>/login``

3. **Get the client secret** — on the client's "Credentials" tab, copy the secret.


Backend Configuration
~~~~~~~~~~~~~~~~~~~~~

Set these values in ``joeseln_backend/conf/base_conf.py`` (or via environment
variables in ``docker-compose.yml``):

.. confval:: KEYCLOAK_INTEGRATION
   :type: :code-py:`bool`
   :required: True

   Set to ``True`` to enable Keycloak SSO.

.. confval:: KEYCLOAK_SERVER_URL
   :type: :code-py:`str`
   :required: True

   Base URL of the Keycloak server, e.g. ``https://auth.example.com``.
   This is the root of the realm's well-known configuration.

.. confval:: KEYCLOAK_REALM_NAME
   :type: :code-py:`str`
   :required: True

   Name of the Keycloak realm, e.g. ``dev``.

.. confval:: KEYCLOAK_CLIENT_ID
   :type: :code-py:`str`
   :required: True

   The client ID configured in Keycloak, e.g. ``eln``.

.. confval:: KEYCLOAK_CLIENT_SECRET
   :type: :code-py:`str`
   :required: True

   The client secret from Keycloak's "Credentials" tab.

Frontend Configuration
~~~~~~~~~~~~~~~~~~~~~~

In the frontend config (``frontend/source/assets/config/env.js`` or
``docker-compose.yml``), set :code-js:`KEYCLOAK_INTEGRATION` to ``true`` so the
login page shows the "Login with Keycloak" button.

Authentication Flow
~~~~~~~~~~~~~~~~~~~

1. User clicks **Login with Keycloak** on the frontend.
2. Browser is redirected to ``/api/login-keycloak``, which constructs the
   Keycloak authorization URL and redirects the user to the Keycloak login page.
3. After successful authentication, Keycloak redirects back to
   ``/api/callback`` with an authorization code.
4. The backend introspects the access token, creates or updates the local user, **syncs group memberships** from realm roles,
   and issues an ELN JWT.
5. The browser is redirected to the frontend with the ELN token as a query
   parameter, completing the login.


Healthcheck
-----------

The backend exposes an HTTP healthcheck endpoint at ``/api/health/`` that
verifies connectivity to its critical dependencies.

Checks performed
~~~~~~~~~~~~~~~~

The endpoint runs two checks on every request:

1. **PostgreSQL** — executes ``SELECT 1`` against the database. If the
   query fails, the endpoint returns HTTP 503 with the detail
   ``"Database unavailable"``.

2. **Typesense** — calls the Typesense native health API
   (``GET /health``). If Typesense is unreachable, the endpoint returns
   HTTP 503 with the detail ``"Typesense unavailable"``.

If all checks pass, the response is the literal string ``"ok"`` with
HTTP status 200.


Reverse Proxy
-------------

When ELN is placed behind reverse proxy, proxy should route the frontend
application, API and WebSocket traffic individually.


API proxy — ``location /api/``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All requests under ``/api/`` are forwarded to the FastAPI backend:

.. code-block:: nginx

   location /api/ {
       proxy_pass http://127.0.0.1:8010;
   }

The default Nginx upload limit (1 MB) is often too low for file
attachments in labbook entries. Increase it with:

.. code-block:: nginx

   client_max_body_size 50M;


WebSocket proxy — ``location /ws/``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-time collaboration uses WebSocket connections routed through a
dedicated WebSocket server. A mapping is needed to preserve the
``Upgrade`` header:

.. code-block:: nginx

   map $http_upgrade $connection_upgrade {
       default upgrade;
       '' close;
   }

   location /ws/ {
       proxy_pass http://127.0.0.1:8011;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }


Static frontend — ``location /``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All other requests serve the pre-built Angular application.

.. code-block:: nginx

   location / {
       root /path/to/frontend/browser;
       try_files $uri $uri/ /index.html;
   }


HTTPS and SSL termination
~~~~~~~~~~~~~~~~~~~~~~~~~

With SSL termination in place, inject ``upgrade-insecure-requests`` into
the frontend's Content Security Policy to ensure all client-side HTTP
requests are upgraded to HTTPS automatically:

.. code-block:: html

   <meta http-equiv="Content-Security-Policy"
         content="upgrade-insecure-requests">

In the Docker deployment this is done automatically by the
``docker-entrypoint.sh`` script when SSL certificates are detected.


