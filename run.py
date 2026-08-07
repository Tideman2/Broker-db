import uvicorn
from app.db.Migration.run_migrations import read_schema_migration_table
from app.db.connection import get_test_connection
read_schema_migration_table()
read_schema_migration_table(connection=get_test_connection())
uvicorn.run("app.main:app", port=8001)
