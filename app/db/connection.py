from dotenv import load_dotenv
import os
import mysql.connector

load_dotenv()


def get_connection():
    """To get db engine and connection."""
    return mysql.connector.connect(
        host="localhost",
        user="root",
        autocommit=False,
        password=os.getenv('DB_CONNECTION_PASSWORD'),
        database=os.getenv('DB_NAME'),
    )
