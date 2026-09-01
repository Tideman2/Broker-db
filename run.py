import os

import uvicorn

from app.db.Migration.run_migrations import read_schema_migration_table
from app.db.connection import get_connection


connection = get_connection()

try:
    read_schema_migration_table(connection=connection)
finally:
    connection.close()


port = int(os.getenv("PORT", 8001))

uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=port
)
