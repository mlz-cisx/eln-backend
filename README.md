# MLZ-ELN Backend


## Development Server

#### System Requirements

- Tested on **Ubuntu 22.04.4 Desktop** with **Python 3.10**

#### Installation Steps

- Install required packages:
  ```bash
  apt install python3-pip 
  ```
- Install Node.js v22 and npm via NodeSource
- Install Chromium (/usr/bin/chromium), and install puppeteer with:

  ``` cd joeseln_backend/export && npm install ```

- Create a virtual environment (e.g. `venv`)
- Install dependencies from `requirements.txt`
- Create a **PostgreSQL** database
- Create a **Typesense** service, e.g. with:
  ```bash
  docker-compose up typesense
  ```
- Create two folders for storing uploaded pictures and files, with its paths PICTURES_BASE_PATH and FILES_BASE_PATH

#### Optional Services

- For **OIDC integration**, create a **Keycloak** service, e.g. with:
  ```bash
  docker-compose up keycloak
  ```
- For  **OIDC integration** you must specify the APP_BASE_PATH

#### Configuration

- Enter all previously generated configuration parameters into:
  [joeseln_backend/conf/base_conf.py](joeseln_backend/conf/base_conf.py)

#### Initialization and Server Start

- Activate the virtual environment:
  ```bash
  source venv/bin/activate
  ```
- Start the websocket server:
  ```bash
  python joeseln_backend/ws/ws_server.py
  ```
  
  Please refer to the websocket configuration in [joeseln_backend/conf/base_conf.py](joeseln_backend/conf/base_conf.py)

- [joeseln_backend/main.py](joeseln_backend/main.py) creates tables and initial admin users
- ```cd joeseln_backend```
- Due to nested async calls with websockets, use `--loop asyncio` to start the development server from directory where ```main.py``` is located.
  Here the application will automatically reload if you change any of the source files:
  ```bash
  uvicorn main:app --reload --port 8010 --host 0.0.0.0 --loop asyncio
  ```
  
- For more options, see [Uvicorn CLI](https://www.uvicorn.org/#command-line-options), e.g. you could start the development server with:
  ```bash
  uvicorn main:app --workers 3 --port 8010 --host 0.0.0.0 --loop asyncio
  ```

#### Access

- Login on MLZ-ELN Frontend with credentials:
  - **Username:** `admin`
  - **Password:** `secret`

#### Backend Api

- **Swagger:** [http://localhost:8010/api/docs](http://localhost:8010/api/docs)
- **Redoc:** [http://localhost:8010/api/redoc](http://localhost:8010/api/redoc)


#### Role Model Documentation

- For a full understanding of the role model, please refer to:
  - [RoleDocs.md](joeseln_backend/services/role/role_docs/RoleDocs.md)
  - [UserRoleModel.pdf](joeseln_backend/services/role/role_docs/UserRoleModel.pdf)




##  Docker Deployment


- For using a production-like environment or actual deployment, please refer to the build structure and the comments in [docker-compose.yml](docker-compose.yml). Specify your environment variables there.
It is recommended to start eln-postgres initially, as it provides the necessary database backend for dependent services.

## License

License: [AGPL 3](LICENSE)  


