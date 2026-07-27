from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_sql_file(cursor, sql, args=None):
    """
    Function to run sql files with 
    the cursor object from sql connection engine
    """
    if args:
        cursor.execute(sql, args)
    else:
        cursor.execute(sql)


def read_file(fname):
    """
    function to read a file
    """
    sql = Path(fname)

    if not sql.exists():
        return None

    return sql.read_text(encoding="utf-8")
