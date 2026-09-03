Sysadmin Guide
===============

.. role:: code-py(code)
   :language: Python
.. role:: code-js(code)
   :language: Javascript


Keycloak SSO
------------

ELN supports single sign-on (SSO) via Keycloak as an OpenID Connect provider.
When enabled, users are redirected to Keycloak with a **“Login via SSO”** button.

Prerequisites
~~~~~~~~~~~~~

You need a running Keycloak server. Set one up on your own server or use
`Keycloak's official Docker image <https://www.keycloak.org/getting-started/getting-started-docker>`_.

Keycloak Server Setup
~~~~~~~~~~~~~~~~~~~~~

1. **Create a realm** — log into the Keycloak admin console and create a new realm
   (e.g. ``dev``). The realm isolates ELN’s users and clients from other applications.

2. **Create a client** — inside the realm, create a new client:

   * **Client ID**: a unique identifier (e.g. ``eln``)
   * **Client type**: ``confidential`` (requires a client secret)
   * **Valid redirect URIs**: ``https://<your-eln-backend>/api/callback``
   * **Valid post logout redirect URIs**: ``https://<your-eln-frontend>/login``

3. **Get the client secret** — on the client’s *Credentials* tab, copy the secret.

Backend Configuration
~~~~~~~~~~~~~~~~~~~~~

Set Keycloak-related values in ``.env``.
An example file is provided as ``.env.sample``.

If Keycloak integration is disabled, set:

* :code-js:`KEYCLOAK_INTEGRATION=False`

All other Keycloak variables will be ignored automatically.

Frontend Configuration
~~~~~~~~~~~~~~~~~~~~~~

The frontend reads its configuration from ``frontend/source/assets/config/env.js``
or from environment variables passed via ``docker-compose.yml``.

To enable Keycloak SSO, set:

* :code-js:`KEYCLOAK_INTEGRATION: "true"`

The frontend also supports optional environment variables.
If a variable is not provided, the Angular runtime loader applies defaults.

Optional variables and defaults
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following variables are optional. If omitted, Docker injects an empty string,
and the frontend applies its built‑in defaults:

* :code-js:`API_URL` — no default; must be provided in production
* :code-js:`LAB_BOOK_SOCKET_REFRESH_INTERVAL` — defaults to ``1000`` ms
* :code-js:`INSTR_CSV_ALL` — defaults to ``true``
* :code-js:`NOTE_MAXIMUM_SIZE` — defaults to ``5000`` KB
* :code-js:`HSDS_URL`, :code-js:`HSDS_USERNAME`, :code-js:`HSDS_PASSWORD`, :code-js:`HSDS_DOMAIN` — default to empty strings



.. tip::
    Although these variables appear in the same subsection
    as the Keycloak integration settings,
    they are not part of Keycloak itself. They are general Docker‑Compose environment
    variables used by the frontend loader, and they are worth documenting because each
    of them has a defined optional‑value behavior. When omitted, Docker supplies an empty
    string and the frontend applies its own defaults, ensuring predictable runtime behavior
    and preventing placeholder literals from leaking into the application.


Example docker-compose configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Below is the recommended configuration aligned with the frontend loader:

.. code-block:: yaml

   eln-frontend:
     image: eln-frontend
     build:
       context: ./frontend/
     environment:
       SERVER_NAME: "${SERVER_NAME:-}"
       API_URL: "${API_URL:-}"
       LAB_BOOK_SOCKET_REFRESH_INTERVAL: "${LAB_BOOK_SOCKET_REFRESH_INTERVAL:-}"
       KEYCLOAK_INTEGRATION: "${KEYCLOAK_INTEGRATION:-false}"
       KEYCLOAK_BEHIND_NGINX: "${KEYCLOAK_BEHIND_NGINX:-false}"
       INSTR_CSV_ALL: "${INSTR_CSV_ALL:-}"
       NOTE_MAXIMUM_SIZE: "${NOTE_MAXIMUM_SIZE:-}"
       HSDS_URL: "${HSDS_URL:-}"
       HSDS_USERNAME: "${HSDS_USERNAME:-}"
       HSDS_PASSWORD: "${HSDS_PASSWORD:-}"
       HSDS_DOMAIN: "${HSDS_DOMAIN:-}"

.. tip::
    By the way, this configuration pattern ensures that unset variables resolve to
    empty strings, boolean flags retain predictable semantics,
    and the Angular loader can safely apply its documented defaults.
    It also prevents accidental leakage of placeholder literals
    into the running application, keeping the environment clean and reproducible.


Authentication Flow
~~~~~~~~~~~~~~~~~~~

1. User clicks **Login with Keycloak** on the frontend.
2. Browser is redirected to ``/api/login-keycloak``, which constructs the
   Keycloak authorization URL and redirects the user to the Keycloak login page.
3. After successful authentication, Keycloak redirects back to
   ``/api/callback`` with an authorization code.
4. The backend introspects the access token, creates or updates the local user,
   **syncs group memberships** from realm roles, and issues an ELN JWT.
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

When ELN is placed behind a reverse proxy, the proxy should route the frontend
application and API traffic individually.

API proxy — ``location /api/``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All requests under ``/api/`` are forwarded to the FastAPI backend. This
includes ``GET /api/events``, the Server-Sent Events (SSE) stream that
delivers real-time change notifications to the browser. SSE must not be
buffered by the proxy, so buffering is disabled:

.. code-block:: nginx

   location /api/ {
       proxy_pass http://127.0.0.1:8010;
       proxy_buffering off;
       proxy_cache off;
   }

Increase upload limit for file attachments:

.. code-block:: nginx

   client_max_body_size 50M;


Static frontend — ``location /``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Serve the pre-built Angular application:

.. code-block:: nginx

   location / {
       root /path/to/frontend/browser;
       try_files $uri $uri/ /index.html;
   }


HTTPS and SSL termination
~~~~~~~~~~~~~~~~~~~~~~~~~

With SSL termination, inject ``upgrade-insecure-requests`` into the CSP:

.. code-block:: html

   <meta http-equiv="Content-Security-Policy"
         content="upgrade-insecure-requests">

In Docker deployments this is done automatically by ``docker-entrypoint.sh``
when SSL certificates are detected.



