# postgres settings
DB_USER = 'joeseln'
DB_PASSWORD = 'joeseln'
DB_TABLE = 'joeseln'
DB_PORT = 5440
DB_ADDR = 'localhost'

# initial users should not be changed
INITIAL_ADMIN = 'admin'
INSTRUMENT_AS_ADMIN = 'instrument'

# token should be moved to external store for secrets
STATIC_ADMIN_TOKEN = '#super_secret#'

# two modes: match and equal
LABBOOK_QUERY_MODE = 'match'
# LABBOOK_QUERY_MODE = 'equal'

# folder to store pictures
PICTURES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/pictures/'
# folder to store files
FILES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/files/'

# MLZ-ELN URL
URL_BASE_PATH = 'http://localhost:8010/api/'

# Frontend url
APP_BASE_PATH = 'http://localhost:4500/'

# WS ELN URL
WS_URL = 'ws://localhost:4501/ws/'
WS_PORT = 4501
WS_INTERNAL_IP = '0.0.0.0'

# CORS  settings
ORIGINS = [
    "http://localhost:4500",
    "http://172.25.74.236:4500",
    "http://daphneopc01:4500",
    "http://daphneopc01.office.frm2:4500",
]

# Keycloak Settings

KEYCLOAK_REALM_NAME = 'joe'
KEYCLOAK_CLIENT_ID = 'client_backend'
KEYCLOAK_CLIENT_SECRET = 'ZMqN0Fi4BNIFdcGvJsXL80hgCcv24jOr'
KEYCLOAK_SERVER_URL = 'http://daphneopc01:8082/'
KEYCLOAK_INTEGRATION = True

# don't use Hashtags , it is a parameter of a path
STATIC_WS_TOKEN = 'super_ws_secret'

STATIC_HISTORY_DEBOUNCE = 5

# Typesense connection
TYPESENSE_HOST = "localhost"
TYPESENSE_PORT = 8108
TYPESENSE_PROTOCOL = "http"
TYPESENSE_API_KEY = "#super_secret#"

# Jaeger Settings
# docker
# run - d - -name
# jaeger - e
# COLLECTOR_ZIPKIN_HTTP_PORT = 9411 - p
# 5775: 5775 / udp - p
# 6831: 6831 / udp - p
# 6832: 6832 / udp - p
# 5778: 5778 - p
# 16686: 16686 - p
# 14268: 14268 - p
# 9411: 9411
# jaegertracing / all - in -one: 1.6

JAEGER_HOST = 'localhost'
JAEGER_PORT = 6831
JAEGER_SERVICE_NAME = 'MLZ-ELN'

# in kilobytes
ELEM_MAXIMUM_SIZE = 5000
