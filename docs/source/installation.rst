Installation
=============

.. tip::
    It is recommanded to use Docker for deployment.

Docker
------------

* `Install Docker`_ for your system
* Adjust parameter in ``.env`` and ``docker-compose.yml`` according to :doc:`configuration`

.. code-block::

      # copy docker-compose to parent folder, the file structure should be
      # .
      # ├── frontend/
      # │   └── Dockerfile
      # ├── backend/
      # │   └── Dockerfile
      # └── docker-compose.yml
      cp docker-compose.yaml ..

      # build both frontend and backend images
      docker-compose build

      # start all services
      docker-compose up


.. _install-from-source:

From Source code
------------

.. _target:

The following was tested on **Ubuntu 22.04.4 Desktop** with **Python 3.10** and **Node 22**

* Refer to offcial installation guides, install `PostgreSQL`_, `Typesense`_, and `Playwright`_
* Adjust parameter in ``backend/.env`` and  ``frontend/source/assets/config/env.js`` according to :doc:`configuration`

.. code-block::

    # install necessary system dependency
    apt install python3-pip poppler-utils

    # install backend envriroment
    cd backend && pip install -r requirement.txt

    # install frontend dependency
    cd frontend && npm install

    # start backend service
    cd backend && uvicorn main:app --reload --port 8010 --host 0.0.0.0 --loop asyncio

    # start websocket service
    cd backend && python -m joeseln_backend.ws.ws_server

    # build frontend and start a development server
    cd frontend && npx ng serve


.. _Install Docker: https://docs.docker.com/engine/install/
.. _PostgreSQL: https://www.postgresql.org/docs/current/tutorial-install.html
.. _Typesense: https://typesense.org/docs/guide/install-typesense.html
.. _Playwright: https://playwright.dev/python/docs/intro

