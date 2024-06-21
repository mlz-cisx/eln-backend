# postgres settings
DB_USER = 'joeseln'
DB_PASSWORD = 'joeseln'
DB_TABLE = 'joeseln'
DB_PORT = 5440

# folder to store pictures
PICTURES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/pictures/'
# folder to store files
FILES_BASE_PATH = '/home/jbaudisch/mlz_eln_data/pictures/'

# MLZ-ELN URL
URL_BASE_PATH = 'http://172.25.74.236:8010/'

# CORS  settings
ORIGINS = [
    "http://localhost:4500",
    "http://172.25.74.236:4500"
]

# Keycloak Settings
REALM = 'joe'
KEYCLOAK_BASEURL = f'http://172.25.74.236:8181/realms' \
                   f'/{REALM}/protocol/openid-connect'