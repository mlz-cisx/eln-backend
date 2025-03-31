import os

# PostgreSQL settings
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TABLE = os.getenv("DB_TABLE")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_ADDR = os.getenv("DB_ADDR")

# Initial users
INITIAL_ADMIN = os.getenv("INITIAL_ADMIN", "admin")
INSTRUMENT_AS_ADMIN = os.getenv("INSTRUMENT_AS_ADMIN", "instrument")

# Token
STATIC_ADMIN_TOKEN = os.getenv("STATIC_ADMIN_TOKEN")
STATIC_WS_TOKEN = os.getenv("STATIC_WS_TOKEN")

# Query mode
LABBOOK_QUERY_MODE = os.getenv("LABBOOK_QUERY_MODE", "match")

# Folder paths
PICTURES_BASE_PATH = os.getenv("PICTURES_BASE_PATH", "/data/pictures/")
FILES_BASE_PATH = os.getenv("FILES_BASE_PATH", "/data/files/")

# Base URL
URL_BASE_PATH = os.getenv("URL_BASE_PATH")
WS_URL = os.getenv("WS_URL")
WS_PORT = os.getenv("WS_PORT")

WS_INTERNAL_IP = os.getenv("WS_INTERNAL_IP")

# CORS settings
ORIGINS = os.getenv("ORIGINS", "").split(",")

# Keycloak Settings
KEYCLOAK_REALM_NAME = os.getenv("KEYCLOAK_REALM_NAME")
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET")
KEYCLOAK_INTEGRATION = os.getenv("KEYCLOAK_INTEGRATION", "True") == "True"

CENTRIFUGO_API_KEY = os.getenv("CENTRIFUGO_API_KEY", "KEY")
CENTRIFUGO_JWT_KEY = os.getenv("CENTRIFUGO_JWT_KEY", "KEY")
CENTRIFUGO_CHANNEL = os.getenv("CENTRIFUGO_CHANNEL", "default")

# Jaeger settings
JAEGER_HOST = os.getenv("JAEGER_HOST", "localhost")
JAEGER_PORT = int(os.getenv("JAEGER_PORT", "6831"))
JAEGER_SERVICE_NAME = os.getenv("JAEGER_SERVICE_NAME", "MLZ-ELN")

STATIC_HISTORY_DEBOUNCE = int(os.getenv("STATIC_HISTORY_DEBOUNCE", "5"))

NOTE_MAXIMUM_SIZE = int(os.getenv("NOTE_MAXIMUM_SIZE", "5000"))
