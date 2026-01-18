import psycopg
from psycopg.rows import dict_row

# Database configuration - edit these values for your setup
DB_CONFIG = {
    "dbname": "stormhalter",
    "user": "postgres",
    "password": "Odie_14232",
}


def get_connection():
    """Get a database connection with dict_row factory."""
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)
