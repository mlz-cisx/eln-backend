import os
import dotenv

# Load environment variables from .env file if it exists
dotenv.load_dotenv()


def ensure_trailing_slash(value: str | None) -> str | None:
    if not value:
        return value
    return value.rstrip("/") + "/"


def get_secure_env_variable(var_name: str, default: str | None = None) -> str:
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable '{var_name}' is not set and no default value provided.")
    if value.startswith("<") and value.endswith(">"):
        raise ValueError(f"Environment variable '{var_name}' is set to a placeholder value. Please provide a valid value.") 
    return value


DEFAULT_JWT_SECRET = (
    "mlzeln_default_jwt_secret_"
    "u7fK9wq3TzA1pLxE4mN8bR2sV6yC0dQ5hJkW3tZ9gF2sL7pB1rX8nM4vT6cY0"
)


def get_secure_jwt_secret(var_name: str) -> str:
    value = os.getenv(var_name)

    # Use deterministic default if missing or empty
    if value is None or value.strip() == "":
        return DEFAULT_JWT_SECRET

    # Reject placeholder values like <secret>
    if value.startswith("<") and value.endswith(">"):
        raise ValueError(
            f"Environment variable '{var_name}' is set to a placeholder value. "
            "Please provide a valid value."
        )

    return value


# PostgreSQL settings
DB_USER = get_secure_env_variable("DB_USER")
DB_PASSWORD = get_secure_env_variable("DB_PASSWORD")
DB_TABLE = get_secure_env_variable("DB_TABLE")
DB_PORT = int(get_secure_env_variable("DB_PORT", "5432"))
DB_ADDR = get_secure_env_variable("DB_ADDR")

PLAYWRIGHT_WS = get_secure_env_variable("PLAYWRIGHT_WS")
PLAYWRIGHT_MEM = int(get_secure_env_variable("PLAYWRIGHT_MEMORY_LIMIT_MB", "1024"))
PLAYWRIGHT_CPU = int(get_secure_env_variable("PLAYWRIGHT_CPU_LIMIT", "1"))

# Initial users
INITIAL_ADMIN = get_secure_env_variable("INITIAL_ADMIN", "admin")
INSTRUMENT_AS_ADMIN = get_secure_env_variable("INSTRUMENT_AS_ADMIN", "instrument")

# Token
STATIC_ADMIN_TOKEN = get_secure_env_variable("STATIC_ADMIN_TOKEN")
STATIC_WS_TOKEN = get_secure_env_variable("STATIC_WS_TOKEN")

# Query mode
LABBOOK_QUERY_MODE = get_secure_env_variable("LABBOOK_QUERY_MODE", "match")

# Folder paths
PICTURES_BASE_PATH = get_secure_env_variable("PICTURES_BASE_PATH", "/data/pictures/")
FILES_BASE_PATH = get_secure_env_variable("FILES_BASE_PATH", "/data/files/")

# Base URL
URL_BASE_PATH = ensure_trailing_slash(get_secure_env_variable("URL_BASE_PATH"))
WS_URL = ensure_trailing_slash(get_secure_env_variable("WS_URL"))
APP_BASE_PATH = ensure_trailing_slash(get_secure_env_variable("APP_BASE_PATH", ""))

WS_PORT = get_secure_env_variable("WS_PORT")

WS_INTERNAL_IP = get_secure_env_variable("WS_INTERNAL_IP")

# CORS settings
ORIGINS = get_secure_env_variable("ORIGINS", "").split(",")


# --- Keycloak integration flag ---
KEYCLOAK_INTEGRATION = get_secure_env_variable("KEYCLOAK_INTEGRATION", "True") == "True"

# --- Load Keycloak variables normally ---
KEYCLOAK_REALM_NAME = get_secure_env_variable("KEYCLOAK_REALM_NAME", "")
KEYCLOAK_SERVER_URL = ensure_trailing_slash(get_secure_env_variable("KEYCLOAK_SERVER_URL", ""))
KEYCLOAK_CLIENT_ID = get_secure_env_variable("KEYCLOAK_CLIENT_ID", "")
KEYCLOAK_CLIENT_SECRET = get_secure_env_variable("KEYCLOAK_CLIENT_SECRET", "")

# --- Override if integration disabled ---
if not KEYCLOAK_INTEGRATION:
    KEYCLOAK_REALM_NAME = ""
    KEYCLOAK_SERVER_URL = ""
    KEYCLOAK_CLIENT_ID = ""
    KEYCLOAK_CLIENT_SECRET = ""

# typesense connection
TYPESENSE_HOST = get_secure_env_variable("TYPESENSE_HOST")
TYPESENSE_PORT = int(get_secure_env_variable("TYPESENSE_PORT", "8108"))
TYPESENSE_PROTOCOL = get_secure_env_variable("TYPESENSE_PROTOCOL", "http")
TYPESENSE_API_KEY = get_secure_env_variable("TYPESENSE_API_KEY")

# Jaeger settings
JAEGER_HOST = get_secure_env_variable("JAEGER_HOST", "localhost")
JAEGER_PORT = int(get_secure_env_variable("JAEGER_PORT", "6831"))
JAEGER_SERVICE_NAME = get_secure_env_variable("JAEGER_SERVICE_NAME", "MLZ-ELN")

STATIC_HISTORY_DEBOUNCE = int(get_secure_env_variable("STATIC_HISTORY_DEBOUNCE", "5"))

ELEM_MAXIMUM_SIZE = int(get_secure_env_variable("ELEM_MAXIMUM_SIZE", "5000"))

TOKEN_VALIDITY = int(get_secure_env_variable("TOKEN_VALIDITY", str(50)))

JWT_SECRET_KEY = get_secure_jwt_secret("JWT_SECRET_KEY")
JWT_ALGORITHM = get_secure_env_variable("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(get_secure_env_variable("JWT_ACCESS_TOKEN_EXPIRE_MINUTES","20"))
JWT_ACCESS_TOKEN_EXPIRE_SECONDS = int(get_secure_env_variable("JWT_ACCESS_TOKEN_EXPIRE_SECONDS","1000"))
JWT_DOWNLOAD_TOKEN_EXPIRE_MINUTES = int(get_secure_env_variable("JWT_DOWNLOAD_TOKEN_EXPIRE_MINUTES","1440"))
JWT_LEEWAY = int(get_secure_env_variable("JWT_LEEWAY","300"))

