# postgres settings
DB_USER = 'joeseln'
DB_PASSWORD = 'joeseln'
DB_TABLE = 'joeseln'
DB_PORT = 5440

# initial users
INITIAL_ADMIN = 'admin'
INTRUMNENT_AS_ADMIN = 'instrument'

# two modes: match and equal
LABBOOK_QUERY_MODE = 'match'
# LABBOOK_QUERY_MODE = 'equal'

# folder to store pictures
PICTURES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/pictures/'
# folder to store files
FILES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/files/'

# MLZ-ELN URL
URL_BASE_PATH = 'http://172.25.74.236:8010/'

# WS ELN URL
WS_URL = 'ws://172.25.74.236:8010/ws/'

# CORS  settings
ORIGINS = [
    "http://localhost:4500",
    "http://172.25.74.236:4500",
    "http://daphneopc01:4500",
    "http://daphneopc01.office.frm2:4500",
]

# Keycloak Settings
REALM = 'joe'
KEYCLOAK_BASEURL = f'http://172.25.74.236:8181/realms' \
                   f'/{REALM}/protocol/openid-connect'

STATIC_ADMIN_TOKEN = '#super_secret#'
STATIC_WS_TOKEN = '#super_ws_secret#'

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
