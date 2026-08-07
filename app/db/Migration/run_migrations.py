from pathlib import Path
from app.db.connection import get_connection, mysql
from app.db.Migration.migration_utils import run_sql_file

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


def ensure_migrations_table(cursor):
    """
    function to create the migration table
    """
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)
    except mysql.connector.Error as err:
        print(f"Failed creating schema_migration table: {err}")


def read_schema_migration_table(connection=None):
    """
    Orchestrator for executing migrations script that 
    have not been applied yet
    """
    try:
        if connection is None:
            connection = get_connection()
        cursor = connection.cursor()

        # ensure table exists
        ensure_migrations_table(cursor)
       # get applied migrations
        run_sql_file(
            cursor=cursor, sql="SELECT version FROM schema_migrations")
        applied = {row[0] for row in cursor.fetchall()}

        # get all migration files
        sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        # run pending migrations
        for file in sql_files:
            version = file.stem  # filename without .sql

            if version in applied:
                continue

            print(f"Running migration: {version}")

            sql = file.read_text(encoding="utf-8")
            # cursor.execute(sql)
            run_sql_file(cursor=cursor, sql=sql)

            run_sql_file(
                cursor=cursor, sql="INSERT INTO schema_migrations (version, applied_at) VALUES (%s, NOW())", args=(version,))
            connection.commit()

        print("successfully ran migrations")
    except mysql.connector.Error as err:
        connection.rollback()
        print("Database error: ", err)
    finally:
        cursor.close()
        connection.close()


read_schema_migration_table()
