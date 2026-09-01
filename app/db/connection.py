from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()

RUN_TEST = os.getenv("RUN_TEST", "False").lower() == "true"


def get_connection():
    """To get db engine and connection."""

    if (RUN_TEST):
        return get_test_connection()

    config = {
        "host": os.getenv("PROD_DB_HOST", "localhost"),
        "user": os.getenv("PROD_DB_USER", "root"),
        "port": int(os.getenv("PROD_DB_PORT", "3306")),
        "autocommit": False,
        "password": os.getenv("PROD_DB_PASSWORD") or os.getenv("DB_CONNECTION_PASSWORD"),
        "database": os.getenv("PROD_DB_NAME") or os.getenv("DB_NAME"),
    }

    ca_cert = os.getenv("PROD_DB_CA_CERT")

    if ca_cert:
        config["ssl_ca"] = ca_cert

    return mysql.connector.connect(**config)


def get_test_connection():
    """To get test db engine and connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        autocommit=False,
        password=os.getenv('TEST_DB_CONNECTION_PASSWORD'),
        database=os.getenv('TEST_DB_NAME'),
    )
