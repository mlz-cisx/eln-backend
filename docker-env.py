import os

# PostgreSQL settings
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_TABLE = os.getenv("DB_TABLE")
DB_PORT = int(os.getenv("DB_PORT"))
DB_ADDR = os.getenv("DB_ADDR")

# Initial users
INITIAL_ADMIN = os.getenv("INITIAL_ADMIN")
INSTRUMENT_AS_ADMIN = os.getenv("INSTRUMENT_AS_ADMIN")

# Token
STATIC_ADMIN_TOKEN = os.getenv("STATIC_ADMIN_TOKEN")
STATIC_WS_TOKEN = os.getenv("STATIC_WS_TOKEN")

# Query mode
LABBOOK_QUERY_MODE = os.getenv("LABBOOK_QUERY_MODE")

# Folder paths
PICTURES_BASE_PATH = os.getenv("PICTURES_BASE_PATH", "/data/pictures")
FILES_BASE_PATH = os.getenv("FILES_BASE_PATH", "/data/files")

# Base URL
URL_BASE_PATH = os.getenv("URL_BASE_PATH")
WS_URL = os.getenv("WS_URL")

# CORS settings
ORIGINS = os.getenv("ORIGINS").split(",")

# Keycloak Settings
REALM = os.getenv("REALM")
KEYCLOAK_BASEURL = os.getenv("KEYCLOAK_BASEURL")

# Jaeger settings
JAEGER_HOST = os.getenv("JAEGER_HOST")
JAEGER_PORT = int(os.getenv("JAEGER_PORT"))
JAEGER_SERVICE_NAME = os.getenv("JAEGER_SERVICE_NAME")

STATIC_HISTORY_DEBOUNCE = int(os.getenv("STATIC_HISTORY_DEBOUNCE"))

required_vars = [
    "DB_USER",
    "DB_PASSWORD",
    "DB_TABLE",
    "DB_PORT",
    "INITIAL_ADMIN",
    "INSTRUMENT_AS_ADMIN",
    "STATIC_ADMIN_TOKEN",
    "STATIC_WS_TOKEN",
    "LABBOOK_QUERY_MODE",
    "KEYCLOAK_BASEURL",
    "URL_BASE_PATH",
    "WS_URL",
    "ORIGINS",
    "REALM",
    "JAEGER_HOST",
    "JAEGER_PORT",
    "JAEGER_SERVICE_NAME",
    "STATIC_HISTORY_DEBOUNCE",
]

# Check for required environment variables
for var in required_vars:
    if os.getenv(var) is None:
        raise EnvironmentError(f"Required environment variable '{var}' is not set.")
