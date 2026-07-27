import uvicorn
from app.db.Migration.run_migrations import read_schema_migration_table
read_schema_migration_table()
uvicorn.run("app.main:app", port=8001)
