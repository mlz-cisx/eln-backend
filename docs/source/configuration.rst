Configuration
=============

.. role:: code-py(code)
   :language: Python
.. role:: code-js(code)
   :language: Javascript


.. caution::

   * For Docker deployment, address of services is alredy given in ``docker-compose.yml``
   * For source code deployment, make sure all required services are alredy installed (see :ref:`install-from-source`)


backend
-------------

.. note::

    Edit those in ``.env``. An example ``.env`` file is provided as ``.env.sample``.


.. confval:: DB_USER
   :type: :code-py:`str`
   :required: True

   PostgreSQL user name

.. confval:: DB_PASSWORD
   :type: :code-py:`str`
   :required: True

   PostgreSQL user secret

.. confval:: DB_TABLE
   :type: :code-py:`str`
   :required: True

   PostgreSQL database name

.. confval:: DB_PORT
   :type: :code-py:`int`
   :required: True
   :default: ``5432``

   PostgreSQL port

.. confval:: DB_ADDR
   :type: :code-py:`str`
   :required: True

   PostgreSQL address

.. confval:: PLAYWRIGHT_WS
   :type: :code-py:`str`
   :required: True

   Playwright address

.. confval:: PLAYWRIGHT_MEMORY_LIMIT_MB
   :type: :code-py:`int`
   :default: ``1024``

   Playwright memory limit in MB

.. confval:: PLAYWRIGHT_CPU_LIMIT
   :type: :code-py:`int`
   :default: ``1``

   Playwright CPU limit

.. confval:: TYPESENSE_HOST
   :type: :code-py:`str`
   :required: True

   Typesense address

.. confval:: TYPESENSE_PORT
   :type: :code-py:`int`
   :required: True
   :default: `8108`

   Typesense port

.. confval:: TYPESENSE_PROTOCOL
   :type: :code-py:`str`
   :default: ``http``

   Typesense connection protocol

.. confval:: TYPESENSE_API_KEY
   :type: :code-py:`str`
   :required: True

   Typesense api key

.. confval:: KEYCLOAK_INTEGRATION
   :type: :code-py:`bool`
   :required: True

   enable SSO login with Keycloak

.. confval:: KEYCLOAK_SERVER_URL
   :type: :code-py:`str`
   :required: False

   Keycloak server URL

.. confval:: KEYCLOAK_REALM_NAME
   :type: :code-py:`str`
   :required: False

   Keycloak realm name

.. confval:: KEYCLOAK_CLIENT_ID
   :type: :code-py:`str`
   :required: False

   Keycloak client ID

.. confval:: KEYCLOAK_CLIENT_SECRET
   :type: :code-py:`str`
   :required: False

   Keycloak client secret

.. confval:: APP_BASE_PATH
   :type: :code-py:`str`
   :required: True

   Base path for the eln app, eg. ``https://eln.example.com``

.. confval:: URL_BASE_PATH
   :type: :code-py:`str`
   :required: True

   Base path for the eln **backend**, eg. ``https://eln.example.com/api``

.. confval:: WS_URL
   :type: :code-py:`str`
   :required: True

   Path to Websocket services, eg. ``https://eln.example.com/ws``

.. confval:: WS_PORT
   :type: :code-py:`int`
   :required: True

   Websocket services port

.. confval:: WS_INTERNAL_IP
   :type: :code-py:`str`
   :default: ``0.0.0.0``

   Internal IP address for Websocket service to bind to

.. confval:: ORIGINS
   :type: :code-py:`list[str]`
   :required: True

   Allowed CORS origins, eg. ``https://eln.example.com, https://eln2.example.com``

.. confval:: INITIAL_ADMIN
   :type: :code-py:`str`
   :default: ``"admin"``

   auto created first admin accout name

.. confval:: INSTRUMENT_AS_ADMIN
   :type: :code-py:`str`
   :default: ``"instrument"``

   account name for instrument ingestor

.. confval:: STATIC_ADMIN_TOKEN
   :type: :code-py:`str`
   :required: True

   token for ingestor (pick random string)

.. confval:: STATIC_WS_TOKEN
   :type: :code-py:`str`
   :required: True

   token for internal Websocket connection (pick random string)

.. confval:: LABBOOK_QUERY_MODE
   :type: :code-py:`str`
   :default: ``"match"``

   Labbook management mode


.. caution::

   Make sure those path exist (and correctly bind to container)

.. confval:: PICTURES_BASE_PATH
   :type: :code-py:`str`
   :default: ``/data/pictures/``

   Path to store pictures

.. confval:: FILES_BASE_PATH
   :type: :code-py:`str`
   :default: ``/data/files/``

   Path to store files

.. confval:: ELEM_MAXIMUM_SIZE
   :type: :code-py:`int`
   :default: ``5000``

   Max elememt size allowed

.. confval:: TOKEN_VALIDITY
   :type: :code-py:`int`
   :default: ``50``

   Token validity in seconds

.. confval:: JWT_SECRET_KEY
   :type: :code-py:`str`
   :required: True

   JWT secret key used for signing tokens

.. confval:: JWT_ALGORITHM
   :type: :code-py:`str`
   :default: ``HS256``

   JWT signing algorithm

.. confval:: JWT_ACCESS_TOKEN_EXPIRE_MINUTES
   :type: :code-py:`int`
   :default: ``20``

   JWT access token expiration time in minutes

.. confval:: JWT_ACCESS_TOKEN_EXPIRE_SECONDS
   :type: :code-py:`int`
   :default: ``1000``

   JWT access token expiration time in seconds

.. confval:: JWT_DOWNLOAD_TOKEN_EXPIRE_MINUTES
   :type: :code-py:`int`
   :default: ``1440``

   JWT download token expiration time in minutes (default 24 h)

.. confval:: JWT_LEEWAY
   :type: :code-py:`int`
   :default: ``300``

   JWT leeway in seconds for token validation


.. confval:: STATIC_HISTORY_DEBOUNCE
   :type: :code-py:`int`
   :default: ``5``

   Debound time for recording edit history


frontend
-------------

.. note::

    Edit those in either ``docker-compose.yml`` (for Docker deployment) or in ``frontend/source/assets/config/env.js``


.. confval:: SERVER_NAME
   :type: :code-js:`String`
   :required: True

   Base path for SNI filtering, eg. ``eln.example.com``

.. confval:: WS_URL
   :type: :code-js:`String`
   :required: True

   Path to Websocket service, eg. ``wss://eln.example.com``

.. confval:: API_URL
   :type: :code-js:`String`
   :required: True

   Path to backend service, eg. ``https://eln.example.com``

.. confval:: KEYCLOAK_INTEGRATION
   :type: :code-js:`boolean`
   :required: True

   Enable SSO login with keycloak


.. confval:: instr_csv_all
  :type: :code-js:`boolean`
  :required: False

   allow all user to download raw csv generated by instrument

